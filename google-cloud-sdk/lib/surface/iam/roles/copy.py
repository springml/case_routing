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
"""Command for creating a role from an existing role."""

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope.exceptions import RequiredArgumentException
from googlecloudsdk.command_lib.iam import base_classes
from googlecloudsdk.command_lib.iam import iam_util


class Copy(base_classes.BaseIamCommand):
  r"""Create a role from an existing role.

  This command creates a role from an existing role.

  ## EXAMPLES

  To create a role from an existing role, run:

    $ {command} --source viewer --destination reader \
        --source-organization org1 --dest-organization org1
  """

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--source',
        help='The source role name or id.'
        'For curated roles, for example: roles/viewer.'
        'For custom roles, for example: viewer.')
    parser.add_argument(
        '--destination',
        help='The destination role id for the new custom '
        'role. For example: viewer.')
    parser.add_argument(
        '--source-organization',
        help='The organization of the source role '
        'if it is an custom role.')
    parser.add_argument(
        '--dest-organization', help='The organization of the destination role.')
    parser.add_argument(
        '--source-project',
        help='The project of the source role '
        'if it is an custom role.')
    parser.add_argument(
        '--dest-project', help='The project of the destination role.')

  def Run(self, args):
    iam_client = apis.GetClientInstance('iam', 'v1')
    messages = apis.GetMessagesModule('iam', 'v1')
    if args.source is None:
      raise RequiredArgumentException('source', 'the source role is required.')
    if args.destination is None:
      raise RequiredArgumentException('destination',
                                      'the destination role is required.')
    source_role_name = iam_util.GetRoleName(
        args.source_organization,
        args.source_project,
        args.source,
        attribute='the source custom role',
        parameter_name='source')
    dest_parent = iam_util.GetParentName(
        args.dest_organization,
        args.dest_project,
        attribute='the destination custom role')

    source_role = iam_client.organizations_roles.Get(
        messages.IamOrganizationsRolesGetRequest(name=source_role_name))

    new_role = messages.Role(
        title=source_role.title,
        description=source_role.description,
        includedPermissions=source_role.includedPermissions)

    if source_role.includedPermissions:
      full_resource_name = '//cloudresourcemanager.googleapis.com/'
      if args.dest_project:
        full_resource_name += 'projects/{0}'.format(args.dest_project)
      else:
        full_resource_name += 'organizations/{0}'.format(args.dest_organization)
      valid_permissions = []
      token = None
      source_permissions = set(source_role.includedPermissions)
      while len(source_role.includedPermissions) != len(valid_permissions):
        resp = iam_client.permissions.QueryTestablePermissions(
            messages.QueryTestablePermissionsRequest(
                fullResourceName=full_resource_name, pageToken=token))
        for testable_permission in resp.permissions:
          if (testable_permission.name in source_permissions and
              (testable_permission.customRolesSupportLevel !=
               messages.Permission.CustomRolesSupportLevelValueValuesEnum.
               NOT_SUPPORTED)):
            valid_permissions.append(testable_permission.name)
        token = resp.nextPageToken
        if not token:
          break
      new_role.includedPermissions = valid_permissions

    result = iam_client.organizations_roles.Create(
        messages.IamOrganizationsRolesCreateRequest(
            createRoleRequest=messages.CreateRoleRequest(
                role=new_role, roleId=args.destination),
            parent=dest_parent))
    iam_util.SetRoleStageIfAlpha(result)
    return result
