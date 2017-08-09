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

"""Command for listing Cloud CDN cache invalidations."""

import sys

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import constants
from googlecloudsdk.api_lib.compute import request_helper
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import arg_parsers


class ListCacheInvalidations(base_classes.BaseLister):
  """List Cloud CDN cache invalidations for a URL map."""

  detailed_help = {
      'DESCRIPTION': """\
List Cloud CDN cache invalidations for a URL map. A cache invalidation instructs
Cloud CDN to stop using cached content. You can list invalidations to check
which have completed.
""",
  }

  @staticmethod
  def _Flags(parser):
    parser.add_argument(
        '--limit',
        type=arg_parsers.BoundedInt(1, sys.maxint, unlimited=True),
        help='The maximum number of invalidations to list.')

  @staticmethod
  def Args(parser):
    parser.add_argument('urlmap', help='The name of the URL map.')

  @property
  def resource_type(self):
    return 'invalidations'

  @property
  def global_service(self):
    return self.compute.globalOperations

  def GetUrlMapGetRequest(self, args):
    return (
        self.compute.urlMaps,
        'Get',
        self.messages.ComputeUrlMapsGetRequest(
            project=self.project,
            urlMap=args.urlmap))

  def GetResources(self, args, errors):
    get_request = self.GetUrlMapGetRequest(args)

    new_errors = []
    objects = list(request_helper.MakeRequests(
        requests=[get_request],
        http=self.http,
        batch_url=self.batch_url,
        errors=new_errors))
    errors.extend(new_errors)
    if new_errors:
      utils.RaiseToolException(
          errors,
          error_message='Could not fetch resource:')
    urlmap_id = objects[0].id
    filter_expr = ('(operationType eq invalidateCache) (targetId eq '
                   '{urlmap_id})').format(urlmap_id=urlmap_id)
    max_results = args.limit or constants.MAX_RESULTS_PER_PAGE
    project = self.project
    requests = [
        (self.global_service, 'AggregatedList',
         self.global_service.GetRequestType('AggregatedList')(
             filter=filter_expr,
             maxResults=max_results,
             orderBy='creationTimestamp desc',
             project=project))
    ]
    return request_helper.MakeRequests(requests=requests,
                                       http=self.http,
                                       batch_url=self.batch_url,
                                       errors=errors)

  def Run(self, args):
    args.names = []
    args.regexp = None
    args.uri = None
    return super(ListCacheInvalidations, self).Run(args)
