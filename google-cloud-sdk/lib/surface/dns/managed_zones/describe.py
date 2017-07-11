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

"""gcloud dns managed-zone describe command."""

from googlecloudsdk.api_lib.dns import util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.dns import flags
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


@base.ReleaseTracks(base.ReleaseTrack.GA)
class Describe(base.DescribeCommand):
  """View the details of a Cloud DNS managed-zone.

  This command displays the details of the specified managed-zone.

  ## EXAMPLES

  To display the details of your managed-zone, run:

    $ {command} my_zone
  """

  @staticmethod
  def Args(parser):
    flags.GetDnsZoneArg(
        'The name of the managed-zone to be described.').AddToParser(parser)

  def Run(self, args):
    dns = apis.GetClientInstance('dns', 'v1')
    zone_ref = resources.REGISTRY.Parse(
        args.dns_zone,
        params={
            'project': properties.VALUES.core.project.GetOrFail,
        },
        collection='dns.managedZones')

    return dns.managedZones.Get(
        dns.MESSAGES_MODULE.DnsManagedZonesGetRequest(
            project=zone_ref.project,
            managedZone=zone_ref.managedZone))


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class DescribeBeta(base.DescribeCommand):
  """View the details of a Cloud DNS managed-zone.

  This command displays the details of the specified managed-zone.

  ## EXAMPLES

  To display the details of your managed-zone, run:

    $ {command} my_zone
  """

  @staticmethod
  def Args(parser):
    flags.GetDnsZoneArg(
        'The name of the managed-zone to be described.').AddToParser(parser)

  def Run(self, args):
    dns = apis.GetClientInstance('dns', 'v2beta1')
    zone_ref = util.GetRegistry('v2beta1').Parse(
        args.dns_zone,
        params={
            'project': properties.VALUES.core.project.GetOrFail,
        },
        collection='dns.managedZones')

    return dns.managedZones.Get(
        dns.MESSAGES_MODULE.DnsManagedZonesGetRequest(
            project=zone_ref.project,
            managedZone=zone_ref.managedZone))
