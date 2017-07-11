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
"""Private Cloud ML dataflow transforms and functions.
"""

import datetime
import logging
import os
import subprocess
import time

import apache_beam as beam

from google.cloud.ml.io.coders import TrainingJobResult
from google.cloud.ml.util import _file as ml_file
from google.cloud.ml.util._api import ApiBeta


class TrainingJobDo(beam.DoFn):
  """A DoFn that submits a training job and waits for it to finish.

  The input PCollection should be a PCollection of TrainingJobRequest.
  """

  def __init__(self, api_class=ApiBeta, sleep_func=time.sleep):
    """Construct a DoFn to train a model.

    Args:
      api_class: (Optional intended for testing only) A subclass of ApiBase
        that acts a client library for the Cloud ML Apis.
      sleep_func: (Optional intended for testing only) A function to call to
        wait some amount of time.
    """
    self._api = None
    # Handle to the function to use to sleep between calls.
    # Makes it easy to inject a mock during testing
    self._sleep_func = sleep_func

    # This bit of indirection is intended to make it easy to inject a mock Api
    # during testing.
    self._api_class = api_class

  # TODO(user): Remove the try catch after sdk update
  def process(self, train_spec):
    try:
      train_spec = train_spec.element
    except AttributeError:
      pass
    logging.info('Setting endpoint to %s', train_spec.endpoint)
    self._api = self._api_class(project_id=train_spec.project,
                                endpoint=train_spec.endpoint)

    # Check if the job already exists.
    training_job = self._api.get_job(train_spec.job_name)

    if not training_job:
      print 'Submitting training job', train_spec.job_name
      logging.info('Submitting training job %s.', train_spec.job_name)
      training_job = self._api.submit_training_job(
          name=train_spec.job_name, package_uris=train_spec.package_uris,
          python_module=train_spec.python_module, args=train_spec.job_args,
          hyperparameters=train_spec.hyperparameters,
          region=train_spec.region, scale_tier=train_spec.scale_tier,
          master_type=train_spec.master_type,
          worker_type=train_spec.worker_type,
          ps_type=train_spec.ps_type, worker_count=train_spec.worker_count,
          ps_count=train_spec.ps_count,
          runtime_version=train_spec.runtime_version)

    else:
      logging.info('The training job %s already exists.',
                   train_spec.job_name)

    timeout = train_spec.timeout
    if 'createTime' in training_job:
      # Adjust our timeout based on when the job was actually created,
      # in case dataflow is retrying this operation.
      # createTime is formatted like 2016-10-05T17:27:53Z
      start_time = datetime.datetime.strptime(training_job['createTime'],
                                              '%Y-%m-%dT%H:%M:%SZ')
      already_ran = datetime.datetime.now() - start_time
      timeout -= already_ran
      if timeout.total_seconds() < 0:
        # Don't allow a negative timeout.  We'll always check the job status
        # at least once before timing out.
        timeout = datetime.timedelta(seconds=0)

    logging.info('Waiting for Cloud ML training job: %s', training_job)
    # Print as well, so that users can see the job id during local runs.
    print 'Waiting for Cloud ML training job:', training_job
    final_job = self._api.wait_for_job(
        train_spec.job_name,
        timeout=timeout,
        polling_interval=train_spec.polling_interval)

    result = TrainingJobResult()
    result.training_request = train_spec

    result.training_job_metadata = final_job
    result.training_job_result = final_job.get('trainingOutput', None)
    result.error = final_job.get('errorMessage', None)

    if final_job.get('state', None) not in [
        'SUCCEEDED', 'FAILED', 'CANCELLED', 'CANCELLING'
    ]:
      msg = ('The training job {0} did not complete in the time '
             'allotted.').format(training_job)
      logging.error(msg)
      # Cancel the job ourselves and raise this as an error.
      self._api.cancel_job(train_spec.job_name)
      raise RuntimeError(msg)
    else:
      # The job completed. So now we need to check whether it completed
      # successfully or with an error.
      if final_job.get('errorMessage', None) is not None:
        # The job finished with an error.
        msg = 'The training job {0} finished with {1} error: {1}.'.format(
            training_job, final_job['errorMessage'])
        logging.error(msg)
        raise RuntimeError(msg)

    return [result]


