# Copyright 2015 Google Inc. All Rights Reserved.
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
"""Command for creating groups."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import request_helper
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute.groups import flags
from googlecloudsdk.core import properties


class Create(base.CreateCommand):
  """Create Google Compute Engine groups."""

  @staticmethod
  def Args(parser):
    parser.display_info.AddFormat(flags.DEFAULT_LIST_FORMAT)
    parser.add_argument(
        'names',
        metavar='NAME',
        nargs='+',
        help='The name of the group to create.')

    parser.add_argument(
        '--description',
        help='An optional, textual description for the group being created.')

  def Run(self, args):
    """Issues requests necessary for adding users."""
    holder = base_classes.ComputeUserAccountsApiHolder(self.ReleaseTrack())
    client = holder.client

    group_refs = [holder.resources.Parse(
        group,
        params={'project': properties.VALUES.core.project.GetOrFail},
        collection='clouduseraccounts.groups') for group in args.names]

    requests = []
    for group_ref in group_refs:

      group = client.MESSAGES_MODULE.Group(
          name=group_ref.Name(),
          description=args.description,
      )

      request = client.MESSAGES_MODULE.ClouduseraccountsGroupsInsertRequest(
          project=group_ref.project,
          group=group)
      requests.append((client.groups, 'Insert', request))

    errors = []
    responses = list(request_helper.MakeRequests(
        requests=requests,
        http=client.http,
        batch_url='https://www.googleapis.com/batch/',
        errors=errors))
    if errors:
      utils.RaiseToolException(
          errors, error_message='Could not fetch resource:')
    return responses


Create.detailed_help = {
    'brief': 'Create Google Compute Engine groups',
    'DESCRIPTION': """\
        *{command}* creates Google Compute Engine groups.
        """,
    'EXAMPLES': """\
        To create a group, run:

          $ {command} example-group
        """,
}
