# Copyright 2014 Google Inc. All Rights Reserved.
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
"""Create node pool command."""

import argparse

from apitools.base.py import exceptions as apitools_exceptions

from googlecloudsdk.api_lib.compute import constants as compute_constants
from googlecloudsdk.api_lib.container import api_adapter
from googlecloudsdk.api_lib.container import util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.container import flags
from googlecloudsdk.command_lib.container import messages
from googlecloudsdk.core import log

DETAILED_HELP = {
    'DESCRIPTION':
        """\
        *{command}* facilitates the creation of a node pool in a Google
        Container Engine cluster. A variety of options exists to customize the
        node configuration and the number of nodes created.
        """,
    'EXAMPLES':
        """\
        To create a new node pool "node-pool-1" with the default options in the
        cluster "sample-cluster", run:

          $ {command} node-pool-1 --cluster=example-cluster

        The new node pool will show up in the cluster after all the nodes have
        been provisioned.

        To create a node pool with 5 nodes, run:

          $ {command} node-pool-1 --cluster=example-cluster --num-nodes=5
        """,
}


def _Args(parser):
  """Register flags for this command.

  Args:
    parser: An argparse.ArgumentParser-like object. It is mocked out in order
        to capture some information, but behaves like an ArgumentParser.
  """
  flags.AddNodePoolNameArg(parser, 'The name of the node pool to create.')
  flags.AddNodePoolClusterFlag(parser, 'The cluster to add the node pool to.')
  parser.add_argument(
      '--enable-cloud-endpoints',
      action='store_true',
      default=True,
      help='Automatically enable Google Cloud Endpoints to take advantage of '
      'API management features.')
  # Timeout in seconds for operation
  parser.add_argument(
      '--timeout', type=int, default=1800, help=argparse.SUPPRESS)
  parser.add_argument(
      '--num-nodes',
      type=int,
      help='The number of nodes in the node pool in each of the '
      'cluster\'s zones.',
      default=3)
  parser.add_argument(
      '--machine-type',
      '-m',
      help='The type of machine to use for nodes. Defaults to n1-standard-1')
  parser.add_argument(
      '--disk-size',
      type=int,
      help='Size in GB for node VM boot disks. Defaults to 100GB.')
  parser.add_argument(
      '--scopes',
      type=arg_parsers.ArgList(min_length=1),
      metavar='SCOPE',
      help="""\
Specifies scopes for the node instances. The project's default
service account is used. Examples:

  $ {{command}} node-pool-1 --cluster=example-cluster --scopes https://www.googleapis.com/auth/devstorage.read_only

  $ {{command}} node-pool-1 --cluster=example-cluster --scopes bigquery,storage-rw,compute-ro

Multiple SCOPEs can specified, separated by commas. The scopes
necessary for the cluster to function properly (compute-rw, storage-ro),
are always added, even if not explicitly specified.

SCOPE can be either the full URI of the scope or an alias.
Available aliases are:

[options="header",format="csv",grid="none",frame="none"]
|========
Alias,URI
{aliases}
|========

{scope_deprecation_msg}
""".format(
    aliases=compute_constants.ScopesForHelp(),
    scope_deprecation_msg=compute_constants.DEPRECATED_SCOPES_MESSAGES))
  flags.AddImageTypeFlag(parser, 'node pool')
  flags.AddNodeLabelsFlag(parser, for_node_pool=True)
  flags.AddTagsFlag(parser, """\
Applies the given Compute Engine tags (comma separated) on all nodes in the new
node-pool. Example:

  $ {command} node-pool-1 --cluster=example-cluster --tags=tag1,tag2

New nodes, including ones created by resize or recreate, will have these tags
on the Compute Engine API instance object and can be used in firewall rules.
See https://cloud.google.com/sdk/gcloud/reference/compute/firewall-rules/create
for examples.
""")
  flags.AddDiskTypeFlag(parser, suppressed=True)
  parser.display_info.AddFormat(util.NODEPOOLS_FORMAT)


