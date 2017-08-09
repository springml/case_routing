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
"""Command for creating users."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import request_helper
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute.users import utils as user_utils
from googlecloudsdk.command_lib.util import gaia
from googlecloudsdk.core import properties


class Create(base.CreateCommand):
  """Create Google Compute Engine users."""

  @staticmethod
  def Args(parser):
    parser.display_info.AddFormat(user_utils.DEFAULT_LIST_FORMAT)
    parser.add_argument(
        '--owner',
        help=('The owner of the user to be created. The owner must be an email '
              'address associated with a Google account'))

    parser.add_argument(
        '--description',
        help='An optional, textual description for the user being created.')

    user_utils.AddUserArgument(parser, 'create')

  def Run(self, args):
    """Issues requests necessary for adding users."""
    holder = base_classes.ComputeUserAccountsApiHolder(self.ReleaseTrack())
    client = holder.client

    owner = args.owner
    if not owner:
      owner = gaia.GetAuthenticatedGaiaEmail(client.http)

    name = args.name
    if not name:
      name = gaia.MapGaiaEmailToDefaultAccountName(owner)

    user_ref = holder.resources.Parse(
        name,
        params={'project': properties.VALUES.core.project.GetOrFail},
        collection='clouduseraccounts.users')

    user = client.MESSAGES_MODULE.User(
        name=user_ref.Name(),
        description=args.description,
        owner=owner,
    )

    request = client.MESSAGES_MODULE.ClouduseraccountsUsersInsertRequest(
        project=user_ref.project,
        user=user)

    errors = []
    responses = list(
        request_helper.MakeRequests(
            requests=[(client.users, 'Insert', request)],
            http=client.http,
            batch_url='https://www.googleapis.com/batch/',
            errors=errors))
    if errors:
      utils.RaiseToolException(
          errors, error_message='Could not fetch resource:')
    return responses


Create.detailed_help = {
    'brief': 'Create Google Compute Engine users',
    'DESCRIPTION': """\
        *{command}* creates a Google Compute Engine user.
        """,
    'EXAMPLES': """\
        To create a user with the specified name and owner, run:

          $ {command} example-user --owner example-owner@google.com

        To create a user with the currently authenticated Google account as
        owner and a default username mapped from that account's email, run:

          $ {command}

        To create a user with the specified name and the currently
        authenticated Google account as owner, run:

          $ {command} example-user

        To create a user with the specified owner and a default username
        mapped from the owner email, run:

          $ {command} --owner example-owner@google.com

        """,
}
