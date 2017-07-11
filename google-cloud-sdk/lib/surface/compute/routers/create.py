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

"""Command for creating Google Compute Engine routers."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute.networks import flags as network_flags
from googlecloudsdk.command_lib.compute.routers import flags


class Create(base.CreateCommand):
  """Create a Google Compute Engine router.

    *{command}* is used to create a router for use in dynamic
  routing with vpn tunnels.
  """

  NETWORK_ARG = None
  ROUTER_ARG = None

  @classmethod
  def Args(cls, parser):
    parser.display_info.AddFormat(flags.DEFAULT_LIST_FORMAT)
    cls.NETWORK_ARG = network_flags.NetworkArgumentForOtherResource(
        'The network for this router')
    cls.NETWORK_ARG.AddArgument(parser)
    cls.ROUTER_ARG = flags.RouterArgument()
    cls.ROUTER_ARG.AddArgument(parser, operation_type='create')

    parser.add_argument(
        '--description',
        help='An optional description of this router.')

    parser.add_argument(
        '--asn',
        required=True,
        type=int,
        # TODO(b/36051028): improve this help
        help='The BGP asn for this router')

  def Run(self, args):
    """Issues requests necessary for adding a router."""
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    client = holder.client

    router_ref = self.ROUTER_ARG.ResolveAsResource(args, holder.resources)
    network_ref = self.NETWORK_ARG.ResolveAsResource(args, holder.resources)

    request = client.messages.ComputeRoutersInsertRequest(
        router=client.messages.Router(
            description=args.description,
            network=network_ref.SelfLink(),
            bgp=client.messages.RouterBgp(
                asn=args.asn),
            name=router_ref.Name()),
        region=router_ref.region,
        project=router_ref.project)

    return client.MakeRequests([(client.apitools_client.routers, 'Insert',
                                 request)])
