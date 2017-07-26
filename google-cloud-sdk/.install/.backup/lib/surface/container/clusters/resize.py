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
"""Resize cluster command."""
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.container import flags
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io


class Resize(base.Command):
  """Resizes an existing cluster for running containers."""

  @staticmethod
  def Args(parser):
    """Register flags for this command.

    Args:
      parser: An argparse.ArgumentParser-like object. It is mocked out in order
          to capture some information, but behaves like an ArgumentParser.
    """
    parser.add_argument('name', help='The name of this cluster.')
    parser.add_argument(
        '--size',
        required=True,
        type=int,
        help=('Target number of nodes in the cluster.'))
    parser.add_argument('--node-pool', help='The node pool to resize.')
    flags.AddAsyncFlag(parser)

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    """
    adapter = self.context['api_adapter']
    cluster_ref = adapter.ParseCluster(args.name,
                                       getattr(args, 'region', None))
    cluster = adapter.GetCluster(cluster_ref)
    pool = adapter.FindNodePool(cluster, args.node_pool)
    console_io.PromptContinue(
        message=('Pool [{pool}] for [{cluster_name}] will be resized to '
                 '{new_size}.').format(pool=pool.name,
                                       cluster_name=cluster.name,
                                       new_size=args.size),
        throw_if_unattended=True,
        cancel_on_no=True)
    ops = []
    for ig in pool.instanceGroupUrls:
      igm = adapter.ParseIGM(ig)
      op_ref = adapter.ResizeCluster(igm.project, igm.zone,
                                     igm.instanceGroupManager, args.size)
      ops.append(op_ref)

    if not args.async:
      adapter.WaitForComputeOperations(
          cluster_ref.projectId, cluster.zone, [op.name for op in ops],
          'Resizing {0}'.format(cluster_ref.clusterId))
    log.UpdatedResource(cluster_ref)


Resize.detailed_help = {
    'brief': 'Resizes an existing cluster for running containers.',
    'DESCRIPTION': """
        Resize an existing cluster to a provided size.

If you have multiple node pools, you must specify which node pool to resize by
using the --node-pool flag. You are not required to use the flag if you have
a single node pool.

When increasing the size of a container cluster, the new instances are created
with the same configuration as the existing instances.
Existing pods are not moved onto the new instances,
but new pods (such as those created by resizing a replication controller)
will be scheduled onto the new instances.

When decreasing a cluster, the pods that are scheduled on the instances being
removed will be killed. If your pods are being managed by a replication
controller, the controller will attempt to reschedule them onto the remaining
instances. If your pods are not managed by a replication controller,
they will not be restarted.
Note that when resizing down, instances running pods and instances without pods
are not differentiated. Resize will pick instances to remove at random.
""",
}
