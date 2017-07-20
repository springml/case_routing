# Copyright 2013 Google Inc. All Rights Reserved.
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
"""Sets the password of the MySQL root user."""

import getpass

from googlecloudsdk.api_lib.sql import api_util
from googlecloudsdk.api_lib.sql import operations
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib import deprecation_utils
from googlecloudsdk.command_lib.sql import flags
from googlecloudsdk.command_lib.sql import validate
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


@base.ReleaseTracks(base.ReleaseTrack.GA, base.ReleaseTrack.BETA)
@deprecation_utils.DeprecateCommandAtVersion(
    remove_version='162.0.0', remove=False, alt_command='users set-password')
class SetRootPassword(base.Command):
  """Sets the password of the MySQL root user."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    base.ASYNC_FLAG.AddToParser(parser)
    parser.add_argument(
        'instance',
        type=validate.InstanceNameRegexpValidator(),
        completer=flags.InstanceCompleter,
        help='Cloud SQL instance ID.')
    password_group = parser.add_mutually_exclusive_group(required=True)
    password_group.add_argument(
        '--password',
        '-p',
        help='The password for the root user. WARNING: Setting password using '
        'this option can potentially expose the password to other users '
        'of this machine. Instead, you can use --password-file to get the'
        ' password from a file.')
    password_group.add_argument(
        '--password-file',
        help='The path to the filename which has the password to be set. The '
        'first line of the file will be interpreted as the password to be set.')
    password_group.add_argument(
        '--prompt-for-password',
        action='store_true',
        help=('Prompt for the Cloud SQL user\'s password with character echo '
              'disabled. The password is all typed characters up to but not '
              'including the RETURN or ENTER key.'))

  def Run(self, args):
    """Sets the password of the MySQL root user.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object representing the operations resource describing the
      setRootPassword operation if the setRootPassword was successful.
    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing the
          command.
    """
    client = api_util.SqlClient(api_util.API_VERSION_DEFAULT)
    sql_client = client.sql_client
    sql_messages = client.sql_messages

    instance_ref = client.resource_parser.Parse(
        args.instance,
        params={'project': properties.VALUES.core.project.GetOrFail},
        collection='sql.instances')

    if args.prompt_for_password:
      password = getpass.getpass('Instance Password: ')
    elif args.password_file:
      with open(args.password_file) as f:
        password = f.readline().rstrip('\n')
    else:
      password = args.password

    operation_ref = None
    result_operation = sql_client.users.Update(
        sql_messages.SqlUsersUpdateRequest(
            project=instance_ref.project,
            instance=instance_ref.Name(),
            name='root',
            host='%',
            user=sql_messages.User(
                project=instance_ref.project,
                instance=instance_ref.Name(),
                name='root',
                host='%',
                password=password)))
    operation_ref = client.resource_parser.Create(
        'sql.operations',
        operation=result_operation.name,
        project=instance_ref.project)
    if args.async:
      return sql_client.operations.Get(
          sql_messages.SqlOperationsGetRequest(
              project=operation_ref.project, operation=operation_ref.operation))
    operations.OperationsV1Beta4.WaitForOperation(sql_client, operation_ref,
                                                  'Updating Cloud SQL user')

    log.status.write(
        'Set password for [{instance}].\n'.format(instance=instance_ref))

    return None
