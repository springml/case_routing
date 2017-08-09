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
"""Command for deleting groups."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import request_helper
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties


class Delete(base.Command):
  """Delete Google Compute Engine groups.

  *{command}* deletes one or more Google Compute Engine groups.

  ## EXAMPLES
  To delete a group, run:

    $ {command} example-group

  To delete multiple groups, run:

    $ {command} example-group-1 example-group-2
  """

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'names',
        metavar='NAME',
        nargs='+',
        help='The names of the groups to delete.')

  def Run(self, args):
    holder = base_classes.ComputeUserAccountsApiHolder(self.ReleaseTrack())
    client = holder.client

    group_refs = [holder.resources.Parse(
        group,
        params={'project': properties.VALUES.core.project.GetOrFail},
        collection='clouduseraccounts.groups') for group in args.names]

    utils.PromptForDeletion(group_refs)

    requests = []
    for group_ref in group_refs:
      request = client.MESSAGES_MODULE.ClouduseraccountsGroupsDeleteRequest(
          project=group_ref.project,
          groupName=group_ref.Name())
      requests.append((client.groups, 'Delete', request))

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
