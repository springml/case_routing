# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Cloud ML batch prediction dataflow transforms.
"""
# TODO(user): add a unittest to test logging futures.

import datetime
import json
import logging
import threading
import traceback



import apache_beam as beam
from apache_beam.options.value_provider import StaticValueProvider
from apache_beam.options.value_provider import ValueProvider
from apache_beam.transforms import window
from apache_beam.utils.windowed_value import WindowedValue

from google.cloud.ml import prediction as mlprediction
from google.cloud.ml.dataflow import _aggregators as aggregators
from google.cloud.ml.dataflow import _cloud_logging_client as cloud_logging_client

BASE64_JSON_ATTR_ = "b64"
BASE64_TENSOR_NAME_SUFFIX_ = "_bytes"
DEFAULT_BATCH_SIZE = 1000  # 1K instances per batch when evaluating models.
LOG_SIZE_LIMIT = 1000  # 1K bytes for the input field in log entries.
LOG_NAME = "worker"


class EmitAsBatchDoFn(beam.DoFn):
  """A DoFn that buffers the records and emits them batch by batch."""

  def __init__(self, desired_batch_size):
    """Constructor of EmitAsBatchDoFn beam.DoFn class.

    Args:
      desired_batch_size: the desired size we want to buffer the records before
        emitting.
    """
    # TODO(user): Remove the "if" section when the direct use of
    # EmitAsBatchDoFn() is retired from ml_transform.
    if isinstance(desired_batch_size, int):
      desired_batch_size = StaticValueProvider(int, desired_batch_size)
    self._desired_batch_size = desired_batch_size
    self._batch = []

    # Metrics.
    self._batch_size_distribution = beam.metrics.Metrics.distribution(
        self.__class__, "batch_size")
    self._num_instances = beam.metrics.Metrics.counter(self.__class__,
                                                       "num_instances")

  def _flush_batch(self):
    self._batch_size_distribution.update(len(self._batch))
    self._num_instances.inc(len(self._batch))
    result = self._batch
    self._batch = []
    return result

  # TODO(user): Remove the context and try catch after sdk update
  def process(self, element):
    try:
      element = element.element
    except AttributeError:
      pass

    self._batch.append(element)
    if len(self._batch) >= self._desired_batch_size.get():
      yield self._flush_batch()

  def finish_bundle(self, context=None):
    if self._batch:
      yield WindowedValue(self._flush_batch(), -1, [window.GlobalWindow()])


class PredictionDoFn(beam.DoFn):
  """A DoFn class loading the model to create session and performing prediction.

  The input PCollection consists of a list of strings from the input files.

  The DoFn first loads model from a given path where meta graph data and
  checkpoint data are exported to. Then if the there is only one string input
  tensor or the model needs to preprocess the input, it directly passes the
  data to prediction. Otherwise, it tries to load the data into JSON.

  Then it batches the inputs of each instance into one feed_dict. After that, it
  runs session and predicts the interesting values for all the instances.
  Finally it emits the prediction result for each individual instance.
  """

  class _ModelState(object):
    """Atomic representation of the in-memory state of the model."""

    def __init__(self, model_dir, skip_preprocessing):
      self.model_dir = model_dir

      session, signature = mlprediction.load_model(model_dir)
      client = mlprediction.SessionClient(session, signature)
      self.model = mlprediction.create_model(
          client, model_dir, skip_preprocessing=skip_preprocessing)

  # TODO(b/33746781): Get rid of this and instead use self._model_state for
  # all initialization detection.
  _thread_local = threading.local()

  def __init__(self,
               aggregator_dict=None,
               user_project_id="",
               user_job_id="",
               skip_preprocessing=False,
               target="",
               config=None):
    """Constructor of Prediction beam.DoFn class.

    Args:
      aggregator_dict: A dict of aggregators containing maps from counter name
                       to the aggregator.
      user_project_id: A string. The project to which the logs will be sent.
      user_job_id:     A string. The job to which the logs will be sent.
      skip_preprocessing: bool whether to skip preprocessing even when
                          the metadata.yaml/metadata.json file exists.
      target: The execution engine to connect to. See target in tf.Session(). In
              most cases, users should not set the target.
      config: A ConfigProto proto with configuration options. See config in
              tf.Session()

    Side Inputs:
      model_dir: The directory containing the model to load and the
                 checkpoint files to restore the session.
    """
    self._target = target

    # TODO(user): Remove the "if" section when the direct use of
    # PredictionDoFn() is retired from ml_transform.
    if isinstance(user_project_id, basestring):
      user_project_id = StaticValueProvider(str, user_project_id)
    if isinstance(user_job_id, basestring):
      user_job_id = StaticValueProvider(str, user_job_id)

    self._user_project_id = user_project_id
    self._user_job_id = user_job_id
    self._skip_preprocessing = skip_preprocessing
    self._config = config
    self._aggregator_dict = aggregator_dict
    self._model_state = None
    self._cloud_logger = None

    # Metrics.
    self._model_load_seconds_distribution = beam.metrics.Metrics.distribution(
        self.__class__, "model_load_seconds")

  def start_bundle(self):
    user_project_id = self._user_project_id.get()
    user_job_id = self._user_job_id.get()
    if user_project_id and user_job_id:
      self._cloud_logger = cloud_logging_client.MLCloudLoggingClient.create(
          user_project_id, user_job_id, LOG_NAME, "jsonPayload")

  def _create_snippet(self, input_data):
    """Truncate the input data to create a snippet."""
    try:
      input_snippet = "\n".join(str(x) for x in input_data)
      return unicode(input_snippet[:LOG_SIZE_LIMIT], errors="replace")
    except Exception:  # pylint: disable=broad-except
      logging.warning("Failed to create snippet from input: [%s].",
                      traceback.format_exc())
      return "Input snippet is unavailable."

  # TODO(user): Remove the try catch after sdk update
  def process(self, element, model_dir):
    try:
      element = element.element
    except AttributeError:
      pass

    try:
      if isinstance(model_dir, ValueProvider):
        model_dir = model_dir.get()

      if self._model_state is None:
        if (getattr(self._thread_local, "model_state", None) is None or
            self._thread_local.model_state.model_dir != model_dir):
          start = datetime.datetime.now()
          self._thread_local.model_state = self._ModelState(
              model_dir, self._skip_preprocessing)
          self._model_load_seconds_distribution.update(
              int((datetime.datetime.now() - start).total_seconds()))
        self._model_state = self._thread_local.model_state
      else:
        assert self._model_state.model_dir == model_dir

      # Try to load it.
      if (self._model_state.model.is_single_string_input() or
          self._model_state.model.need_preprocess()):
        loaded_data = element
      else:
        loaded_data = [json.loads(d) for d in element]
      instances = mlprediction.decode_base64(loaded_data)
      inputs, predictions = self._model_state.model.predict(instances)
      predictions = list(predictions)
      predictions = mlprediction.encode_base64(
          predictions,
          self._model_state.model.signature.outputs)

      if self._aggregator_dict:
        aggr = self._aggregator_dict.get(
            aggregators.AggregatorName.ML_PREDICTIONS, None)
        if aggr:
          aggr.inc(len(predictions))

      for i, p in zip(inputs, predictions):
        yield i, p

    except mlprediction.PredictionError as e:
      logging.error("Got a known exception: [%s]\n%s", e.error_message,
                    traceback.format_exc())
      if self._cloud_logger:
        # TODO(user): consider to write a sink to buffer the logging events. It
        # also eliminates the restarting/duplicated running issue.
        self._cloud_logger.write_error_message(e.error_message,
                                               self._create_snippet(element))
      # reraise failure to load model as permanent exception to end dataflow job
      if e.error_code == mlprediction.PredictionError.FAILED_TO_LOAD_MODEL:
        raise beam.utils.retry.PermanentException(e.error_message)
      try:
        yield beam.pvalue.TaggedOutput("errors", (e.error_message, element))
      except AttributeError:
        yield beam.pvalue.SideOutputValue("errors", (e.error_message, element))

    except Exception as e:  # pylint: disable=broad-except
      logging.error("Got an unknown exception: [%s].", traceback.format_exc())
      if self._cloud_logger:
        self._cloud_logger.write_error_message(
            str(e), self._create_snippet(element))
      try:
        yield beam.pvalue.TaggedOutput("errors", (str(e), element))
      except AttributeError:
        yield beam.pvalue.SideOutputValue("errors", (str(e), element))


class BatchPredict(beam.PTransform):
  """A transform to load tensorflow model and do prediction.

  The transform first reads prediction instance from the input. Then it loads
  the tensorflow model from disk and restores the session. For each input, it
  performs prediction and emits the results.
  """

  def __init__(self,
               model_dir,
               batch_size=DEFAULT_BATCH_SIZE,
               aggregator_dict=None,
               user_project_id="",
               user_job_id="",
               target="",
               config=None,
               return_input=False,
               **kwargs):
    """Constructs the transform.

    Args:
      model_dir: a Pvalue singleton of model directory that contains model
                 graph and model parameter files.
      batch_size: the number of records in one batch or a ValueProvider of
                  integer.  All the instances in the same batch would be fed
                  into tf session together thereby only on Session.Run() is
                  invoked for one batch.
      aggregator_dict: A dict of aggregators containing maps from counter name
                 to the aggregator.
      user_project_id: A string or a ValueProvider of string.
                       The project to which the logs will be sent.
      user_job_id: A string or a ValueProvider of string. The job to which
                   the logs will be sent.
      target: The execution engine to connect to. Optional. See target in
              tf.Session()
      config: A ConfigProto proto with configuration options. Optional. See
              config in tf.Session()
      return_input: if true, the transforms returns a tuple of [input, output]
                    otherwise only the output is returned.
      **kwargs: Other named arguments, e.g. label, passed to base PTransform.
    """
    super(BatchPredict, self).__init__(**kwargs)

    if not isinstance(batch_size, (int, ValueProvider)):
      raise TypeError("%s: batch_size must be of type int"
                      " or ValueProvider; got %r instead"
                      % (self.__class__.__name__, batch_size))
    if isinstance(batch_size, int):
      batch_size = StaticValueProvider(int, batch_size)
    self._batch_size = batch_size

    self._aggregator_dict = aggregator_dict

    if not isinstance(user_project_id, (basestring, ValueProvider)):
      raise TypeError("%s: user_project_id must be of type string"
                      " or ValueProvider; got %r instead"
                      % (self.__class__.__name__, user_project_id))
    if isinstance(user_project_id, basestring):
      user_project_id = StaticValueProvider(str, user_project_id)
    self._user_project_id = user_project_id

    if not isinstance(user_job_id, (basestring, ValueProvider)):
      raise TypeError("%s: user_job_id must be of type string"
                      " or ValueProvider; got %r instead"
                      % (self.__class__.__name__, user_job_id))
    if isinstance(user_job_id, basestring):
      user_job_id = StaticValueProvider(str, user_job_id)
    self._user_job_id = user_job_id

    self._target = target
    self._config = config
    self._model_dir = model_dir
    self._return_input = return_input

  # TODO(b/33677990): Remove apply method.
  def apply(self, data):
    return self.expand(data)

  def expand(self, data):
    """Apply the transform.

    Args:
      data: A PCollection of records containing the data to predict.

    Returns:
      A PCollection of prediction records and errors
    """
    result = (data | "Batch" >> beam.ParDo(EmitAsBatchDoFn(self._batch_size))
              | "Prediction" >> beam.ParDo(
                  PredictionDoFn(
                      self._aggregator_dict,
                      self._user_project_id,
                      self._user_job_id,
                      skip_preprocessing=False,
                      target=self._target,
                      config=self._config), self._model_dir).with_outputs(
                          "errors", main="main"))
    input_output, errors = result.main, result.errors
    if self._return_input:
      output_data = input_output
    else:
      output_data = input_output | beam.Map(lambda (_, prediction): prediction)

    return output_data, errors
