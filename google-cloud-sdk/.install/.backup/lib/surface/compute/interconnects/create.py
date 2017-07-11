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

"""Command for creating interconnects."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute.interconnects import client
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute.interconnects import flags
from googlecloudsdk.command_lib.compute.interconnects.locations import flags as location_flags


class Create(base.CreateCommand):
  """Create a Google Compute Engine interconnect.

  *{command}* is used to create interconnect. A interconnect represents a
  single specific connection between Google and the customer.
  """

  INTERCONNECT_ARG = None
  LOCATION_ARG = None

  @classmethod
  def Args(cls, parser):
    cls.LOCATION_ARG = (
        location_flags.InterconnectLocationArgumentForOtherResource(
            'The location for the interconnect, user can first list the '
            'locations by using '
            '{ gcloud alpha compute interconnects locations list }, then find'
            'the appropriate location to use when create interconnect here.'))
    cls.LOCATION_ARG.AddArgument(parser)
    cls.INTERCONNECT_ARG = flags.InterconnectArgument()
    cls.INTERCONNECT_ARG.AddArgument(parser, operation_type='create')

    parser.add_argument(
        '--description',
        help='An optional, textual description for the interconnect.')
    flags.AddAdminEnabled(parser)
    flags.AddInterconnectType(parser)
    flags.AddLinkType(parser)
    flags.AddNocContactEmail(parser)
    flags.AddRequestedLinkCount(parser)

  def Collection(self):
    return 'compute.interconnects'

  def Run(self, args):
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    ref = self.INTERCONNECT_ARG.ResolveAsResource(args, holder.resources)
    interconnect = client.Interconnect(ref, compute_client=holder.client)

    enum_values = flags.ResolveInterconnectEnumValues(args, holder)
    interconnect_type = enum_values['interconnect_type']
    link_type = enum_values['link_type']

    location_ref = self.LOCATION_ARG.ResolveAsResource(args, holder.resources)

    return interconnect.Create(
        description=args.description,
        interconnect_type=interconnect_type,
        requested_link_count=args.requested_link_count,
        link_type=link_type,
        admin_enabled=args.admin_enabled,
        noc_contact_email=args.noc_contact_email,
        location=location_ref.SelfLink())
