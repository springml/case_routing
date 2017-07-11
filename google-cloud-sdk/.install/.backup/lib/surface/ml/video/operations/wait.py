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
"""Command to wait for the results of video operations."""

from googlecloudsdk.api_lib.ml.video import video_client
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.ml.video import video_command_util
from googlecloudsdk.command_lib.resource_manager import flags
from googlecloudsdk.core import resources


class Wait(base.DescribeCommand):
  """Poll long-running video analysis operation until it completes.

  Poll a long-running video analysis operation until it completes. When
  the operation is complete, this command will display the results of the
  analysis.

  {auth_hints}
  """
  detailed_help = {'auth_hints': video_command_util.SERVICE_ACCOUNT_HELP}

  @staticmethod
  def Args(parser):
    # Format in json because ML API users are expected to prefer json.
    parser.display_info.AddFormat('json')
    flags.OperationIdArg('to poll until complete').AddToParser(parser)

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Raises:
      googlecloudsdk.api_lib.util.exceptions.HttpException, if there is an
          error returned by the API.

    Returns:
      videointelligence_v1beta1_messages.
      GoogleCloudVideointelligenceV1AnnotateVideoResponse: the result of the
        analysis.
    """
    operation_ref = resources.REGISTRY.Parse(
        args.id,
        collection='videointelligence.operations')
    client = video_client.VideoClient()
    return client.WaitOperation(operation_ref)
