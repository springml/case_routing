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

"""Command for stopping an instance."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute.instances import flags


@base.ReleaseTracks(base.ReleaseTrack.GA, base.ReleaseTrack.BETA)
class Stop(base.SilentCommand):
  """Stop a virtual machine instance.

  *{command}* is used stop a Google Compute Engine virtual machine.
  Stopping a VM performs a clean shutdown, much like invoking the shutdown
  functionality of a workstation or laptop. Stopping a VM with a local SSD
  is not supported and will result in an API error.
  """

  @staticmethod
  def Args(parser):
    flags.INSTANCES_ARG.AddArgument(parser)
    parser.add_argument(
        '--discard-local-ssd',
        action='store_true',
        help=('If provided, local SSD data is discarded.'))

  def _CreateStopRequest(self, client, instance_ref, unused_discard_local_ssd):
    return client.messages.ComputeInstancesStopRequest(
        instance=instance_ref.Name(),
        project=instance_ref.project,
        zone=instance_ref.zone)

  def Run(self, args):
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    client = holder.client

    instance_refs = flags.INSTANCES_ARG.ResolveAsResource(
        args, holder.resources,
        scope_lister=flags.GetInstanceZoneScopeLister(client))
    return client.MakeRequests(
        [(client.apitools_client.instances, 'Stop', self._CreateStopRequest(
            client, instance_ref, args.discard_local_ssd))
         for instance_ref in instance_refs])


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class StopAlpha(Stop):
  """Stop a virtual machine instance.

  *{command}* is used stop a Google Compute Engine virtual machine.
  Stopping a VM performs a clean shutdown, much like invoking the shutdown
  functionality of a workstation or laptop. Stopping a VM with a local SSD
  is not supported and will result in an API error.
  """

  def _CreateStopRequest(self, client, instance_ref, discard_local_ssd):
    """Adds the discardLocalSsd var into the message."""
    return client.messages.ComputeInstancesStopRequest(
        discardLocalSsd=discard_local_ssd,
        instance=instance_ref.Name(),
        project=instance_ref.project,
        zone=instance_ref.zone)
