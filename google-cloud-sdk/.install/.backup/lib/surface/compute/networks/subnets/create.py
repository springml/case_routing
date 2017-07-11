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

"""Command for creating subnetworks."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute import flags as compute_flags
from googlecloudsdk.command_lib.compute.networks import flags as network_flags
from googlecloudsdk.command_lib.compute.networks.subnets import flags


def _AddArgs(cls, parser):
  """Add subnetwork create arguments to parser."""
  cls.SUBNETWORK_ARG = flags.SubnetworkArgument()
  cls.NETWORK_ARG = network_flags.NetworkArgumentForOtherResource(
      'The network to which the subnetwork belongs.')
  cls.SUBNETWORK_ARG.AddArgument(parser, operation_type='create')
  cls.NETWORK_ARG.AddArgument(parser)

  parser.add_argument(
      '--description',
      help='An optional description of this subnetwork.')

  parser.add_argument(
      '--range',
      required=True,
      help='The IP space allocated to this subnetwork in CIDR format.')

  parser.add_argument(
      '--enable-private-ip-google-access',
      action='store_true',
      default=False,
      help=('Enable/disable access to Google Cloud APIs from this subnet for '
            'instances without a public ip address.'))


@base.ReleaseTracks(base.ReleaseTrack.GA)
class Create(base.CreateCommand):
  """Define a subnet for a network in custom subnet mode."""

  NETWORK_ARG = None
  SUBNETWORK_ARG = None

  @classmethod
  def Args(cls, parser):
    parser.display_info.AddFormat(flags.DEFAULT_LIST_FORMAT)
    _AddArgs(cls, parser)

  def Run(self, args):
    """Issues a list of requests necessary for adding a subnetwork."""
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    client = holder.client

    network_ref = self.NETWORK_ARG.ResolveAsResource(args, holder.resources)
    subnet_ref = self.SUBNETWORK_ARG.ResolveAsResource(
        args,
        holder.resources,
        scope_lister=compute_flags.GetDefaultScopeLister(client))

    request = client.messages.ComputeSubnetworksInsertRequest(
        subnetwork=client.messages.Subnetwork(
            name=subnet_ref.Name(),
            description=args.description,
            network=network_ref.SelfLink(),
            ipCidrRange=args.range,
            privateIpGoogleAccess=args.enable_private_ip_google_access,
        ),
        region=subnet_ref.region,
        project=subnet_ref.project)

    return client.MakeRequests([(client.apitools_client.subnetworks,
                                 'Insert', request)])


@base.ReleaseTracks(base.ReleaseTrack.BETA, base.ReleaseTrack.ALPHA)
class CreateBeta(Create):
  """Define a subnet for a network in custom subnet mode."""

  @classmethod
  def Args(cls, parser):
    parser.display_info.AddFormat(flags.DEFAULT_LIST_FORMAT)
    _AddArgs(cls, parser)
    parser.add_argument(
        '--secondary-range',
        type=arg_parsers.ArgDict(min_length=1),
        action='append',
        metavar='PROPERTY=VALUE',
        help="""\
        Adds a secondary IP range to the subnetwork for use in IP aliasing.

        For example, `--secondary-range range1=192.168.64.0/24` adds
        a secondary range 192.168.64.0/24 with name range1.

        * `RANGE_NAME` - Name of the secondary range.
        * `RANGE` - `IP range in CIDR format.`
        """)

  def Run(self, args):
    """Issues a list of requests for adding a subnetwork. Overrides."""
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    client = holder.client

    network_ref = self.NETWORK_ARG.ResolveAsResource(args, holder.resources)
    subnet_ref = self.SUBNETWORK_ARG.ResolveAsResource(
        args,
        holder.resources,
        scope_lister=compute_flags.GetDefaultScopeLister(client))

    request = client.messages.ComputeSubnetworksInsertRequest(
        subnetwork=client.messages.Subnetwork(
            name=subnet_ref.Name(),
            description=args.description,
            network=network_ref.SelfLink(),
            ipCidrRange=args.range,
            privateIpGoogleAccess=args.enable_private_ip_google_access,
        ),
        region=subnet_ref.region,
        project=subnet_ref.project)

    secondary_ranges = []
    if args.secondary_range:
      for secondary_range in args.secondary_range:
        for range_name, ip_cidr_range in sorted(secondary_range.iteritems()):
          secondary_ranges.append(
              client.messages.SubnetworkSecondaryRange(
                  rangeName=range_name,
                  ipCidrRange=ip_cidr_range))

    request.subnetwork.secondaryIpRanges = secondary_ranges
    return client.MakeRequests([(client.apitools_client.subnetworks,
                                 'Insert', request)])
