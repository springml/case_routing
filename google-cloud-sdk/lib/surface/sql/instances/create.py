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
  flags.AddActivationPolicy(parser)
  flags.AddAssignIp(parser)
  flags.AddAuthorizedGAEApps(parser)
  flags.AddAuthorizedNetworks(parser)
  parser.add_argument(
      '--backup',
      required=False,
      action='store_true',
      default=True,
      help='Enables daily backup.')
  flags.AddBackupStartTime(parser)
  flags.AddCPU(parser)
  flags.AddDatabaseFlags(parser)
  parser.add_argument(
      '--database-version',
      required=False,
      default='MYSQL_5_6',
      choices=['MYSQL_5_5', 'MYSQL_5_6', 'MYSQL_5_7', 'POSTGRES_9_6'],
      help='The database engine type and version.')
  flags.AddEnableBinLog(parser)
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
  flags.AddMaintenanceReleaseChannel(parser)
  flags.AddMaintenanceWindowDay(parser)
  flags.AddMaintenanceWindowHour(parser)
  parser.add_argument(
      '--master-instance-name',
      required=False,
      help=('Name of the instance which will act as master in the '
            'replication setup. The newly created instance will be a read '
            'replica of the specified master instance.'))
  flags.AddMemory(parser)
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
  flags.AddReplication(parser)
  parser.add_argument(
      '--require-ssl',
      required=False,
      action='store_true',
      default=None,  # Tri-valued: None => don't change the setting.
      help='Specified if users connecting over IP must use SSL.')
  flags.AddStorageAutoIncrease(parser)
  flags.AddStorageSize(parser)
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
