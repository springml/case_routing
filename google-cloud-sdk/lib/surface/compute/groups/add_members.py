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
"""Command for adding a user to a group."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import request_helper
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties


class AddMembers(base.SilentCommand):
  """Add a user to a Google Compute Engine group.

  *{command}* adds a users to a Google Compute Engine group.
  """

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'names',
        metavar='NAME',
        nargs='+',
        help='The names of the groups to add members to.')

    parser.add_argument(
        '--members',
        metavar='USERNAME',
        required=True,
        type=arg_parsers.ArgList(min_length=1),
        help='The names or fully-qualified URLs of the users to add.')

  def Run(self, args):
    holder = base_classes.ComputeUserAccountsApiHolder(self.ReleaseTrack())
    client = holder.client

    user_refs = [holder.resources.Parse(
        user,
        params={'project': properties.VALUES.core.project.GetOrFail},
        collection='clouduseraccounts.users') for user in args.members]

    group_refs = [holder.resources.Parse(
        group,
        params={'project': properties.VALUES.core.project.GetOrFail},
        collection='clouduseraccounts.groups') for group in args.names]

    user_selflinks = [user_ref.SelfLink() for user_ref in user_refs]
    requests = []
    for group_ref in group_refs:
      new_member = client.MESSAGES_MODULE.GroupsAddMemberRequest(
          users=user_selflinks)

      request = client.MESSAGES_MODULE.ClouduseraccountsGroupsAddMemberRequest(
          project=group_ref.project,
          groupsAddMemberRequest=new_member,
          groupName=group_ref.Name())
      requests.append((client.groups, 'AddMember', request))

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


AddMembers.detailed_help = {
    'EXAMPLES': """\
        To add a user to a group, run:

          $ {command} example-group --members example-user

        To add multiple users to multiple groups, run:

          $ {command} example-group-1 example-group-2 --members example-user-1,example-user-2
        """,
}
