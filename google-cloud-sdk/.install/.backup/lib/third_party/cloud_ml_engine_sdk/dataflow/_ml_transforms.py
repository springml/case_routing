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

import abc
import datetime
import logging
import os
import random
import tempfile

import _ml_functions as ml_func
import apache_beam as beam

# pylint: disable=g-import-not-at-top
# TODO(user): Remove after Dataflow 2.0.0 SDK is released.
try:
  from apache_beam.options import pipeline_options as df_options
except ImportError:
  try:
    from apache_beam.utils import pipeline_options as df_options
  except ImportError:
    from apache_beam.utils import options as df_options
import batch_prediction

from google.cloud.ml.io import coders as ml_coders
from google.cloud.ml.io import SaveFeatures
from google.cloud.ml.io import SaveMetadata
from google.cloud.ml.util import _dataflow as dfutil
from google.cloud.ml.util._api import ApiBeta
# pylint: enable=g-import-not-at-top


class DeployVersion(beam.PTransform):
  """Deploys a model version for use in online prediction.

  This PCollection is parameterized by model and version names.

  The input PCollection should be a trained model, as returned from the
  ``Train`` operation.
  """

  def __init__(self,
               model_name,
               version_name,
               cloud_ml_endpoint=None,
               runtime_version=None):
    super(DeployVersion, self).__init__()
    self._model_name = model_name
    self._version_name = version_name
    self._cloud_ml_endpoint = cloud_ml_endpoint
    self._runtime_version = runtime_version

  # TODO(b/33677990): Remove apply method.
  def apply(self, trained_model):
    return self.expand(trained_model)

  def expand(self, trained_model):
    options = trained_model.pipeline.options
    if options is None:
      options = df_options.PipelineOptions()

    project = options.view_as(df_options.GoogleCloudOptions).project

    def deploy_version(trained_model, (project, model_name, version_name)):
      """Deploy a model version using the Cloud ML api.

      Args:
        trained_model: A trained model from ml.Train
        (project, model_name, version_name): Tuple of project name, model name,
          and version name to deploy.

      Returns:
        A list containing a tuple of (model_name, version_name).

      Raises:
        RuntimeError: if the api call fails.
      """
      api = ApiBeta(project_id=project, endpoint=self._cloud_ml_endpoint)
      api.create_model(model_name)
      operation = api.deploy_version(
          model_name,
          version_name,
          origin_uri=trained_model,
          runtime_version=self._runtime_version)
      print 'Waiting for Cloud ML version creation:', operation['name']
      deployed = api.wait_for_operation(
          operation['name'],
          timeout=datetime.timedelta(hours=1),
          polling_interval=datetime.timedelta(seconds=30))
      if not deployed.get('done', None):
        msg = ('The version creation {0} did not complete in the time '
               'allotted.').format(operation['name'])
        logging.error(msg)
      else:
        # The job completed. So now we need to check whether it completed
        # successfully or with an error.
        if deployed.get('error', None) is not None:
          # The job finished with an error.
          msg = 'The version creation {0} finished with {1} error: {1}.'.format(
              version_name, deployed['error'])
          logging.error(msg)
          raise RuntimeError(msg)
      return [(model_name, version_name)]

    return trained_model | (beam.Map(
        deploy_version, (project, self._model_name, self._version_name)))


class Evaluate(beam.PTransform):
  """Applies a model to each element in the PCollection to produce a prediction.

  This PCollection is parameterized by a trained model, as returned from the
  ``Train`` operation.

  The input PCollection should be a pre-processed set of examples, in the format
  expected by the trained model. The output is a PCollection of
  (input_example, predicted_value).

  TODO(b/33925193): Reconcile this with batch_prediction.BatchPredict.
  """

  def __init__(self, trained_model,
               batch_size=batch_prediction.DEFAULT_BATCH_SIZE, **kwargs):
    super(Evaluate, self).__init__(**kwargs)
    self._trained_model = trained_model
    self._batch_size = batch_size

  # TODO(b/33677990): Remove apply method.
  def apply(self, features):
    return self.expand(features)

  def expand(self, features):
    # Create a PValue singleton for input and output spec.
    return (features
            # TODO(user): Use an appropriate formatter for in-memory
            # representations here.
            | 'Serialize' >> beam.Map(lambda x: x.SerializeToString())
            | beam.ParDo(batch_prediction.EmitAsBatchDoFn(self._batch_size))
            | beam.ParDo(
                batch_prediction.PredictionDoFn(skip_preprocessing=True),
                beam.pvalue.AsSingleton(self._trained_model)))