def ParseCreateNodePoolOptionsBase(args):
  return api_adapter.CreateNodePoolOptions(
      machine_type=args.machine_type,
      disk_size_gb=args.disk_size,
      scopes=args.scopes,
      enable_cloud_endpoints=args.enable_cloud_endpoints,
      num_nodes=args.num_nodes,
      local_ssd_count=args.local_ssd_count,
      tags=args.tags,
      node_labels=args.node_labels,
      enable_autoscaling=args.enable_autoscaling,
      max_nodes=args.max_nodes,
      min_nodes=args.min_nodes,
      image_type=args.image_type,
      preemptible=args.preemptible,
      enable_autorepair=args.enable_autorepair,
      enable_autoupgrade=args.enable_autoupgrade,
      service_account=args.service_account,
      disk_type=args.disk_type)


@base.ReleaseTracks(base.ReleaseTrack.GA)
class Create(base.CreateCommand):
  """Create a node pool in a running cluster."""

  @staticmethod
  def Args(parser):
    _Args(parser)
    flags.AddClusterAutoscalingFlags(parser, hidden=True)
    flags.AddLocalSSDFlag(parser, suppressed=True)
    flags.AddPreemptibleFlag(parser, for_node_pool=True, suppressed=True)
    flags.AddEnableAutoRepairFlag(parser, for_node_pool=True, suppressed=True)
    flags.AddEnableAutoUpgradeFlag(parser, for_node_pool=True, suppressed=True)
    flags.AddServiceAccountFlag(parser, suppressed=True)

  def ParseCreateNodePoolOptions(self, args):
    return ParseCreateNodePoolOptionsBase(args)

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      Cluster message for the successfully created node pool.

    Raises:
      util.Error, if creation failed.
    """
    adapter = self.context['api_adapter']
    if not args.scopes:
      args.scopes = []

    try:
      if not args.scopes:
        args.scopes = []
      pool_ref = adapter.ParseNodePool(args.name, getattr(args, 'region', None))
      options = self.ParseCreateNodePoolOptions(args)

      if options.enable_autorepair is not None:
        log.status.Print(
            messages.AutoUpdateUpgradeRepairMessage(options.enable_autorepair,
                                                    'autorepair'))

      if options.enable_autoupgrade is not None:
        log.status.Print(
            messages.AutoUpdateUpgradeRepairMessage(options.enable_autoupgrade,
                                                    'autoupgrade'))

      operation_ref = adapter.CreateNodePool(pool_ref, options)

      adapter.WaitForOperation(
          operation_ref,
          'Creating node pool {0}'.format(pool_ref.nodePoolId),
          timeout_s=args.timeout)
      pool = adapter.GetNodePool(pool_ref)
    except apitools_exceptions.HttpError as error:
      raise exceptions.HttpException(error, util.HTTP_ERROR_FORMAT)

    log.CreatedResource(pool_ref)
    return [pool]


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class CreateBeta(Create):
  """Create a node pool in a running cluster."""

  @staticmethod
  def Args(parser):
    _Args(parser)
    flags.AddClusterAutoscalingFlags(parser, hidden=True)
    flags.AddLocalSSDFlag(parser)
    flags.AddPreemptibleFlag(parser, for_node_pool=True)
    flags.AddEnableAutoRepairFlag(parser, for_node_pool=True)
    flags.AddEnableAutoUpgradeFlag(parser, for_node_pool=True)
    flags.AddServiceAccountFlag(parser)


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class CreateAlpha(Create):
  """Create a node pool in a running cluster."""

  def ParseCreateNodePoolOptions(self, args):
    ops = ParseCreateNodePoolOptionsBase(args)
    ops.accelerators = args.accelerator
    return ops

  @staticmethod
  def Args(parser):
    _Args(parser)
    flags.AddClusterAutoscalingFlags(parser)
    flags.AddLocalSSDFlag(parser)
    flags.AddPreemptibleFlag(parser, for_node_pool=True)
    flags.AddEnableAutoRepairFlag(parser, for_node_pool=True)
    flags.AddEnableAutoUpgradeFlag(parser, for_node_pool=True)
    flags.AddServiceAccountFlag(parser)
    flags.AddAcceleratorArgs(parser)


Create.detailed_help = DETAILED_HELP
