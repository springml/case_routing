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
"""Command to create a custom role for a project or an organization."""

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.iam import base_classes
from googlecloudsdk.command_lib.iam import flags
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.core import log


class Create(base_classes.BaseIamCommand):
  r"""Create a custom role for a project or an organization.

  This command creates a custom role with the provided information.

  ## EXAMPLES

  To create a custom role from a yaml file, run:

    $ {command} viewer --organization 12345 --file role_file_path

  To create a custom role with flags, run:

    $ {command} editor --project myproject --title myrole --description \
        "Have access to get and update the project" --permissions \
        resourcemanager.projects.get,resourcemanager.projects.update
  """

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--title', help='The title of the role you want to create.')
    parser.add_argument(
        '--description', help='The description of the role you want to create.')
    parser.add_argument(
        '--stage', help='The state of the role you want to create.')
    parser.add_argument(
        '--permissions',
        help='The permissions of the role you want to create. '
        'Use commas to separate them.')
    parser.add_argument(
        '--file',
        help='The Yaml file you want to use to create a role. '
        'Can not be specified with other flags except role-id.')
    flags.GetOrgFlag('create').AddToParser(parser)
    flags.GetCustomRoleFlag('create').AddToParser(parser)

  def Run(self, args):
    iam_client = apis.GetClientInstance('iam', 'v1')
    messages = apis.GetMessagesModule('iam', 'v1')
    parent_name = iam_util.GetParentName(args.organization, args.project)
    if args.file:
      if args.title or args.description or args.stage or args.permissions:
        raise exceptions.ConflictingArgumentsException('file', 'others')
      role = iam_util.ParseYamlToRole(args.file, messages.Role)
      role.name = None
      role.etag = None
    else:
      role = messages.Role(title=args.title, description=args.description)
      if args.permissions:
        role.includedPermissions = args.permissions.split(',')
      if args.stage:
        role.stage = iam_util.StageTypeFromString(args.stage)

    if not role.title:
      role.title = args.role

    result = iam_client.organizations_roles.Create(
        messages.IamOrganizationsRolesCreateRequest(
            createRoleRequest=messages.CreateRoleRequest(
                role=role, roleId=args.role),
            parent=parent_name))
    log.CreatedResource(args.role, kind='role')
    iam_util.SetRoleStageIfAlpha(result)
    return result