class Predict(beam.PTransform):
  """A transform for batch prediction, based on a trained model.
  """

  def __init__(self,
               input_uris,
               output_uri=None,
               api_version=ApiBeta,
               region=None,
               data_format='TEXT',
               cloud_ml_endpoint=None,
               runtime_version=None):
    """Construct a transform to do batch prediction based on a train a model.

    The input PCollection should be the output of DeployVersion, or a tuple of
    (model, version).

    Args:
      input_uris: The input files to run against batch prediction. Must be a
        Google Cloud Storage location.
      output_uri: (Optional) The location to use for storing the results. If
        provided, must be a Google Cloud Storage location.
      api_version: version of the API to be used. Used for testing.
      region: Cloud region in which to run the job.
      data_format: The data format of the input data, 'TEXT' or 'TFRECORD'.
        Defaults to TEXT.
      cloud_ml_endpoint: (Optional) Override the default endpoint for Cloud ML.
      runtime_version: (Optional) the Google Cloud ML runtime version to use.

    Raises:
       ValueError: If region is not specified.
    """
    super(Predict, self).__init__()

    self.input_uris = input_uris
    self.output_uri = output_uri
    self.api_version = api_version
    self.region = region
    self.data_format = data_format
    self.cloud_ml_endpoint = cloud_ml_endpoint
    if not self.region:
      raise ValueError('region must be specified for ml Predict API calls.')
    self.runtime_version = runtime_version

  # TODO(b/33677990): Remove apply method.
  def apply(self, deployed_model):
    return self.expand(deployed_model)

  def expand(self, deployed_model):
    """Apply the transform.

    Args:
      deployed_model: A PCollection should be the output of DeployVersion, or a
        tuple of (model, version).

    Returns:
         A PCollection with a the results of the Prediction

    Raises:
       ValueError: If the arguments are invalid.
    """
    pipeline = deployed_model.pipeline

    # For the job name use a combination of the transform label and a
    # datestamp. The datestamp is intended to make it unique.
    now = datetime.datetime.now()
    # We add some salt to the job name to avoid collisions if we try to submit
    # multiple jobs at the same time.
    # N.B. The job_name is fixed at pipeline construction time. This is
    # critical because multiple invocation of the Train transform (e.g. because
    # of retries) need to use the same job name.
    salt = '%04x' % random.getrandbits(4 * 4)

    # TODO(b/28989568): We need to lower case the name because the backend
    # only allows lower case letters for job names. The backend should probably
    # do this automatically but currently it doesn't.
    job_name = '{0}_{1}_{2}'.format(self.label, now.strftime('%y%m%d_%H%M%S'),
                                    salt).lower().replace(' ', '_')

    options = pipeline.options
    # TODO(b/29163051) Options can be None depending on how the runner was
    # constructed.
    if options is None:
      options = df_options.PipelineOptions()

    cloud_options = options.view_as(df_options.GoogleCloudOptions)
    project_id = cloud_options.project

    if cloud_options.temp_location:
      temp_dir = cloud_options.temp_location
    elif cloud_options.staging_location:
      temp_dir = cloud_options.staging_location
    else:
      raise ValueError(
          '--staging_location must be specified to run in the cloud')

    if not self.output_uri:
      output_uri = os.path.join(temp_dir, 'prediction_results')
    else:
      output_uri = self.output_uri

    logging.info('Output uri : %s', output_uri)

    # Construct the batch prediction job.
    prediction_request = ml_func.PredictionJobRequest(
        project_id, job_name, self.input_uris, output_uri, self.region,
        self.data_format, endpoint=self.cloud_ml_endpoint,
        runtime_version=self.runtime_version)
    request = (pipeline | 'PredictRequest' >> beam.Create([prediction_request])
               | 'AugmentPredictArgs' >> beam.ParDo(
                   ml_func._AugmentPredictArgsDo(),  # pylint: disable=protected-access
                   beam.pvalue.AsSingleton(deployed_model)))

    # Run the batch prediction job
    predict_do = ml_func.BatchPredictionJobDo(
        api_class=self.api_version)
    unused_prediction_results = (
        request | 'BatchPrediction' >> beam.ParDo(predict_do))

    # Wait until the prediction job is done, then Read the results from the file
    # to which they were written and return.
    results = 'Read Results' >> beam.io.ReadFromText(output_uri, validate=False)
    return results


