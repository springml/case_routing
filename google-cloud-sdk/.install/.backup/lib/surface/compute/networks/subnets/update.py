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

"""Command for modifying the properties of a subnetwork."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute.networks.subnets import flags


class Update(base.UpdateCommand):
  """Updates properties of an existing Google Compute Engine subnetwork."""

  SUBNETWORK_ARG = None

  @classmethod
  def Args(cls, parser):
    """The command arguments handler.

    Args:
      parser: An argparse.ArgumentParser instance.
    """
    cls.SUBNETWORK_ARG = flags.SubnetworkArgument()
    cls.SUBNETWORK_ARG.AddArgument(parser, operation_type='update')

    parser.add_argument(
        '--enable-private-ip-google-access',
        action='store_true',
        default=None,  # Tri-valued, None => do not change.
        help=('Enable/disable access to Google Cloud APIs from this subnet for '
              'instances without a public ip address.'))

  def Run(self, args):
    """Issues requests necessary to update Subnetworks."""
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    client = holder.client

    request_list = []
    subnet_ref = self.SUBNETWORK_ARG.ResolveAsResource(args, holder.resources)

    if args.enable_private_ip_google_access is not None:
      google_access = (
          client.messages.SubnetworksSetPrivateIpGoogleAccessRequest())
      google_access.privateIpGoogleAccess = args.enable_private_ip_google_access

      google_access_request = (
          client.messages.ComputeSubnetworksSetPrivateIpGoogleAccessRequest(
              project=subnet_ref.project,
              region=subnet_ref.region,
              subnetwork=subnet_ref.Name(),
              subnetworksSetPrivateIpGoogleAccessRequest=google_access))
      request_list.append((client.apitools_client.subnetworks,
                           'SetPrivateIpGoogleAccess', google_access_request))

    return client.MakeRequests(request_list)
