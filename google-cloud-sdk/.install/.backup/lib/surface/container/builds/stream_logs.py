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
"""Stream-logs command."""


from googlecloudsdk.api_lib.cloudbuild import cloudbuild_util
from googlecloudsdk.api_lib.cloudbuild import logs as cb_logs
from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class StreamLogs(base.Command):
  """Stream the logs for a build."""

  @staticmethod
  def Args(parser):
    """Register flags for this command.

    Args:
      parser: An argparse.ArgumentParser-like object. It is mocked out in order
          to capture some information, but behaves like an ArgumentParser.
    """
    parser.add_argument(
        'build',
        completion_resource='cloudbuild.projects.builds',
        list_command_path='container builds list --uri',
        help=('The build whose logs shall be streamed. The ID of the build is '
              'printed at the end of the build submission process, or in the '
              'ID column when listing builds.'),
    )

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      Some value that we want to have printed later.
    """

    client = cloudbuild_util.GetClientInstance()
    messages = cloudbuild_util.GetMessagesModule()

    build_ref = resources.REGISTRY.Parse(
        args.build,
        params={'projectId': properties.VALUES.core.project.GetOrFail},
        collection='cloudbuild.projects.builds')

    cb_logs.CloudBuildClient(client, messages).Stream(build_ref)