class _TrainingJobLocalDo(beam.DoFn):
  """A DoFn that runs training locally.

  The input PCollection should be a PCollection of TrainingJobRequest.

  Training runs locally by running TensorFlow in a container as opposed to
  firing off a CloudML job.

  The input PCollection should be a PCollection of TrainingJobRequest.
  The value of trainer_uri should be the docker image to use.

  This requires docker is installed locally. As a result, it will not work
  when running on the Dataflow service.
  """

  # TODO(user): Remove the try catch after sdk update
  def process(self, train_spec):
    try:
      train_spec = train_spec.element
    except AttributeError:
      pass
    args = train_spec.job_args or []

    if not train_spec.python_module:
      raise ValueError('python_module must be provided.')

    command = ['python', '-m', train_spec.python_module]
    command.extend(args)

    logging.info('Running command: %s', ' '.join(command))
    subprocess.check_call(command)

    # TODO(user): Is there other data we should be outputting?
    result = TrainingJobResult()
    result.training_request = train_spec

    return [result]


class PredictionJobRequest(object):
  """This class contains the parameters for running a batch prediction job.
  """

  def __init__(self,
               project_id=None,
               job_name=None,
               input_uri=None,
               output_uri=None,
               region=None,
               data_format='TEXT',
               timeout=datetime.timedelta(hours=1),
               polling_interval=datetime.timedelta(seconds=30),
               endpoint=None,
               runtime_version=None):
    """Construct an instance of PredictionJobRequest.

    Args:
      project_id: The id of the project, used as credentials for the API
      job_name: A job name. This must be unique within the project.
      input_uri: A  URI to input files to do prediction on.
      output_uri: The output directory where the results of the job will be
        written
      region: Cloud region in which to run the request.
      data_format: The data format for the prediction api call.  Either TEXT or
        TF_RECORD.
      timeout: A datetime.timedelta expressing the amount of time to wait before
        giving up. The timeout applies to a single invocation of the process
        method in TrainModelDo. A DoFn can be retried several times before a
        pipeline fails.
      polling_interval: A datetime.timedelta to represent the amount of time to
        wait between requests polling for the files.
      endpoint: (Optional) The endpoint for the Cloud ML API.
      runtime_version: (Optional) the Google Cloud ML runtime version to use.
    """
    # Parent, model_name, and version_id get set by _AugmentPredictArgsDo
    self.parent = None
    self.model_name = None
    self.version_id = None

    self.project_id = project_id
    self.job_name = job_name
    self.input_uri = input_uri
    self.output_uri = output_uri
    self.region = region
    self.data_format = data_format
    self.endpoint = endpoint
    self.timeout = timeout
    self.polling_interval = polling_interval
    self.runtime_version = runtime_version

  @property
  def project(self):
    return self.parent

  def copy(self):
    """Return a copy of the object."""
    r = PredictionJobRequest()
    r.__dict__.update(self.__dict__)

    return r

  def __eq__(self, o):
    for f in ['parent', 'model_name', 'version_id', 'project_id', 'job_name',
              'input_uri', 'output_uri', 'region', 'data_format', 'timeout',
              'polling_interval', 'endpoint', 'runtime_version']:
      if getattr(self, f) != getattr(o, f):
        return False

    return True

  def __ne__(self, o):
    return not self == o

  def __repr__(self):
    fields = []
    for k, v in self.__dict__.iteritems():
      fields.append('{0}={1}'.format(k, v))
    return 'PredictionJobRequest({0})'.format(', '.join(fields))


