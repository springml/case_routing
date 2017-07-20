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
"""Command for suspending an instance."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute.instances import flags


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class Suspend(base.SilentCommand):
  """Suspend a virtual machine instance.

  *{command}* is used to suspend a Google Compute Engine virtual machine.
  Suspending a VM is the equivalent of sleep or standby mode:
  the guest receives an ACPI S3 suspend signal, after which all VM state
  is saved to temporary storage.  An instance can only be suspended while
  it is in the RUNNING state.  A suspended instance will be put in
  SUSPENDED state.

  Note: A suspended instance can be resumed by running the
  `gcloud alpha compute instances start` command.

  Alpha restrictions: Suspending a Preemptible VM is not supported and
  will result in an API error. Suspending a VM that is using CSEK or GPUs
  is not supported and will result in an API error.
  """

  @staticmethod
  def Args(parser):
    flags.INSTANCES_ARG.AddArgument(parser)
    parser.add_argument(
        '--discard-local-ssd',
        action='store_true',
        help=('If provided, local SSD data is discarded.'))
    # TODO(b/36057354): consider adding detailed help.

  def _CreateSuspendRequest(self, client, instance_ref, discard_local_ssd):
    return client.messages.ComputeInstancesSuspendRequest(
        discardLocalSsd=discard_local_ssd,
        instance=instance_ref.Name(),
        project=instance_ref.project,
        zone=instance_ref.zone)

  def Run(self, args):
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    client = holder.client

    instance_refs = flags.INSTANCES_ARG.ResolveAsResource(
        args,
        holder.resources,
        scope_lister=flags.GetInstanceZoneScopeLister(client))

    requests = []
    for instance_ref in instance_refs:
      requests.append((client.apitools_client.instances,
                       'Suspend', self._CreateSuspendRequest(
                           client, instance_ref, args.discard_local_ssd)))
    return client.MakeRequests(requests)

