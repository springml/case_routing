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
"""gcloud dns operations list command."""

import itertools
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.dns import util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties


class List(base.ListCommand):
  """View the list of all your operations.

  This command displays the list of your operations for one or more
  managed-zones.

  ## EXAMPLES

  To see the list of all operations for two managed-zones, run:

    $ {command} --zones zone1,zone2

  To see the last 5 operations for two managed-zones, run:

    $ {command} --zones zone1,zone2 --sort-by ~start_time --limit 5
  """

  @staticmethod
  def Args(parser):
    parser.display_info.AddFormat('table({fields})'.format(
        # The operations describe command needs both the zone name and the ID.
        # We need the zone name in the list output otherwise it gets confusing
        # when listing multiple zones. Since the zone name doesn't change, it
        # doesn't matter if we get it from oldValue or newValue.
        fields=','.join([
            'zoneContext.oldValue.name:label=ZONE_NAME:sort=1',
            'id',
            'startTime',
            'user',
            'type',
        ])))
    base.URI_FLAG.RemoveFromParser(parser)
    base.PAGE_SIZE_FLAG.RemoveFromParser(parser)
    parser.add_argument(
        '--zones',
        help='Names of one or more zones to read.',
        metavar='ZONES',
        type=arg_parsers.ArgList(),
        required=True)

  def Run(self, args):
    dns_client = apis.GetClientInstance('dns', 'v2beta1')

    zone_refs = [
        util.GetRegistry('v2beta1').Parse(
            zone,
            params={
                'project': properties.VALUES.core.project.GetOrFail,
            },
            collection='dns.managedZones')
        for zone in args.zones]
    requests = [
        dns_client.MESSAGES_MODULE.DnsManagedZoneOperationsListRequest(
            managedZone=zone_ref.Name(),
            project=zone_ref.project)
        for zone_ref in zone_refs]
    responses = [
        list_pager.YieldFromList(dns_client.managedZoneOperations,
                                 request,
                                 limit=args.limit,
                                 field='operations')
        for request in requests]

    return itertools.chain.from_iterable(responses)
