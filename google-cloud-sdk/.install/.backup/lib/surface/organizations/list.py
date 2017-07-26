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
"""Command to list all organization IDs associated with the active user."""

from apitools.base.py import list_pager

from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.organizations import orgs_base


@base.ReleaseTracks(
    base.ReleaseTrack.GA, base.ReleaseTrack.BETA, base.ReleaseTrack.ALPHA)
class List(orgs_base.OrganizationCommand, base.ListCommand):
  """List organizations accessible by the active account.

  Lists all organizations to which the user has access. Organizations are listed
  in an unspecified order.
  """

  @staticmethod
  def Args(parser):
    parser.display_info.AddFormat(
        """
          table(
            displayName:label=DISPLAY_NAME,
            name.segment():label=ID:align=right:sort=1,
            owner.directoryCustomerId:label=DIRECTORY_CUSTOMER_ID:align=right
          )""")
    parser.display_info.AddUriFunc(orgs_base.OrganizationsUriFunc)

  def Run(self, args):
    """Run the list command."""
    messages = self.OrganizationsMessages()
    return list_pager.YieldFromList(
        self.OrganizationsClient(),
        # Note that args.filter is not included in the
        # SearchOrganizationsRequest to CRM.
        # Filtering occurs as part of the display functionality in
        # googlecloudsdk.calliope.display
        messages.SearchOrganizationsRequest(),
        method='Search',
        limit=args.limit,
        batch_size_attribute='pageSize',
        batch_size=args.page_size,
        field='organizations')
