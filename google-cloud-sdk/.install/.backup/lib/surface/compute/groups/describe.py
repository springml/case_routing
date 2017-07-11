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
"""Command for describing groups."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties


class Describe(base.Command):
  """Describe a Google Compute Engine group.

  *{command}* displays all data associated with a Google Compute
  Engine group in a project.

  ## EXAMPLES
  To describe a user, run:

    $ {command} example-user
  """

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'name',
        metavar='NAME',
        help='The name of the group to describe.')

  def Run(self, args):
    """Issues requests necessary for describing groups."""
    compute_holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    holder = base_classes.ComputeUserAccountsApiHolder(self.ReleaseTrack())
    client = holder.client

    group_ref = holder.resources.Parse(
        args.name,
        params={'project': properties.VALUES.core.project.GetOrFail},
        collection='clouduseraccounts.groups')

    request = client.MESSAGES_MODULE.ClouduseraccountsGroupsGetRequest(
        project=group_ref.project,
        groupName=group_ref.Name())

    return compute_holder.client.MakeRequests([(client.groups, 'Get', request)])
