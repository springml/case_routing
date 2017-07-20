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

"""The `app update` command."""

from googlecloudsdk.api_lib.app.api import appengine_app_update_api_client
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core.console import progress_tracker


_DETAILED_HELP = {
    'brief': ('Updates an App Engine application.'),
    'DESCRIPTION': """\
        This command is used to update settings on an app engine application.

        """,
    'EXAMPLES': """\
        To enable split health checks on an application:

          $ {command} --split-health-checks=true

        """,
}


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class Update(base.UpdateCommand):
  """Updates an App Engine application."""

  @staticmethod
  def Args(parser):
    def Bool(s):
      return s.lower() in ['true', '1']

    parser.add_argument(
        '--split-health-checks',
        required=False, type=Bool, default=None,
        help='(true/false) Enables split health checks by default on new'
             ' deployments.')

  def Run(self, args):
    api_client = (appengine_app_update_api_client.
                  AppengineAppUpdateApiClient.GetApiClient())

    if args.split_health_checks is not None:
      with progress_tracker.ProgressTracker(
          'Updating the app [{0}]'.format(api_client.project)):
        return api_client.PatchApplication(args.split_health_checks)
    else:
      log.status.Print('Nothing to update.')


Update.detailed_help = _DETAILED_HELP
