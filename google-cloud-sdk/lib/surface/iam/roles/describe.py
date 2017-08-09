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
"""Command for describing a role."""

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.iam import base_classes
from googlecloudsdk.command_lib.iam import flags
from googlecloudsdk.command_lib.iam import iam_util


class Describe(base_classes.BaseIamCommand, base.DescribeCommand):
  """Show metadata for a role.

  This command shows metadata for a role.

  This command can fail for the following reasons:
  * The role specified does not exist.
  * The active user does not have permission to access the given role.

  ## EXAMPLES

  To print metadata for a role of an organization, run:

    $ {command} --organization 1234567 viewer

  To print metadata for a role of a project, run:

    $ {command} --project myproject viewer

  To print metadata for a predefined role, run:

    $ {command} roles/viewer
  """

  @staticmethod
  def Args(parser):
    flags.GetOrgFlag('describe').AddToParser(parser)
    flags.GetRoleFlag('describe').AddToParser(parser)

  def Run(self, args):
    iam_client = apis.GetClientInstance('iam', 'v1')
    messages = apis.GetMessagesModule('iam', 'v1')
    role_name = iam_util.GetRoleName(args.organization, args.project, args.role)
    res = iam_client.organizations_roles.Get(
        messages.IamOrganizationsRolesGetRequest(name=role_name))
    iam_util.SetRoleStageIfAlpha(res)
    return res
