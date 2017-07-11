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
"""Command for listing target SSL proxies."""

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


class List(base.ListCommand):
  """List target SSL proxies."""

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'names',
        metavar='NAME',
        nargs='*',
        default=[],
        completion_resource='compute.instances',
        help=('If provided, show details for the specified names and/or URIs '
              'of resources.'))

    parser.add_argument(
        '--regexp', '-r',
        help="""\
        A regular expression to filter the names of the results on. Any names
        that do not match the entire regular expression will be filtered out.
        """)

  def DeprecatedFormat(self, args):
    return """
        table(
          name,
          proxyHeader,
          service.basename(),
          sslCertificates.map().basename().list():label=SSL_CERTIFICATES
        )
    """

  def Run(self, args):
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())

    client = holder.client.apitools_client
    messages = client.MESSAGES_MODULE

    project = properties.VALUES.core.project.Get(required=True)

    # TODO(b/33298284): remove names and regexp arguments.
    filter_uris = []
    filter_names = []
    if args.names:
      log.warn('Name argument for filtering list results is deprecated. '
               'Please use --filter flag.')
    if args.regexp:
      log.warn('--regexp flag for filtering list results is deprecated. '
               'Please use --filter flag.')

    for name in args.names:
      try:
        ref = holder.resources.Parse(
            name,
            params={'project': project},
            collection='compute.targetSslProxies')
        filter_uris.append(ref.SelfLink())
      except resources.UserError:
        filter_names.append(name)

    request = messages.ComputeTargetSslProxiesListRequest(
        project=project,
        filter='name eq {0}'.format(args.regexp) if args.regexp else None
    )

    results = list_pager.YieldFromList(
        client.targetSslProxies, request, field='items',
        limit=args.limit, batch_size=None)

    for item in results:
      if not args.names:
        yield item

      elif item.selfLink in filter_uris or item.name in filter_names:
        yield item


List.detailed_help = base_classes.GetGlobalListerHelp('target SSL proxies')
