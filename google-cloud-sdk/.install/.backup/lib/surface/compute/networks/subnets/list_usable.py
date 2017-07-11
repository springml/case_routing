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
"""Command for list subnetworks which the current user has permission to use."""

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class ListUsableSubnets(base.ListCommand):
  """List subnetworks which the current user has permission to use."""

  @staticmethod
  def Args(parser):
    pass

  def Collection(self):
    return 'compute.subnetworks'

  def GetUriFunc(self):
    def _GetUri(search_result):
      return ''.join([
          p.value.string_value
          for p
          in search_result.resource.additionalProperties
          if p.key == 'selfLink'])
    return _GetUri

  def Run(self, args):
    messages = apis.GetMessagesModule('cloudresourcesearch', 'v1')
    client = apis.GetClientInstance('cloudresourcesearch', 'v1')
    request = messages.CloudresourcesearchResourcesSearchRequest(
        query='@type="type.googleapis.com/compute.Subnetwork"'
              ' withPermission(compute.subnetworks.use)')
    return list_pager.YieldFromList(
        client.resources,
        request,
        method='Search',
        batch_size_attribute='pageSize',
        batch_size=100,
        field='results')

  def DeprecatedFormat(self, args):
    return 'table({fields})'.format(
        fields=','.join([
            'resource.selfLink.segment(-5):label=PROJECT',
            'resource.region.segment(-1):label=REGION',
            'resource.network.segment(-1):label=NETWORK',
            'resource.selfLink.segment(-1):label=SUBNET',
            'resource.ipCidrRange:label=RANGE',
        ]))

ListUsableSubnets.detailed_help = {
    'brief': 'List subnetworks which the current user has permission to use.',
    'DESCRIPTION': """\
        *{command}* is used to list subnetworks which the current user has permission to use.
        """,
    'EXAMPLES': """\
          $ {command}
        """,
}
