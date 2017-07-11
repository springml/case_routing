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
"""Command for listing disk types."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties


@base.ReleaseTracks(base.ReleaseTrack.BETA, base.ReleaseTrack.GA)
class List(base_classes.ZonalLister):
  """List Google Compute Engine disk types."""

  @property
  def service(self):
    return self.compute.diskTypes

  @property
  def resource_type(self):
    return 'diskTypes'


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class ListAlpha(base.ListCommand):
  """List Google Compute Engine disk types."""

  SCOPES = (base_classes.ScopeType.regional_scope,
            base_classes.ScopeType.zonal_scope)

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'names',
        metavar='NAME',
        nargs='*',
        default=[],
        completion_resource='compute.diskTypes',
        help=('If provided, show details for the specified names and/or URIs '
              'of resources.'))
    parser.add_argument(
        '--regexp', '-r',
        help="""\
        A regular expression to filter the names of the results on. Any names
        that do not match the entire regular expression will be filtered out.
        """)

    scope = parser.add_mutually_exclusive_group()
    scope.add_argument(
        '--zones',
        metavar='ZONE',
        help=('If provided, only zonal resources are shown. '
              'If arguments are provided, only resources from the given '
              'zones are shown.'),
        type=arg_parsers.ArgList())
    scope.add_argument(
        '--regions',
        metavar='REGION',
        help=('If provided, only regional resources are shown. '
              'If arguments are provided, only resources from the given '
              'regions are shown.'),
        type=arg_parsers.ArgList())

    parser.display_info.AddFormat("""
          table(
            name,
            location():label=LOCATION,
            location_scope():label=SCOPE,
            validDiskSize:label=VALID_DISK_SIZES
          )
    """)

  def _GetFilter(self, names, name_regex, zones, regions):
    result = []
    if names:
      result.append('(name eq {0})'.format('|'.join(names)))
    if name_regex:
      result.append('(name eq {0})'.format(name_regex))
    if zones:
      result.append('(zone eq {0})'.format('|'.join(zones)))
    if regions:
      result.append('(region eq {0})'.format('|'.join(regions)))
    return ''.join(result)

  def _GetListPage(self, compute_disk_types, request):
    response = compute_disk_types.AggregatedList(request)
    disk_types_lists = []
    for disk_in_scope in response.items.additionalProperties:
      disk_types_lists += disk_in_scope.value.diskTypes
    return disk_types_lists, response.nextPageToken

  def Run(self, args):
    compute_disk_types = apis.GetClientInstance('compute', 'alpha').diskTypes
    messages = apis.GetMessagesModule('compute', 'alpha')

    request = messages.ComputeDiskTypesAggregatedListRequest(
        filter=self._GetFilter(
            args.names, args.regexp, args.zones, args.regions),
        project=properties.VALUES.core.project.Get(required=True),
    )

    # TODO(b/34871930): Write and use helper for handling listing.
    disk_types_lists, next_page_token = self._GetListPage(
        compute_disk_types, request)
    while next_page_token:
      request.pageToken = next_page_token
      disk_types_list_page, next_page_token = self._GetListPage(
          compute_disk_types, request)
      disk_types_lists += disk_types_list_page
    return disk_types_lists


List.detailed_help = base_classes.GetZonalListerHelp('disk types')
ListAlpha.detailed_help = base_classes.GetMultiScopeListerHelp(
    'disk types', ListAlpha.SCOPES)
