# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Command to describe speech operations."""

from googlecloudsdk.api_lib.ml.speech import speech_api_client
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.ml.speech import speech_command_util
from googlecloudsdk.core import resources


class Describe(base.DescribeCommand):

  """Get description of a long-running speech recognition operation.

  Get information about a long-running speech recognition operation.

  {auth_hints}
  """

  detailed_help = {'auth_hints': speech_command_util.SPEECH_AUTH_HELP}

  @staticmethod
  def Args(parser):
    # Format in json because ML API users are expected to prefer json.
    parser.display_info.AddFormat('json')
    parser.add_argument('operation',
                        help=('The ID of the operation to describe.'))

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Raises:
      googlecloudsdk.api_lib.util.exceptions.HttpException, if there is an
          error returned by the API.

    Returns:
      The results of the Get request.
    """
    operation_ref = resources.REGISTRY.Parse(
        args.operation,
        collection='speech.operations')
    speech_client = speech_api_client.SpeechClient()
    return speech_client.DescribeOperation(operation_ref)

