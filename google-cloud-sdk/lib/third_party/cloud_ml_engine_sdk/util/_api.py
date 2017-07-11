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
"""Implements Google Cloud ML HTTP API wrapper."""

import datetime
import httplib
import logging
import os
import subprocess
import time

import oauth2client.client as client
import yaml


from google.cloud.ml.util._exceptions import _RequestException  # pylint: disable=g-importing-member
from google.cloud.ml.util._http import _Http  # pylint: disable=g-importing-member


class ApiBase(object):
  """A helper class to issue Google Cloud ML HTTP requests.

  The base class provides functionality common to all versions of the API.
  """
  _JOBS_PATH = '/projects/%s/jobs/%s'
  _OAUTH_SCOPES = ['https://www.googleapis.com/auth/cloud-platform',]

  def __init__(self, credential=None, project_id=None, endpoint=None):
    """Initializes the Google Cloud ML helper class.

    The helper is created with credential and project information.

    Args:
      credential: a GoogleCredential to use with the API calls.  If None,
        default credentials are used.
      project_id: the Google Cloud project Id to use with the calls.  If None,
        the default gcloud project is used.
      endpoint: The endpoint for the Cloud ML service.
    """
    self._credentials = credential
    self._project_id = project_id
    self._endpoint = endpoint

    # Check the credential.
    if not credential:
      self._credentials = client.GoogleCredentials.get_application_default()
    if self._credentials.create_scoped_required():
      self._credentials = self._credentials.create_scoped(self._OAUTH_SCOPES)

    # Check the project id.
    if not project_id:
      logging.info('Fetching the default project from gcloud.')
      get_project = subprocess.Popen(
          ['gcloud', 'config', 'list', 'project', '--format', 'yaml', '-q'],
          stdout=subprocess.PIPE,
          stderr=subprocess.PIPE)
      with get_project.stdout as project_config:
        project_data = yaml.safe_load(project_config)
        self._project_id = project_data['core']['project']
      get_project.wait()

  def get_operation(self, op_name):
    """Return the specified operation.

    Args:
      op_name: The name of the operation. This should just be the
        final piece of the url; i.e. the full url will be
        projects/{project}/operations/{op_name}

    Returns:
      op: The operation or None if it doesn't exist.
    """
    url = self._endpoint + op_name
    try:
      result = _Http.request(url, credentials=self._credentials)
    except _RequestException as e:
      if (e.error_code == httplib.NOT_FOUND or
          e.error_code == httplib.BAD_REQUEST):
        # API returns NOT_FOUND if the job isn't defined.
        # TODO(user): The API is currently returning BAD_REQUEST for these.
        # But we know our requests are well formed, so assume those are not
        # found errors as well.
        return None
      # Reraise the exception.
      raise
    return result

  def wait_for_operation(self,
                         op_name,
                         timeout=datetime.timedelta(hours=1),
                         polling_interval=datetime.timedelta(seconds=5)):
    """Wait for the specified operation to complete.

    Args:
      op_name: Name of the operation to wait for.
      timeout: A datetime.timedelta expressing the amount of time to wait before
        giving up.
      polling_interval: A datetime.timedelta to represent the amount of time to
        wait between requests polling for the operation status.

    Returns:
      op: The final operation.

    Raises:
      TimeoutError: if we timeout waiting for the operation to complete.
    """
    endtime = datetime.datetime.now() + timeout
    if not op_name.startswith('/'):
      op_name = '/' + op_name
    while True:
      op = self.get_operation(op_name)
      done = op.get('done', False)
      if done:
        return op
      if datetime.datetime.now() > endtime:
        raise TimeoutError('Timed out waiting for op: {0} to complete.'.format(
            op_name))
      time.sleep(polling_interval.total_seconds())

  def get_job(self, job_name):
    """Return the specified job."""
    op_name = self._JOBS_PATH % (self._project_id, job_name)
    return self.get_operation(op_name)

  def wait_for_job(self,
                   job_name,
                   timeout=datetime.timedelta(hours=1),
                   polling_interval=datetime.timedelta(seconds=5)):
    """Wait for the specified job to complete.

    Args:
      job_name: the job tame.
      timeout: if the job takes longer than this, TimeoutError is raised.
      polling_interval: time between query intervals.

    Raises:
      TimeoutError: if job talkes longer than timeout.

    Returns:
      The HTTP request result.
    """
    endtime = datetime.datetime.now() + timeout
    op_name = self._JOBS_PATH % (self._project_id, job_name)
    while True:
      job = self.get_operation(op_name)
      state = job.get('state', 'RUNNING')
      if state in ['SUCCEEDED', 'FAILED', 'CANCELLED', 'CANCELLING']:
        return job
      if datetime.datetime.now() > endtime:
        raise TimeoutError('Timed out waiting for job: {0} to complete.'.format(
            job_name))
      time.sleep(polling_interval.total_seconds())


