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
"""Creates a new Cloud SQL instance."""
import argparse

from apitools.base.py import exceptions as apitools_exceptions

from googlecloudsdk.api_lib.sql import api_util
from googlecloudsdk.api_lib.sql import instances
from googlecloudsdk.api_lib.sql import operations
from googlecloudsdk.api_lib.sql import validate
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.sql import flags
from googlecloudsdk.command_lib.sql import validate as command_validate
from googlecloudsdk.command_lib.util import labels_util
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.resource import resource_lex
from googlecloudsdk.core.resource import resource_property


def AddBaseArgs(parser):
  """Declare flag and positional arguments for this command parser."""
  # TODO(b/35705305): move common flags to command_lib.sql.flags
  base.ASYNC_FLAG.AddToParser(parser)
  parser.display_info.AddFormat(flags.INSTANCES_FORMAT_BETA)
  parser.add_argument(
      '--activation-policy',
      required=False,
      choices=['ALWAYS', 'NEVER', 'ON_DEMAND'],
      default=None,
      help=('The activation policy for this instance. This specifies when '
            'the instance should be activated and is applicable only when '
            'the instance state is RUNNABLE. More information on activation '
            'policies can be found here: '
            'https://cloud.google.com/sql/faq#activation_policy'))
  parser.add_argument(
      '--assign-ip',
      required=False,
      action='store_true',
      default=None,  # Tri-valued: None => don't change the setting.
      help='Specified if the instance must be assigned an IP address.')
  parser.add_argument(
      '--authorized-gae-apps',
      type=arg_parsers.ArgList(min_length=1),
      metavar='APP',
      required=False,
      default=[],
      help=('First Generation instances only. List of IDs for App Engine '
            'applications running in the Standard environment that can '
            'access this instance.'))
  parser.add_argument(
      '--authorized-networks',
      type=arg_parsers.ArgList(min_length=1),
      metavar='NETWORK',
      required=False,
      default=[],
      help=('The list of external networks that are allowed to connect to '
            'the instance. Specified in CIDR notation, also known as '
            '\'slash\' notation (e.g. 192.168.100.0/24).'))
  parser.add_argument(
      '--backup',
      required=False,
      action='store_true',
      default=True,
      help='Enables daily backup.')
  parser.add_argument(
      '--backup-start-time',
      required=False,
      help=('The start time of daily backups, specified in the 24 hour '
            'format - HH:MM, in the UTC timezone.'))
  parser.add_argument(
      '--cpu',
      type=int,
      required=False,
      help=('A whole number value indicating how many cores are desired in '
            'the machine. Both --cpu and --memory must be specified if a '
            'custom machine type is desired, and the --tier flag must be '
            'omitted.'))
  parser.add_argument(
      '--database-flags',
      type=arg_parsers.ArgDict(min_length=1),
      metavar='FLAG=VALUE',
      required=False,
      help=('A comma-separated list of database flags to set on the '
            'instance. Use an equals sign to separate flag name and value. '
            'Flags without values, like skip_grant_tables, can be written '
            'out without a value after, e.g., `skip_grant_tables=`. Use '
            'on/off for booleans. View the Instance Resource API for allowed '
            'flags. (e.g., `--database-flags max_allowed_packet=55555,'
            'skip_grant_tables=,log_output=1`)'))
  parser.add_argument(
      '--database-version',
      required=False,
      default='MYSQL_5_6',
      choices=['MYSQL_5_5', 'MYSQL_5_6', 'MYSQL_5_7', 'POSTGRES_9_6'],
      help='The database engine type and version.')
  parser.add_argument(
      '--enable-bin-log',
      required=False,
      action='store_true',
      default=None,  # Tri-valued: None => don't change the setting.
      help=(
          'Specified if binary log should be enabled. If backup '
          'configuration is disabled, binary log must be disabled as well.'))
  parser.add_argument(
      '--failover-replica-name',
      required=False,
      help='Also create a failover replica with the specified name.')
  parser.add_argument(
      '--follow-gae-app',
      required=False,
      help=('First Generation instances only. The App Engine app this '
            'instance should follow. It must be in the same region as '
            'the instance.'))
  parser.add_argument(
      '--gce-zone',
      required=False,
      help=('The preferred Compute Engine zone (e.g. us-central1-a, '
            'us-central1-b, etc.).'))
  parser.add_argument(
      'instance',
      type=command_validate.InstanceNameRegexpValidator(),
      help='Cloud SQL instance ID.')
  parser.add_argument(
      '--maintenance-release-channel',
      choices={
          'production': 'Production updates are stable and recommended '
                        'for applications in production.',
          'preview': 'Preview updates release prior to production '
                     'updates. You may wish to use the preview channel '
                     'for dev/test applications so that you can preview '
                     'their compatibility with your application prior '
                     'to the production release.'
      },
      type=str.lower,
      help="Which channel's updates to apply during the maintenance window.")
  parser.add_argument(
      '--maintenance-window-day',
      choices=arg_parsers.DayOfWeek.DAYS,
      type=arg_parsers.DayOfWeek.Parse,
      help='Day of week for maintenance window, in UTC time zone.')
  parser.add_argument(
      '--maintenance-window-hour',
      type=arg_parsers.BoundedInt(lower_bound=0, upper_bound=23),
      help='Hour of day for maintenance window, in UTC time zone.')
  parser.add_argument(
      '--master-instance-name',
      required=False,
      help=('Name of the instance which will act as master in the '
            'replication setup. The newly created instance will be a read '
            'replica of the specified master instance.'))
  parser.add_argument(
      '--memory',
      type=arg_parsers.BinarySize(),
      required=False,
      help=('A whole number value indicating how much memory is desired in '
            'the machine. A size unit should be provided (eg. 3072MiB or '
            '9GiB) - if no units are specified, GiB is assumed. Both --cpu '
            'and --memory must be specified if a custom machine type is '
            'desired, and the --tier flag must be omitted.'))
  parser.add_argument(
      '--on-premises-host-port', required=False, help=argparse.SUPPRESS)
  parser.add_argument(
      '--pricing-plan',
      '-p',
      required=False,
      choices=['PER_USE', 'PACKAGE'],
      default='PER_USE',
      help=('First Generation instances only. The pricing plan for this '
            'instance.'))
  # TODO(b/31989340): add remote completion
  parser.add_argument(
      '--region',
      required=False,
      default='us-central',
      help=('The regional location (e.g. asia-east1, us-east1). See the full '
            'list of regions at '
            'https://cloud.google.com/sql/docs/instance-locations.'))
  parser.add_argument(
      '--replica-type',
      choices=['READ', 'FAILOVER'],
      help='The type of replica to create.')
  parser.add_argument(
      '--replication',
      required=False,
      choices=['SYNCHRONOUS', 'ASYNCHRONOUS'],
      default=None,
      help='The type of replication this instance uses.')
  parser.add_argument(
      '--require-ssl',
      required=False,
      action='store_true',
      default=None,  # Tri-valued: None => don't change the setting.
      help='Specified if users connecting over IP must use SSL.')
  parser.add_argument(
      '--storage-auto-increase',
      action='store_true',
      default=None,
      help=('Storage size can be increased, but it cannot be decreased; '
            'storage increases are permanent for the life of the instance. '
            'With this setting enabled, a spike in storage requirements '
            'can result in permanently increased storage costs for your '
            'instance. However, if an instance runs out of available space, '
            'it can result in the instance going offline, dropping existing '
            'connections.'))
  parser.add_argument(
      '--storage-size',
      type=arg_parsers.BinarySize(
          lower_bound='10GB',
          upper_bound='10230GB',
          suggested_binary_size_scales=['GB']),
      help=('Amount of storage allocated to the instance. Must be an integer '
            'number of GB between 10GB and 10230GB inclusive.'))
  parser.add_argument(
      '--storage-type',
      required=False,
      choices=['SSD', 'HDD'],
      default=None,
      help='The storage type for the instance.')
  parser.add_argument(
      '--tier',
      '-t',
      required=False,
      help=('The tier for this instance. For Second Generation instances, '
            'TIER is the instance\'s machine type (e.g., db-n1-standard-1). '
            'For PostgreSQL instances, only shared-core machine types '
            '(e.g., db-f1-micro) apply. A complete list of tiers is '
            'available here: https://cloud.google.com/sql/pricing.'))


