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
"""gcloud dns dnskeys describe command."""

from googlecloudsdk.api_lib.dns import util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.dns import flags
from googlecloudsdk.core import properties
from googlecloudsdk.core.resource import resource_projector


ALGORITHM_NUMBERS = {
    'RSAMD5': 1,
    'DH': 2,
    'DSA': 3,
    'RSASHA1': 5,
    'DSANSEC3SHA1': 6,
    'RSASHA1NSEC3SHA1': 7,
    'RSASHA256': 8,
    'RSASHA512': 10,
    'ECCGOST': 12,
    'ECDSAP256SHA256': 13,
    'ECDSAP384SHA384': 14,
}


DIGEST_TYPE_NUMBERS = {
    'SHA1': 1,
    'SHA256': 2,
    'SHA384': 4,
}


def _GenerateDSRecord(key):
  key_tag = str(key.keyTag)
  key_algorithm = str(ALGORITHM_NUMBERS[key.algorithm.name])
  digest_algorithm = str(DIGEST_TYPE_NUMBERS[key.digests[0].type.name])
  digest = key.digests[0].digest
  return ' '.join([key_tag, key_algorithm, digest_algorithm, digest])


class Describe(base.DescribeCommand):
  """Get a DnsKey.

  This command displays the details of a single DnsKey.

  ## EXAMPLES

  To get a DnsKey from a managed-zone, run:

    $ {command} my_zone --key_id my_key
  """

  @staticmethod
  def Args(parser):
    flags.GetZoneArg(
        'The name of the managed-zone the DnsKey belongs to'
    ).AddToParser(parser)
    flags.GetKeyArg().AddToParser(parser)

  def Run(self, args):
    dns_client = apis.GetClientInstance('dns', 'v2beta1')

    zone_ref = util.GetRegistry('v2beta1').Parse(
        args.zone,
        params={
            'project': properties.VALUES.core.project.GetOrFail,
        },
        collection='dns.managedZones')

    result_object = dns_client.dnsKeys.Get(
        dns_client.MESSAGES_MODULE.DnsDnsKeysGetRequest(
            dnsKeyId=args.key_id,
            managedZone=zone_ref.Name(),
            project=zone_ref.project))
    result_dict = resource_projector.MakeSerializable(result_object)
    if result_object.type.name == 'KEY_SIGNING':
      result_dict['dsRecord'] = _GenerateDSRecord(result_object)
    return result_dict