class ApiBeta(ApiBase):
  """Client library for the v1beta1 API."""

  _API_VERSION = 'v1beta1'
  _DEFAULT_ENDPOINT = 'https://ml.googleapis.com/'

  def __init__(self, credential=None, project_id=None, endpoint=None):
    """Initializes the Google Cloud ML helper class.

    The helper is created with credential and project information.

    Args:
      credential: a GoogleCredential to use with the API calls.  If None,
        default credentials are used.
      project_id: the Google Cloud project Id to use with the calls.  If None,
        the default gcloud project is used.
      endpoint: (Optional) The endpoint for the Cloud ML service. If unset,
        but the CLOUDSDK_API_ENDPOINT_OVERRIDES_ML environment variable is
        present, that is used. Otherwise, the default value is used.
    """
    # Super call does not init endpoint if it is null.
    super(ApiBeta, self).__init__(credential, project_id, endpoint)

    # Init endpoint if needed. The user can explicitly pass None or the empty
    # string for endpoint, but we still set the default correctly.
    if not self._endpoint:
      self._endpoint = (
          os.environ.get('CLOUDSDK_API_ENDPOINT_OVERRIDES_ML',
                         self._DEFAULT_ENDPOINT) + self._API_VERSION)
    if self._endpoint is not self._DEFAULT_ENDPOINT + self._API_VERSION:
      logging.info('Using endpoint: %s', self._endpoint)
    self.default_runtime_version = (
        os.environ.get('CLOUDSDK_ML_DEFAULT_RUNTIME_VERSION'))

  def submit_batch_prediction_job(self,
                                  name,
                                  input_paths,
                                  output_path,
                                  model_name=None,
                                  version_name=None,
                                  data_format='TEXT',
                                  region=None,
                                  # already deprecated, so pylint: disable=unused-argument
                                  runtime_version=None):
    """Call the API to submit a batch prediction job.

    Args:
      name: The name to assign the prediction job.
      input_paths: URIs that contains the features to be predicted on.
      output_path: URI where the results of the prediction will be written.
      model_name: uri of trained model file
      version_name: (Optional) name of the version to be used for model
      data_format: The format of the input data, either TEXT or TF_RECORD.
      region: region the job is assigned to.
      runtime_version: (Optional) the Google Cloud ML runtime version to use.

    Returns:
      The HTTP request result.
    """
    url = '{0}/projects/{1}/jobs'.format(self._endpoint, self._project_id)

    data = {'job_id': name,}
    prediction_input = {
        'input_paths': input_paths,
        'output_path': output_path,
        'data_format': data_format,
        'region': region
    }
    if version_name:
      prediction_input['version_name'] = (
          'projects/{0}/models/{1}/versions/{2}'.format(self._project_id,
                                                        model_name,
                                                        version_name))
    else:
      prediction_input['model_name'] = ('projects/{0}/models/{1}'.format(
          self._project_id, model_name))
    data['prediction_input'] = prediction_input

    return _Http.request(url, data=data, credentials=self._credentials)

  def submit_training_job(self,
                          name,
                          package_uris=None,
                          python_module='',
                          args=None,
                          hyperparameters=None,
                          region=None,
                          scale_tier=None,
                          master_type=None,
                          worker_type=None,
                          ps_type=None,
                          worker_count=None,
                          ps_count=None,
                          runtime_version=None):
    """Submit a training job.

    Args:
      name: The name to assign the training job. This will be the final
        piece of the operation id; i.e. the operation id will be
        projects/{project}/operations/{name}.
      package_uris: List of URIs of the tarball containing the training code.
      python_module: String indicating the entry point in the python code for
        the training job.
      args: (Optional) Extra arguments for the job. These are passed to
        the main program that is launched by the Cloud ML service. List of flag
        formatted strings, for example: ['--my_flag=a',].
      hyperparameters: (Optional) Hyperparameter config to use for the job.
      region: (Optional) Google Cloud Region in which to run training.
      scale_tier: ML scale tier, specifying the machine types and number of
        workers to use for the job.
      master_type: (Optional) the master machine type.
      worker_type: (Optional) the worker machine type.
      ps_type: (Optional) the parameter server machine type.
      worker_count: (Optional) the number of worker machines.
      ps_count: (Optional) the numer of parameter server machines.
      runtime_version: (Optional) the Google Cloud ML runtime version to use.

    Returns:
      The operation describing the training job.
    """

    url = '{0}/projects/{1}/jobs'.format(self._endpoint, self._project_id)

    data = {'job_id': name,}
    training_input = {
        'package_uris': package_uris,
        'python_module': python_module,
        'scale_tier': scale_tier
    }

    if args:
      training_input['args'] = args
    if hyperparameters:
      training_input['hyperparameters'] = hyperparameters
    if region:
      training_input['region'] = region
    if master_type:
      training_input['master_type'] = master_type
    if worker_type:
      training_input['worker_type'] = worker_type
    if ps_type:
      training_input['parameter_server_type'] = ps_type
    if worker_count:
      training_input['worker_count'] = worker_count
    if ps_count:
      training_input['parameter_server_count'] = ps_count
    runtime_version = runtime_version or self.default_runtime_version
    if runtime_version:
      training_input['runtime_version'] = runtime_version

    data['training_input'] = training_input

    return _Http.request(url, data=data, credentials=self._credentials)

  def cancel_operation(self, op_name):
    """Cancel a training job.

    Args:
      op_name: The op_name corresponding to the job being cancelled.

    Returns:
      The result of cancellation of the job.
    """
    url = '{0}/projects/{1}/jobs/{2}:cancel'.format(self._endpoint,
                                                    self._project_id, op_name)
    data = {}

    return _Http.request(url, data=data, credentials=self._credentials)

  def cancel_job(self, job_name):
    """Cancel a training job."""
    return self.cancel_operation(job_name)

  def create_model(self, name):
    """Create a model.

    Args:
      name: The name of the model. This name only needs to be unique within
        a project and will be the final piece of the fully-
        qualified name, i.e., the full model name will be:
          /projects/{project}/models/{name}.

    Returns:
      The model object.
    """
    url = '{0}/projects/{1}/models'.format(self._endpoint, self._project_id)

    data = {'name': name}
    try:
      return _Http.request(url, data=data, credentials=self._credentials)
    except _RequestException as e:
      if e.error_code == httplib.CONFLICT:
        # The model already exists.
        return None
      raise

  def delete_model(self, model_name):
    """Delete the specified model."""
    url = '{0}/projects/{1}/models/{2}?$trace=producer'.format(self._endpoint,
                                                               self._project_id,
                                                               model_name)

    return _Http.request(url, method='DELETE', credentials=self._credentials)

  def deploy_version(self,
                     model_name,
                     version_name,
                     origin_uri,
                     is_default=False,
                     runtime_version=None):
    """Deploys a version to the service.

    Args:
      model_name: The name of the model for which this is a version. It should
        be the "short name", i.e., the last part of the fully-qualified name:
        /projects/{project}/models/{model_name}.
      version_name: The name of this version. This only need to be unique
        for the given model. This is the last part of the fully-qualified
        version name:
        /projects/{project}/models/{model_name}/versions/{version_name}
      origin_uri: The URI pointing to the exported model which will be
        deployed to the service.
      is_default: Whether or not this model should be set as the default.
      runtime_version: (Optional) the Google Cloud ML runtime version to use.

    Returns:
      The version object.
    """
    url = '{0}/projects/{1}/models/{2}/versions'.format(self._endpoint,
                                                        self._project_id,
                                                        model_name)
    data = {
        'name': version_name,
        'deployment_uri': origin_uri,
        'is_default': is_default
    }
    runtime_version = runtime_version or self.default_runtime_version
    if runtime_version:
      data['runtime_version'] = runtime_version
    return _Http.request(url, data=data, credentials=self._credentials)

  def get_version(self, model_name, version_name):
    url = '{0}/projects/{1}/models/{2}/versions/{3}'.format(self._endpoint,
                                                            self._project_id,
                                                            model_name,
                                                            version_name)
    return _Http.request(url, credentials=self._credentials)


class TimeoutError(Exception):
  """An error indicating an operation timed out."""
