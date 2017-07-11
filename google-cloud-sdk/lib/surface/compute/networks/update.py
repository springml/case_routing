# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Command for updating networks."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute.networks import flags
from googlecloudsdk.command_lib.compute.networks import network_utils
from googlecloudsdk.core.console import console_io


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class UpdateAlpha(base.UpdateCommand):
  """Update a Google Compute Engine Network."""

  NETWORK_ARG = None

  @classmethod
  def Args(cls, parser):
    cls.NETWORK_ARG = flags.NetworkArgument()
    cls.NETWORK_ARG.AddArgument(parser)
    network_utils.AddUpdateAlphaArgs(parser)

  def Run(self, args):
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    messages = holder.client.messages
    service = holder.client.apitools_client.networks

    network_ref = self.NETWORK_ARG.ResolveAsResource(args, holder.resources)

    if args.switch_to_custom_subnet_mode:
      prompt_msg = 'Network [{0}] will be switched to custom mode. '.format(
          network_ref.Name()) + 'This operation cannot be undone.'
      if not console_io.PromptContinue(message=prompt_msg, default=True):
        raise network_utils.CancelledException('Operation aborted by user.')

      resource = service.SwitchToCustomMode(
          messages.ComputeNetworksSwitchToCustomModeRequest(
              project=network_ref.project,
              network=network_ref.Name()))

    if args.bgp_routing_mode:
      network_resource = messages.Network()
      network_resource.routingConfig = messages.NetworkRoutingConfig()
      network_resource.routingConfig.routingMode = (
          messages.NetworkRoutingConfig.RoutingModeValueValuesEnum(
              args.bgp_routing_mode))

      resource = service.Patch(
          messages.ComputeNetworksPatchRequest(
              project=network_ref.project,
              network=network_ref.Name(),
              networkResource=network_resource))

    return resource


UpdateAlpha.detailed_help = {
    'brief':
        'Update a network',
    'DESCRIPTION':
        """\

        *{command}* is used to update virtual networks. TODO: list which fields
        are allowed to be updated."""
}
