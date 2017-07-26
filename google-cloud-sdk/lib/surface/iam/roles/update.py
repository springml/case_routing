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
"""Command for updating a custom role."""
import httplib

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import http_retry
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.iam import base_classes
from googlecloudsdk.command_lib.iam import flags
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.core.console import console_io


class Update(base_classes.BaseIamCommand):
  """Update an IAM custom role.

  This command updates an IAM custom role.

  ## EXAMPLES

  To update a role from a Yaml file, run:

    $ {command} viewer --organization 123 --file role_file_path

  To update a role with flags, run:

    $ {command} viewer --project myproject --permissions permission1,permission2
  """

  @staticmethod
  def Args(parser):
    updated = parser.add_argument_group(
        'Updated fields',
        'The following flags determine the fields need to be updated. '
        'You can update a role by specifying the following flags, or '
        'you can update a role from a Yaml file by specifying the file flag.')
    updated.add_argument(
        '--title', help='The title of the role you want to update.')
    updated.add_argument(
        '--description', help='The description of the role you want to update.')
    updated.add_argument(
        '--stage', help='The state of the role you want to update.')
    updated.add_argument(
        '--permissions',
        help='The permissions of the role you want to set. '
        'Use commas to separate them.')
    updated.add_argument(
        '--add-permissions',
        help='The permissions you want to add to the role. '
        'Use commas to separate them.')
    updated.add_argument(
        '--remove-permissions',
        help='The permissions you want to remove from the '
        'role. Use commas to separate them.')
    parser.add_argument(
        '--file',
        help='The Yaml file you want to use to update a role. '
        'Can not be specified with other flags except role-id.')
    flags.GetOrgFlag('update').AddToParser(parser)
    flags.GetRoleFlag('update').AddToParser(parser)

  def Run(self, args):
    iam_client = apis.GetClientInstance('iam', 'v1')
    messages = apis.GetMessagesModule('iam', 'v1')
    role_name = iam_util.GetRoleName(args.organization, args.project, args.role)
    role = messages.Role()
    if args.file:
      if (args.title or args.description or args.stage or args.permissions or
          args.add_permissions or args.remove_permissions):
        raise exceptions.ConflictingArgumentsException('file', 'others')
      role = iam_util.ParseYamlToRole(args.file, messages.Role)
      if not role.etag:
        msg = ('The specified role does not contain an "etag" field '
               'identifying a specific version to replace. Updating a '
               'role without an "etag" can overwrite concurrent role '
               'changes.')
        console_io.PromptContinue(
            message=msg,
            prompt_string='Replace existing role',
            cancel_on_no=True)
      try:
        res = iam_client.organizations_roles.Patch(
            messages.IamOrganizationsRolesPatchRequest(
                name=role_name, role=role))
        iam_util.SetRoleStageIfAlpha(res)
        return res
      except apitools_exceptions.HttpError as e:
        exc = exceptions.HttpException(e)
        if exc.payload.status_code == 409:
          exc.error_format = ('Stale "etag": '
                              'Please use the etag from your latest describe '
                              'response. Or new changes have been made since '
                              'your latest describe operation. Please retry '
                              'the whole describe-update process. Or you can '
                              'leave the etag blank to overwrite concurrent '
                              'role changes.')
      raise exc

    res = self.UpdateWithFlags(args, role_name, role, iam_client, messages)
    iam_util.SetRoleStageIfAlpha(res)
    return res

  @http_retry.RetryOnHttpStatus(httplib.CONFLICT)
  def UpdateWithFlags(self, args, role_name, role, iam_client, messages):
    role, changed_fields = self.GetUpdatedRole(
        role_name, role, args.description, args.title, args.stage,
        args.permissions, args.add_permissions, args.remove_permissions,
        iam_client, messages)
    return iam_client.organizations_roles.Patch(
        messages.IamOrganizationsRolesPatchRequest(
            name=role_name, role=role, updateMask=','.join(changed_fields)))

  def GetUpdatedRole(self, role_name, role, description, title, stage,
                     permissions, add_permissions, remove_permissions,
                     iam_client, messages):
    """Gets the updated role from flags."""
    changed_fields = []
    if description is not None:
      changed_fields.append('description')
      role.description = description
    if title is not None:
      changed_fields.append('title')
      role.title = title
    if stage:
      changed_fields.append('stage')
      role.stage = iam_util.StageTypeFromString(stage)
    if permissions is not None and (add_permissions or remove_permissions):
      raise exceptions.ConflictingArgumentsException(
          '--permissions', '-add-permissions or --remove-permissions')
    if permissions is not None:
      changed_fields.append('includedPermissions')
      role.includedPermissions = permissions.split(',')
      if not permissions:
        role.includedPermissions = []
    origin_role = iam_client.organizations_roles.Get(
        messages.IamOrganizationsRolesGetRequest(name=role_name))
    if add_permissions or remove_permissions:
      permissions = set(origin_role.includedPermissions)
      changed = False
      if add_permissions:
        for permission in add_permissions.split(','):
          if permission not in permissions:
            permissions.add(permission)
            changed = True
      if remove_permissions:
        for permission in remove_permissions.split(','):
          if permission in permissions:
            permissions.remove(permission)
            changed = True
      if changed:
        changed_fields.append('includedPermissions')
      role.includedPermissions = list(permissions)
    role.etag = origin_role.etag
    return role, changed_fields
