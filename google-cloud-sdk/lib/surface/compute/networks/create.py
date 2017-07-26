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
"""Command for creating networks."""

import textwrap

from apitools.base.py import encoding

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import networks_utils
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute.networks import flags
from googlecloudsdk.command_lib.compute.networks import network_utils
from googlecloudsdk.core import log
from googlecloudsdk.core.resource import resource_projector


@base.ReleaseTracks(base.ReleaseTrack.BETA, base.ReleaseTrack.GA)
class Create(base.CreateCommand):
  """Create a Google Compute Engine network.

  *{command}* is used to create virtual networks. A network
  performs the same function that a router does in a home
  network: it describes the network range and gateway IP
  address, handles communication between instances, and serves
  as a gateway between instances and callers outside the
  network.
  """

  NETWORK_ARG = None

  @classmethod
  def Args(cls, parser):
    parser.display_info.AddFormat(flags.DEFAULT_LIST_FORMAT)
    cls.NETWORK_ARG = flags.NetworkArgument()
    cls.NETWORK_ARG.AddArgument(parser, operation_type='create')

    network_utils.AddCreateArgs(parser)

  def Run(self, args):
    """Issues the request necessary for adding the network."""
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    client = holder.client

    self._network_name = args.name

    # TODO(b/31649473): after one month, make default auto.
    if args.mode is None:
      if args.range is not None:
        log.warn('You are creating a legacy network. Using --mode=legacy will '
                 'be required in future releases.')
        args.mode = 'legacy'
      else:
        args.mode = 'auto'

    if args.mode != 'legacy' and args.range is not None:
      raise exceptions.InvalidArgumentException(
          '--range', '--range can only be used if --mode=legacy')

    network_ref = self.NETWORK_ARG.ResolveAsResource(args, holder.resources)

    if args.mode == 'legacy':
      request = client.messages.ComputeNetworksInsertRequest(
          network=client.messages.Network(
              name=network_ref.Name(),
              IPv4Range=args.range,
              description=args.description),
          project=network_ref.project)
    else:
      request = client.messages.ComputeNetworksInsertRequest(
          network=client.messages.Network(
              name=network_ref.Name(),
              autoCreateSubnetworks=args.mode == 'auto',
              description=args.description),
          project=network_ref.project)

    responses = client.MakeRequests([(client.apitools_client.networks, 'Insert',
                                      request)])

    responses = [encoding.MessageToDict(m) for m in responses]
    return networks_utils.AddMode(responses)

  def Epilog(self, resources_were_displayed=True):
    message = """\

        Instances on this network will not be reachable until firewall rules
        are created. As an example, you can allow all internal traffic between
        instances as well as SSH, RDP, and ICMP by running:

        $ gcloud compute firewall-rules create <FIREWALL_NAME> --network {0} --allow tcp,udp,icmp --source-ranges <IP_RANGE>
        $ gcloud compute firewall-rules create <FIREWALL_NAME> --network {0} --allow tcp:22,tcp:3389,icmp
        """.format(self._network_name)
    log.status.Print(textwrap.dedent(message))


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class CreateAlpha(base.CreateCommand):
  """Create a Google Compute Engine network.

  *{command}* is used to create virtual networks. A network
  performs the same function that a router does in a home
  network: it describes the network range and gateway IP
  address, handles communication between instances, and serves
  as a gateway between instances and callers outside the
  network.
  """

  NETWORK_ARG = None

  @classmethod
  def Args(cls, parser):
    parser.display_info.AddFormat(flags.ALPHA_LIST_FORMAT)
    cls.NETWORK_ARG = flags.NetworkArgument()
    cls.NETWORK_ARG.AddArgument(parser)
    network_utils.AddCreateAlphaArgs(parser)

  def Run(self, args):
    """Issues the request necessary for adding the network."""
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    client = holder.client
    messages = client.messages

    network_utils.CheckRangeLegacyModeOrRaise(args)

    network_ref = self.NETWORK_ARG.ResolveAsResource(args, holder.resources)
    self._network_name = network_ref.Name()
    network_resource = networks_utils.CreateNetworkResourceFromArgs(
        messages=messages,
        network_ref=network_ref,
        network_args=args)

    request = (
        client.apitools_client.networks,
        'Insert',
        client.messages.ComputeNetworksInsertRequest(
            network=network_resource, project=network_ref.project)
    )
    response = client.MakeRequests([request])[0]

    resource = resource_projector.MakeSerializable(response)
    resource['x_gcloud_subnet_mode'] = networks_utils.GetSubnetMode(response)
    resource['x_gcloud_bgp_routing_mode'] = networks_utils.GetBgpRoutingMode(
        response)
    return resource

  def Epilog(self, resources_were_displayed=True):
    message = """\

Instances on this network will not be reachable until firewall rules are
created. As an example, you can allow all internal traffic between instances as
well as SSH, RDP, and ICMP by running:

$ gcloud compute firewall-rules create <FIREWALL_NAME> --network {0} --allow \
tcp,udp,icmp --source-ranges <IP_RANGE>
$ gcloud compute firewall-rules create <FIREWALL_NAME> --network {0} --allow \
tcp:22,tcp:3389,icmp
        """.format(self._network_name)
    log.status.Print(textwrap.dedent(message))