class _AugmentPredictArgsDo(beam.DoFn):

  # TODO(user): Remove the try catch after sdk update
  def process(self, element, deployed_model):
    try:
      predict_request = element.element.copy()
    except AttributeError:
      predict_request = element.copy()
    if len(deployed_model) > 1:
      msg = ('The ml Predict PTransform was called with multiple models. Only 1'
             ' deployed model is currently supported per Predict call.')
      logging.error(msg)
      raise RuntimeError(msg)
    (predict_request.model_name, predict_request.version_id) = deployed_model[0]
    parent = '/projects/%s/models/%s/' % (predict_request.project_id,
                                          predict_request.model_name)
    if predict_request.version_id:
      parent = os.path.join(parent, 'versions', predict_request.version_id)
    predict_request.parent = parent
    logging.info('model dir: %s', parent)
    return [predict_request]


class PredictionJobResult(object):
  """Result of running batch prediction on a model."""

  def __init__(self):
    # A copy of the prediction request that created the job.
    self.prediction_request = None

    # At most one of error and prediction_job_result will be specified.
    # These fields will only be supplied if the job completed.
    # prediction_job_result will be provided if the job completed successfully
    # and error will be supplied otherwise.
    self.error = None
    self.prediction_job_result = None

  def __eq__(self, o):
    for f in ['prediction_request', 'error', 'prediction_job_result']:
      if getattr(self, f) != getattr(o, f):
        return False

    return True

  def __ne__(self, o):
    return not self == o

  def __repr__(self):
    fields = []
    for k, v in self.__dict__.iteritems():
      fields.append('{0}={1}'.format(k, v))
    return 'PredictionJobResult({0})'.format(', '.join(fields))


class BatchPredictionJobDo(beam.DoFn):
  """A DoFn that submits a batch predition job and waits for it to finish.

  The input PCollection should be a PCollection of PredictionJobRequest.
  """

  def __init__(self, api_class=ApiBeta, sleep_func=time.sleep):
    """Construct a DoFn and submit to the APIl.

    Args:
      api_class: (Optional intended for testing only) A subclass of ApiBase
        that acts a client library for the Cloud ML Apis.
      sleep_func: (Optional intended for testing only) A function to call to
        wait some amount of time.
    """
    self._api = None
    # Handle to the function to use to sleep between calls.
    # Makes it easy to inject a mock during testing
    self._sleep_func = sleep_func

    # This bit of indirection is intended to make it easy to inject a mock Api
    # during testing.
    self._api_class = api_class

  # TODO(user): Remove the try catch after sdk update
  def process(self, prediction_spec, input_files=None):
    try:
      prediction_spec = prediction_spec.element
    except AttributeError:
      pass
    print 'Job Name:', prediction_spec.job_name
    print 'Input files:', prediction_spec.input_uri
    print 'Output Files:', prediction_spec.output_uri

    self._api = self._api_class(project_id=prediction_spec.project_id,
                                endpoint=prediction_spec.endpoint)
    logging.info('Running Job %s', prediction_spec.job_name)
    logging.info('Input files %s', prediction_spec.input_uri)
    logging.info('Output Files %s', prediction_spec.output_uri)

    # Check if the job already exists.
    prediction_job = self._api.get_job(prediction_spec.job_name)
    if not prediction_job:
      prediction_job = self._api.submit_batch_prediction_job(
          name=prediction_spec.job_name,
          input_paths=prediction_spec.input_uri,
          output_path=prediction_spec.output_uri,
          model_name=prediction_spec.model_name,
          version_name=prediction_spec.version_id,
          data_format=prediction_spec.data_format,
          region=prediction_spec.region,
          runtime_version=prediction_spec.runtime_version)
    else:
      logging.info('The prediction job %s already exists.',
                   prediction_spec.job_name)

    logging.info('Waiting for Cloud ML prediction job: %s', prediction_job)
    final_job = self._api.wait_for_job(
        prediction_spec.job_name,
        timeout=prediction_spec.timeout,
        polling_interval=prediction_spec.polling_interval)

    result = PredictionJobResult()
    result.prediction_request = prediction_spec

    result.prediction_job_result = final_job.get('response', None)
    result.error = final_job.get('errorMessage', None)

    if final_job.get('state', None) not in [
        'SUCCEEDED', 'FAILED', 'CANCELLED', 'CANCELLING'
    ]:
      msg = ('The batch prediction job {0} did not complete in the time '
             'allotted.').format(prediction_job)
      logging.error(msg)
      # Cancel the job ourselves and raise this as an error.
      self._api.cancel_job(prediction_spec.job_name)
      raise RuntimeError(msg)
    else:
      # The job completed. So now we need to check whether it completed
      # successfully or with an error.
      if final_job.get('errorMessage', None) is not None:
        # The job finished with an error.
        msg = ('The batch prediction job {0} finished with {1}'
               ' error: {1}.'.format(prediction_job, final_job['errorMessage']))
        logging.error(msg)
        raise RuntimeError(msg)

    print 'Batch Prediction Job Completed succesfully'
    logging.info('Batch Prediction Job Completed succesfully')

    return [result]


