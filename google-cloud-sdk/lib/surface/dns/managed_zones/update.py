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
"""gcloud dns managed-zone update command."""

from googlecloudsdk.api_lib.dns import util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.dns import flags
from googlecloudsdk.command_lib.dns import util as command_util
from googlecloudsdk.core import properties


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class Update(base.UpdateCommand):
  """Update an existing Cloud DNS managed-zone.

  Update an existing Cloud DNS managed-zone.

  ## EXAMPLES

  To change the description of a managed-zone, run:

    $ {command} my_zone --description="Hello, world!"

  """

  @staticmethod
  def Args(parser):
    flags.GetDnsZoneArg(
        'The name of the managed-zone to be updated..').AddToParser(parser)
    flags.AddCommonManagedZonesDnssecArgs(parser)
    flags.GetManagedZonesDescriptionArg().AddToParser(parser)
    parser.display_info.AddCacheUpdater(flags.ManagedZoneCompleter)

  def Run(self, args):
    dns = apis.GetClientInstance('dns', 'v2beta1')
    messages = apis.GetMessagesModule('dns', 'v2beta1')

    zone_ref = util.GetRegistry('v2beta1').Parse(
        args.dns_zone,
        params={
            'project': properties.VALUES.core.project.GetOrFail,
        },
        collection='dns.managedZones')

    dnssec_config = command_util.ParseDnssecConfigArgs(args, messages)
    zone_args = {'name': args.dns_zone}
    if dnssec_config is not None:
      zone_args['dnssecConfig'] = dnssec_config
    if args.description is not None:
      zone_args['description'] = args.description
    zone = messages.ManagedZone(**zone_args)

    result = dns.managedZones.Patch(
        messages.DnsManagedZonesPatchRequest(managedZoneResource=zone,
                                             project=zone_ref.project,
                                             managedZone=args.dns_zone))
    return result
