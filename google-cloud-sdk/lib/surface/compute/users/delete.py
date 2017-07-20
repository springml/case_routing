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
"""Command for deleting users."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import lister
from googlecloudsdk.api_lib.compute import request_helper
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.api_lib.compute.users import client as users_client
from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties


class Delete(base.DeleteCommand):
  """Delete Google Compute Engine users.

  *{command}* deletes one or more Google Compute Engine users.

  ## EXAMPLES
  To delete one or more users by name, run:

    $ {command} example-user-1 example-user-2

  To delete all users for one or more owners, run:

    $ {command} example-owner-1@gmail.com example-owner-2@gmail.com --owners
  """

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--owners',
        action='store_true',
        help=('The owner of the user to be created. The owner must be an email '
              'address associated with a Google account'))

    parser.add_argument(
        'names',
        metavar='NAME',
        nargs='+',
        help='The names of the users to delete.')

  def GetOwnerAccounts(self, client, owners):
    """Look up all users on the current project owned by the list of owners."""
    requests = []
    for owner in owners:
      requests += lister.FormatListRequests(
          client.users,
          properties.VALUES.core.project.GetOrFail(), None, None,
          'owner eq ' + owner)
    errors = []
    responses = request_helper.MakeRequests(
        requests=requests,
        http=client.http,
        batch_url='https://www.googleapis.com/batch/',
        errors=errors)

    if errors:
      utils.RaiseException(errors, users_client.UserException, error_message=(
          'Could not get users for owners:'))
    return [response.name for response in responses]

  def Run(self, args):
    """Issues requests necessary for deleting users."""
    holder = base_classes.ComputeUserAccountsApiHolder(self.ReleaseTrack())
    client = holder.client

    if args.owners:
      names = self.GetOwnerAccounts(client, args.names)
    else:
      names = args.names

    user_refs = [holder.resources.Parse(
        user,
        params={'project': properties.VALUES.core.project.GetOrFail},
        collection='clouduseraccounts.users') for user in names]

    utils.PromptForDeletion(user_refs)

    requests = []
    for user_ref in user_refs:
      request = client.MESSAGES_MODULE.ClouduseraccountsUsersDeleteRequest(
          project=user_ref.project,
          user=user_ref.Name())
      requests.append((client.users, 'Delete', request))

    errors = []
    responses = list(
        request_helper.MakeRequests(
            requests=requests,
            http=client.http,
            batch_url='https://www.googleapis.com/batch/',
            errors=errors))
    if errors:
      utils.RaiseToolException(
          errors, error_message='Could not fetch resource:')
    return responses