def stage_packages(packages, staging_location):
  """Stage packages to GCS.

  Args:
    packages: List of local paths to stage to GCS.
    staging_location: Location on GCS where packages should be staged.

  Returns:
    gcs_uris: A, possibly empty, list of gcs uris to which the packages were
      staged.

  Raises:
    ValueError: If the inputs are invalid.
  """
  if not packages:
    return []

  staged_pip_packages = []
  staging_location = staging_location.rstrip('/')

  # We only allow files which are likely to be pip packages.
  valid_suffixes = ['.tar', '.tar.gz', '.zip']
  for package_path in packages:
    if package_path.startswith('gs://'):
      logging.info('Package %s is already on GCS', package_path)
      staged_pip_packages.append(package_path)
      continue

    # only allow packages that are likely to be pip packages based on the
    # file extension.
    if not any(package_path.endswith(s) for s in valid_suffixes):
      logging.info('Skipping package %s because its not of type %s',
                   package_path, valid_suffixes)
      continue

    rpath = package_path.rstrip('/')
    # We use full relative path of the local file because we want to allow
    # for the case where we have to local files with the same name in
    # different directories.
    gcs_location = staging_location + '/' + rpath
    logging.info('Staging %s to %s', package_path, gcs_location)
    ml_file.copy_file(package_path, gcs_location)
    staged_pip_packages.append(gcs_location)

  return staged_pip_packages


class _WrapCallable(beam.PTransform):
  """Wraps a callable as a PTransform."""

  def __init__(self, fn, *args):
    super(_WrapCallable, self).__init__()
    self.fn = fn
    self.args = args

  # TODO(b/33677990): Remove apply method.
  def apply(self, input_var):
    return self.expand(input_var)

  def expand(self, input_var):
    return self.fn(input_var, *self.args)


# Because of b/29179299 AugmentTrainArgsDo is its own DoFn as opposed to
# function that we pass to a MapFn.
class _AugmentTrainArgsDo(beam.DoFn):

  def __init__(self, spec):
    self.tf_main_spec = spec

  # TODO(user): Remove the try catch after sdk update
  def process(self, element, train_files, test_files, output_dir,
              metadata_path):
    try:
      train_request = element.element.copy()
    except AttributeError:
      train_request = element.copy()
    # Force the train/test files into a list, to ensure they are extracted
    # from their Emulated Iterator.
    files = []
    files.extend(train_files)
    files = []
    files.extend(test_files)
    train_request.job_args = train_request.job_args or []
    train_request.job_args += self.tf_main_spec.construct_io_args(train_files,
                                                                  test_files,
                                                                  output_dir,
                                                                  metadata_path)
    return [train_request]
