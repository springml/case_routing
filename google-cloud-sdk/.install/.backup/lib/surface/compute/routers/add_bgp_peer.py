# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Command for adding a BGP peer to a Google Compute Engine router."""

from apitools.base.py import encoding

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute.routers import flags


class AddBgpPeer(base.UpdateCommand):
  """Add a BGP peer to a Google Compute Engine router.

  *{command}* is used to add a BGP peer to a Google Compute Engine router.
  """

  ROUTER_ARG = None

  @classmethod
  def Args(cls, parser):
    cls.ROUTER_ARG = flags.RouterArgument()
    cls.ROUTER_ARG.AddArgument(parser, operation_type='update')

    parser.add_argument(
        '--peer-name',
        required=True,
        help='The name of the peer being added.')

    parser.add_argument(
        '--interface',
        required=True,
        help='The name of the interface of the peer being added.')

    parser.add_argument(
        '--peer-asn',
        required=True,
        type=int,
        help='The asn of the peer being added.')

    parser.add_argument(
        '--peer-ip-address',
        help='The link local address of the peer.')

    parser.add_argument(
        # TODO(b/36057451): document the default priority if any
        '--advertised-route-priority',
        type=int,
        help='The priority of routes advertised to this BGP peer. In the case '
             'where there is more than one matching route of maximum length, '
             'the routes with lowest priority value win. 0 <= priority <= '
             '65535.')

  def GetGetRequest(self, client, router_ref):
    return (client.apitools_client.routers,
            'Get',
            client.messages.ComputeRoutersGetRequest(
                router=router_ref.Name(),
                region=router_ref.region,
                project=router_ref.project))

  def GetSetRequest(self, client, router_ref, replacement):
    return (client.apitools_client.routers,
            'Update',
            client.messages.ComputeRoutersUpdateRequest(
                router=router_ref.Name(),
                routerResource=replacement,
                region=router_ref.region,
                project=router_ref.project))

  def Modify(self, client, args, existing):
    replacement = encoding.CopyProtoMessage(existing)

    peer = client.messages.RouterBgpPeer(
        name=args.peer_name,
        interfaceName=args.interface,
        peerIpAddress=args.peer_ip_address,
        peerAsn=args.peer_asn,
        advertisedRoutePriority=args.advertised_route_priority)

    replacement.bgpPeers.append(peer)

    return replacement

  def Run(self, args):
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    client = holder.client

    router_ref = self.ROUTER_ARG.ResolveAsResource(args, holder.resources)
    get_request = self.GetGetRequest(client, router_ref)

    # There is only one response because one request is made
    router = client.MakeRequests([get_request])[0]

    modified_router = self.Modify(client, args, router)

    return client.MakeRequests(
        [self.GetSetRequest(client, router_ref, modified_router)])
