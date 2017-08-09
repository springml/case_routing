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
"""gcloud dns dnskeys list command."""

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.dns import util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.dns import flags
from googlecloudsdk.core import properties


class List(base.ListCommand):
  """View the list of all your DnsKeys.

  View the list of all your DnsKeys.

  ## EXAMPLES

  To see the list of all DnsKeys for a managed-zone, run:

    $ {command} my_zone
  """

  @staticmethod
  def Args(parser):
    parser.display_info.AddFormat('table(id,keyTag,type,isActive,description)')
    base.URI_FLAG.RemoveFromParser(parser)
    base.PAGE_SIZE_FLAG.RemoveFromParser(parser)
    flags.GetZoneArg(
        'The name of the managed-zone you want to list DnsKeys for.'
    ).AddToParser(parser)

  def Run(self, args):
    dns_client = apis.GetClientInstance('dns', 'v2beta1')

    zone_ref = util.GetRegistry('v2beta1').Parse(
        args.zone,
        params={
            'project': properties.VALUES.core.project.GetOrFail,
        },
        collection='dns.managedZones')

    return list_pager.YieldFromList(
        dns_client.dnsKeys,
        dns_client.MESSAGES_MODULE.DnsDnsKeysListRequest(
            project=zone_ref.project,
            managedZone=zone_ref.Name()),
        field='dnsKeys')