class TensorFlowProgramSpec(object):
  """A class for wrapping a tensorflow main program for use in dataflow.

  Use this class to wrap a tensorflow main program in such a way that it can
  be invoked by the Train transform, producing output suitable for the Predict
  transform.

  An implementer of this class must specify how to write out the input data,
  how to read the output as a tensorflow session, and how to pass that paths
  of the input and output data as flags to the main program.

  Any pip packages that need to be staged on Cloud ML workers should be
  specified using the Pipeline option extra_packages.
  """
  # Despite allowing arbitrary formats for write, prediction still constrains
  # the graph input format to Example protos.
  # TODO(user): Generalize this.
  # (Likely this transformation and the write_input_data are tightly coupled.)

  __metaclass__ = abc.ABCMeta

  def __init__(self, train_request):
    self.train_request = train_request

  def write_input_data(self, features, path):
    """Writes features out to the format expected by the tensorflow program.

    Args:
      features: A PCollection of string json Example proto features.
      path: Where to write the data.

    Returns:
      A PCollection of filenames or other identifiers, to be passed to
      construct_io_args and waited on before launching the tensorflow job.
    """
    # TODO(user): Support non-default formats.
    return features| 'SaveFeatures' >> SaveFeatures(path)

  def construct_io_args(self, train_data_files, test_data_files, output_dir,
                        metadata_path):
    """Returns a list of arguments to add to the command line.

    Use this to inform the main program where to read and write its inputs
    and outputs.  By default no additional args are added.

    Args:
      train_data_files: A list of filenames, as returned by `write_input_data`.
      test_data_files: A list of filenames, as returned by `write_input_data`.
      output_dir: An output directory, to be passed to `read_model`.  Typically
          the trained model should be exported into this directory.
      metadata_path: The metadata file path.

    Returns:
      A list of strings with args for the training job.
    """
    # TODO(user): Take file patterns rather than file lists?
    args = ['--output_path', output_dir]
    args.extend(
        list(sum([('--train_data_paths', x) for x in train_data_files], ())))
    args.extend(
        list(sum([('--eval_data_paths', x) for x in test_data_files], ())))
    if metadata_path:
      args += ['--metadata_path', metadata_path]
    return args

  def read_model(self, train_results, output_dir, export_subdir):
    """Returns the model directory to use for prediction.

    Args:
      train_results: The result of the TrainJobRequest.
      output_dir: The same output directory passed to `construct_io_args`.
      export_subdir: The subdirectory to add onto the output directory.

    Returns:
      The directory from which to read the model.
    """
    directory = output_dir
    # Get the best trial id if it's an hptuning run.
    if (train_results.training_job_result and
        'completedTrialCount' in train_results.training_job_result and
        train_results.training_job_result['completedTrialCount'] > 0 and
        train_results.training_job_result['trials'] and
        'trialId' in train_results.training_job_result['trials'][0]):
      best_trial_id = train_results.training_job_result['trials'][0]['trialId']
      directory = os.path.join(directory, best_trial_id)
    if export_subdir:
      directory = os.path.join(directory, export_subdir)
    return directory


