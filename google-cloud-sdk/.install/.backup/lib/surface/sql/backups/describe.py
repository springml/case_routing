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
"""Retrieves information about a backup."""

from googlecloudsdk.api_lib.sql import api_util
from googlecloudsdk.api_lib.sql import validate
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.sql import flags
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import times


@base.ReleaseTracks(base.ReleaseTrack.GA, base.ReleaseTrack.BETA)
class Describe(base.DescribeCommand):
  """Retrieves information about a backup.

  Retrieves information about a backup.
  """

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument(
        'id',
        # TODO(b/21877717): uncomment validation after deprecation period.
        # type=arg_parsers.BoundedInt(1, sys.maxint),
        help='The ID of the Backup Run.')
    flags.INSTANCE_FLAG.AddToParser(parser)

  def _GetById(self, id_integer, args):
    # If user passes ID, user v1beta4 API.
    client = api_util.SqlClient(api_util.API_VERSION_DEFAULT)
    sql_client = client.sql_client
    sql_messages = client.sql_messages

    instance_ref = client.resource_parser.Parse(
        args.instance,
        params={'project': properties.VALUES.core.project.GetOrFail},
        collection='sql.instances')

    request = sql_messages.SqlBackupRunsGetRequest(
        project=instance_ref.project,
        instance=instance_ref.instance,
        # TODO(b/21877717): Remove cast after deprecation period.
        id=id_integer)
    return sql_client.backupRuns.Get(request)

  def _GetByDatetime(self, datetime, args):
    # Backwards compatibility during deprecation period.
    # If user passes DUE_TIME instead of ID, use v1beta3 API.
    client = api_util.SqlClient(api_util.API_VERSION_FALLBACK)
    sql_client = client.sql_client
    sql_messages = client.sql_messages
    log.warning('Starting on 2017-06-30, DUE_TIME will no longer be valid: Use '
                'the ID argument instead to retrieve a backup. You can start '
                'using ID now.')

    instance_ref = client.resource_parser.Parse(
        args.instance,
        params={'project': properties.VALUES.core.project.GetOrFail},
        collection='sql.instances')

    instance = sql_client.instances.Get(
        sql_messages.SqlInstancesGetRequest(
            project=instance_ref.project, instance=instance_ref.instance))

    backup_config = instance.settings.backupConfiguration[0].id
    request = sql_messages.SqlBackupRunsGetRequest(
        project=instance_ref.project,
        instance=instance_ref.instance,
        backupConfiguration=backup_config,
        dueTime=times.FormatDateTime(datetime, tzinfo=times.UTC))
    return sql_client.backupRuns.Get(request)

  def Run(self, args):
    """Retrieves information about a backup.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object that has the backup run resource if the command ran
      successfully.
    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing the
          command.
    """
    validate.ValidateInstanceName(args.instance)

    try:
      # Check if ID is an integer.
      # TODO(b/21877717): Remove this try clause after deprecation period when
      # re-adding validation above.
      id_integer = int(args.id)
    except ValueError:
      try:
        # If input is not an integer, check if it is a datetime.
        datetime = arg_parsers.Datetime.Parse(args.id)
      except arg_parsers.ArgumentTypeError:
        # If user input is not integer or datetime, throw error.
        raise arg_parsers.ArgumentTypeError('ID must be an integer.')
      return self._GetByDatetime(datetime, args)
    return self._GetById(id_integer, args)
