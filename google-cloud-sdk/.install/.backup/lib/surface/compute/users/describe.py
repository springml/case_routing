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
"""Command for describing users."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import request_helper
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute.users import utils as user_utils
from googlecloudsdk.command_lib.util import gaia
from googlecloudsdk.core import properties


class Describe(base.DescribeCommand):
  """Describe a Google Compute Engine user.

  *{command}* displays all data associated with a Google Compute
  Engine user in a project.

  ## EXAMPLES
  To describe a user, run:

    $ {command} example-user

  To describe the default user mapped from the currently authenticated
  Google account email, run:

    $ {command}
  """

  @staticmethod
  def Args(parser):
    user_utils.AddUserArgument(parser, 'describe')

  def Run(self, args):
    """Issues requests necessary for describing users."""
    compute_holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    holder = base_classes.ComputeUserAccountsApiHolder(self.ReleaseTrack())
    client = holder.client

    user = args.name
    if not user:
      user = gaia.GetDefaultAccountName(
          compute_holder.client.apitools_client.http)

    user_ref = holder.resources.Parse(
        user,
        params={'project': properties.VALUES.core.project.GetOrFail},
        collection='clouduseraccounts.users')

    request = client.MESSAGES_MODULE.ClouduseraccountsUsersGetRequest(
        project=user_ref.project,
        user=user_ref.Name())

    errors = []
    responses = list(
        request_helper.MakeRequests(
            requests=[(client.users, 'Get', request)],
            http=client.http,
            batch_url='https://www.googleapis.com/batch/',
            errors=errors))
    if errors:
      utils.RaiseToolException(
          errors, error_message='Could not fetch resource:')
    return responses
