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
"""bigtable clusters update command."""

from googlecloudsdk.api_lib.bigtable import util
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.bigtable import arguments
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class UpdateCluster(base.UpdateCommand):
  """Update a Bigtable cluster's friendly name and serving nodes."""

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    (arguments.ArgAdder(parser).AddCluster().AddInstance(positional=False)
     .AddClusterNodes().AddAsync())

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      Some value that we want to have printed later.
    """
    cli = util.GetAdminClient()
    msgs = util.GetAdminMessages()
    ref = resources.REGISTRY.Parse(
        args.cluster,
        params={
            'projectsId': properties.VALUES.core.project.GetOrFail,
            'instancesId': args.instance
        },
        collection='bigtableadmin.projects.instances.clusters')
    msg = msgs.Cluster(name=ref.RelativeName(), serveNodes=args.num_nodes)
    result = cli.projects_instances_clusters.Update(msg)
    if not args.async:
      # TODO(b/36051980): enable this line when b/29563942 is fixed in apitools
      pass
      # util.WaitForOpV2(result, 'Updating cluster')
    log.UpdatedResource(args.cluster, kind='cluster', async=args.async)
    return result