def RunBaseCreateCommand(args):
  """Creates a new Cloud SQL instance.

  Args:
    args: argparse.Namespace, The arguments that this command was invoked
        with.

  Returns:
    A dict object representing the operations resource describing the create
    operation if the create was successful.
  Raises:
    HttpException: A http error response was received while executing api
        request.
    ToolException: An error other than http error occured while executing the
        command.
  """
  client = api_util.SqlClient(api_util.API_VERSION_DEFAULT)
  sql_client = client.sql_client
  sql_messages = client.sql_messages

  validate.ValidateInstanceName(args.instance)
  instance_ref = client.resource_parser.Parse(
      args.instance,
      params={'project': properties.VALUES.core.project.GetOrFail},
      collection='sql.instances')
  instance_resource = instances.InstancesV1Beta4.ConstructInstanceFromArgs(
      sql_messages, args, instance_ref=instance_ref)

  if args.pricing_plan == 'PACKAGE':
    if not console_io.PromptContinue(
        'Charges will begin accruing immediately. Really create Cloud '
        'SQL instance?'):
      raise exceptions.ToolException('canceled by the user.')

  operation_ref = None
  try:
    result_operation = sql_client.instances.Insert(instance_resource)

    operation_ref = client.resource_parser.Create(
        'sql.operations',
        operation=result_operation.name,
        project=instance_ref.project)

    if args.async:
      if not args.IsSpecified('format'):
        args.format = 'default'
      return sql_client.operations.Get(
          sql_messages.SqlOperationsGetRequest(
              project=operation_ref.project,
              operation=operation_ref.operation))

    operations.OperationsV1Beta4.WaitForOperation(
        sql_client, operation_ref, 'Creating Cloud SQL instance')

    log.CreatedResource(instance_ref)

    new_resource = sql_client.instances.Get(
        sql_messages.SqlInstancesGetRequest(
            project=instance_ref.project, instance=instance_ref.instance))
    return new_resource
  except apitools_exceptions.HttpError as error:
    log.debug('operation : %s', str(operation_ref))
    exc = exceptions.HttpException(error)
    if resource_property.Get(exc.payload.content,
                             resource_lex.ParseKey('error.errors[0].reason'),
                             None) == 'errorMaxInstancePerLabel':
      msg = resource_property.Get(exc.payload.content,
                                  resource_lex.ParseKey('error.message'),
                                  None)
      raise exceptions.HttpException(msg)
    raise


@base.ReleaseTracks(base.ReleaseTrack.GA)
class Create(base.Command):
  """Creates a new Cloud SQL instance."""

  def Run(self, args):
    return RunBaseCreateCommand(args)

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command."""
    AddBaseArgs(parser)


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class CreateBeta(base.Command):
  """Creates a new Cloud SQL instance."""

  def Run(self, args):
    return RunBaseCreateCommand(args)

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command."""
    AddBaseArgs(parser)
    flags.INSTANCE_RESIZE_LIMIT_FLAG.AddToParser(parser)
    labels_util.AddCreateLabelsFlags(parser)
