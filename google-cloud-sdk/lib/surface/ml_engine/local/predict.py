# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""ml-engine local predict command."""
import json
import subprocess

from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.ml_engine import local_predict
from googlecloudsdk.command_lib.ml_engine import predict_utilities
from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.util import files


class InvalidInstancesFileError(core_exceptions.Error):
  pass


class LocalPredictRuntimeError(core_exceptions.Error):
  """Indicates that some error happened within local_predict."""
  pass


class LocalPredictEnvironmentError(core_exceptions.Error):
  """Indicates that some error happened within local_predict."""
  pass


class InvalidReturnValueError(core_exceptions.Error):
  """Indicates that the return value from local_predict has some error."""
  pass


def _RunPredict(args):
  """Run ML Engine local prediction."""
  instances = predict_utilities.ReadInstancesFromArgs(args.json_instances,
                                                      args.text_instances)
  sdk_root = config.Paths().sdk_root
  if not sdk_root:
    raise LocalPredictEnvironmentError(
        'You must be running an installed Cloud SDK to perform local '
        'prediction.')
  env = {'CLOUDSDK_ROOT': sdk_root}
  # We want to use whatever the user's Python was, before the Cloud SDK started
  # changing the PATH. That's where Tensorflow is installed.
  python_executables = files.SearchForExecutableOnPath('python')
  if not python_executables:
    # This doesn't have to be actionable because things are probably beyond help
    # at this point.
    raise LocalPredictEnvironmentError(
        'Something has gone really wrong; we can\'t find a valid Python '
        'executable on your PATH.')
  python_executable = python_executables[0]
  # Start local prediction in a subprocess.
  proc = subprocess.Popen(
      [python_executable, local_predict.__file__,
       '--model-dir', args.model_dir],
      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
      env=env)

  # Pass the instances to the process that actually runs local prediction.
  for instance in instances:
    proc.stdin.write(json.dumps(instance) + '\n')
  proc.stdin.flush()

  # Get the results for the local prediction.
  output, err = proc.communicate()
  if proc.returncode != 0:
    raise LocalPredictRuntimeError(err)
  if err:
    log.warn(err)

  try:
    return json.loads(output)
  except ValueError:
    raise InvalidReturnValueError('The output for prediction is not '
                                  'in JSON format: ' + output)


def _AddLocalPredictArgs(parser):
  """Add arguments for `gcloud ml-engine local predict` command."""
  parser.add_argument('--model-dir', required=True, help='Path to the model.')
  group = parser.add_mutually_exclusive_group(required=True)
  group.add_argument(
      '--json-instances',
      help="""\
      Path to a local file from which instances are read.
      Instances are in JSON format; newline delimited.

      An example of the JSON instances file:

          {"images": [0.0, ..., 0.1], "key": 3}
          {"images": [0.0, ..., 0.1], "key": 2}
          ...

      This flag accepts "-" for stdin.
      """)
  group.add_argument(
      '--text-instances',
      help="""\
      Path to a local file from which instances are read.
      Instances are in UTF-8 encoded text format; newline delimited.

      An example of the text instances file:

          107,4.9,2.5,4.5,1.7
          100,5.7,2.8,4.1,1.3
          ...

      This flag accepts "-" for stdin.
      """)


class Predict(base.Command):
  """Run prediction locally."""

  @staticmethod
  def Args(parser):
    _AddLocalPredictArgs(parser)

  def Run(self, args):
    return _RunPredict(args)


_DETAILED_HELP = {
    'DESCRIPTION': """\
*{command}* performs prediction locally with the given instances. It requires
the TensorFlow SDK be installed locally.
"""
}


Predict.detailed_help = _DETAILED_HELP