class Train(beam.PTransform):
  """A transform for training a model specified by a tf main program.

  The transform helps coordinate materializing PCollections to disk.
  """

  def __init__(self,
               tf_main_spec=TensorFlowProgramSpec(
                   ml_coders.TrainingJobRequest()),
               package_uris=None,
               python_module=None,
               metadata=None,
               output_dir=None,
               export_subdir=None,
               use_cloud_ml=None,
               cloud_ml_endpoint=None,
               job_args=None,
               hyperparameters=None,
               region=None,
               scale_tier=None,
               worker_count=None,
               ps_count=None,
               worker_type=None,
               ps_type=None,
               master_type=None,
               label=None,
               timeout=datetime.timedelta(hours=3),
               runtime_version=None):
    """Construct a transform to train a model.

    Args:
      tf_main_spec: An instance of TensorFlowProgramSpec, defaults
        to a standard instance.
      package_uris: The location of the tarball containing the training program
        to run, or a list of multple tarballs.
      python_module: The module to run for ml training inside the package_uris.
      metadata: (Optional) A metadata object to pass to the trainer.
      output_dir: (Optional) The location to use for storing the model and
        other results.  If provided, must be a GSC location if either dataflow
        or tensorflow is running in the cloud.
      export_subdir: (Optional) The subdirectory in output_dir that the trainer
        will place the final exported model in.
      use_cloud_ml: (Optional) Whether to run the training job on the Cloud ML
        service or locally, inside the Dataflow worker process. If not specified
        then the default is chosen based on the runner.
      cloud_ml_endpoint: (Optional) Override the default endpoint for Cloud ML.
      job_args: Additional command line args to pass to the job.
      hyperparameters: Hyperparameter config to submit with the training job.
      region: (Optional) Google Cloud region in which to run training.
      scale_tier: Google Cloud ML tier to run training in. Defaults to BASIC.
      worker_count: Worker count to use with a CUSTOM scale tier.
      ps_count: Parameter Server count to use with a CUSTOM scale tier.
      worker_type: Worker type to use with a CUSTOM scale tier.
      ps_type: Parameter Server type to use with a CUSTOM scale tier.
      master_type: Master type to use with a CUSTOM scale tier.
      label: (Optional) label for the transform.
      timeout: Timeout for waiting on the Training Job to complete. The job will
        be cancelled if it does not finish in this time, and this Transform will
        fail. Should be specified as a datetime.timedelta. Defaults to 3 hours.
      runtime_version: (Optional) the Google Cloud ML runtime version to use.
    """
    super(Train, self).__init__(label=label)

    self.tf_main_spec = tf_main_spec
    self.package_uris = package_uris
    self.python_module = python_module
    self.metadata = metadata
    self.job_args = job_args
    self.output_dir = output_dir
    self.export_subdir = export_subdir
    self.cloud_ml_endpoint = cloud_ml_endpoint
    self.use_cloud_ml = use_cloud_ml
    self.hyperparameters = hyperparameters
    self.region = region
    self.scale_tier = scale_tier
    self.worker_count = worker_count
    self.ps_count = ps_count
    self.worker_type = worker_type
    self.ps_type = ps_type
    self.master_type = master_type
    if not tf_main_spec.train_request.timeout:
      tf_main_spec.train_request.timeout = timeout
    self.runtime_version = runtime_version

  # TODO(b/33677990): Remove apply method.
  def apply(self, train_and_test_datasets):
    return self.expand(train_and_test_datasets)

  def expand(self, train_and_test_datasets):
    """Apply the transform.

    Args:
      train_and_test_datasets: A pair of (train, test) PCollections of
        json strings representing Example Protos

    Returns:
       A 2-tuple of
         A PCollection with a single TrainedModel, suitable for used by Predict
         A PCollection with a single TrainingJobResult that describes the
         result of training.

    Raises:
       ValueError: If the arguments are invalid.
    """
    train_dataset, test_dataset = train_and_test_datasets
    pipeline = train_dataset.pipeline

    # For the job name use a combination of the transform label and a
    # datestamp. The datestamp is intended to make it unique.
    now = datetime.datetime.now()
    # We add some salt to the job name to avoid collisions if we try to submit
    # multiple jobs at the same time.
    # N.B. The job_name is fixed at pipeline construction time. This is
    # critical because multiple invocation of the Train transform (e.g. because
    # of retries) need to use the same job name.
    salt = '%04x' % random.getrandbits(4 * 4)

    # TODO(b/28989568): We need to lower case the name because the backend
    # only allows lower case letters for job names. The backend should probably
    # do this automatically but currently it doesn't.
    job_name = '{0}_{1}_{2}'.format(self.label, now.strftime('%y%m%d_%H%M%S'),
                                    salt).lower()

    options = pipeline.options
    # TODO(b/29163051) Options can be None depending on how the runner was
    # constructed.
    if options is None:
      options = df_options.PipelineOptions()

    cloud_options = options.view_as(df_options.GoogleCloudOptions)
    run_on_cloud = self.use_cloud_ml

    if run_on_cloud is None:
      # TODO(user): Remove the fallback after the next Dataflow release.
      try:
        dataflow_runner = beam.runners.DataflowRunner
      except AttributeError:
        dataflow_runner = beam.runners.DataflowPipelineRunner

      # Choose a default based on the runner.
      if isinstance(pipeline.runner, dataflow_runner):
        run_on_cloud = True
      else:
        run_on_cloud = False

    if self.output_dir:
      temp_dir = self.output_dir
    elif run_on_cloud:
      cloud_options = options.view_as(df_options.GoogleCloudOptions)

      if cloud_options.temp_location:
        temp_dir = os.path.join(cloud_options.temp_location, job_name)
      elif cloud_options.staging_location:
        temp_dir = os.path.join(cloud_options.staging_location, job_name)
      else:
        raise ValueError(
            '--staging_location must be specified to run in the cloud')
    else:
      temp_dir = tempfile.mkdtemp(job_name)
    logging.info('Temp dir: %s', temp_dir)

    if run_on_cloud:
      train_do = ml_func.TrainingJobDo()
      project = cloud_options.project
    else:
      train_do = ml_func._TrainingJobLocalDo()  # pylint: disable=protected-access
      project = None

    _ = train_dataset | dfutil.CountPCollection('ml-train-input')

    # Write the train and test data to files so we can pass it to the trainer.
    train_data_path = os.path.join(temp_dir, 'training')
    test_data_path = os.path.join(temp_dir, 'testing')
    output_dir = os.path.join(temp_dir, 'model')
    # TODO(b/34839956) Make sure we can handle the tf.Transform metadata.
    metadata_path = os.path.join(output_dir, 'metadata.json')

    # This PTransform is primarily to avoid stage name collisions in writing
    # training and test data.
    # TODO(user): Figure out why i_type @beam.ptransform_fn breaks pickling.
    train_files = (
        train_dataset | 'WriteTrainData'
        >> ml_func._WrapCallable(  # pylint: disable=protected-access
            self.tf_main_spec.write_input_data, train_data_path))
    test_files = (
        test_dataset | 'WriteTestData'
        >> ml_func._WrapCallable(  # pylint: disable=protected-access
            self.tf_main_spec.write_input_data, test_data_path))
    if self.metadata:
      metadata_files = self.metadata | SaveMetadata(metadata_path)
    else:
      metadata_files = pipeline | beam.Create([None])

    # Construct and run the training job.
    train_request = self.tf_main_spec.train_request.copy()
    if not train_request.package_uris:
      train_request.package_uris = []
    if self.package_uris:
      if isinstance(self.package_uris, basestring):
        train_request.package_uris.extend([self.package_uris])
      else:
        train_request.package_uris.extend(self.package_uris)
    # remove duplicates from train_request
    train_request.package_uris = list(set(train_request.package_uris))

    train_request.job_args = self.job_args or []
    if self.python_module:
      train_request.python_module = self.python_module
    if not train_request.project:
      train_request.parent = project
    if not train_request.job_name:
      train_request.job_name = job_name
    if not train_request.endpoint:
      train_request.endpoint = self.cloud_ml_endpoint
    if not train_request.hyperparameters:
      train_request.hyperparameters = self.hyperparameters
    if not train_request.region:
      train_request.region = self.region
    if not train_request.scale_tier:
      train_request.scale_tier = self.scale_tier
    if not train_request.worker_count:
      train_request.worker_count = self.worker_count
    if not train_request.ps_count:
      train_request.ps_count = self.ps_count
    if not train_request.worker_type:
      train_request.worker_type = self.worker_type
    if not train_request.ps_type:
      train_request.ps_type = self.ps_type
    if not train_request.master_type:
      train_request.master_type = self.master_type
    if not train_request.runtime_version:
      train_request.runtime_version = self.runtime_version

    requests = (
        pipeline | 'CreateRequest' >> beam.Create([train_request])
        | 'AugmentTrainingArgs' >> beam.ParDo(
            ml_func._AugmentTrainArgsDo(  # pylint: disable=protected-access
                self.tf_main_spec),
            beam.pvalue.AsIter(train_files),
            beam.pvalue.AsIter(test_files),
            output_dir,
            beam.pvalue.AsSingleton(metadata_files)))

    train_results = requests | 'TrainModel' >> beam.ParDo(train_do)

    # Read and return the model directory and training results.
    model_directory = (
        train_results
        | 'CreateModel' >> beam.Map(self.tf_main_spec.read_model, output_dir,
                                    self.export_subdir))

    return model_directory, train_results
