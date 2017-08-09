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

"""A command that reads JSON data and lists it."""

import json
import sys

from googlecloudsdk.calliope import base


class ListFromJson(base.ListCommand):
  """Read JSON data and list it on the standard output.

  *{command}* is a test harness for resource output formatting and filtering.
  It behaves like any other `gcloud ... list` command except that the resources
  are read from a JSON data file.

  The input JSON data is either a single resource object or a list of resource
  objects of the same type. The resources are printed on the standard output.
  The default output format is *json*.
  """

  @staticmethod
  def Args(parser):
    base.URI_FLAG.RemoveFromParser(parser)
    parser.add_argument(
        'json_file',
        metavar='JSON-FILE',
        nargs='?',
        default=None,
        help=('A file containing JSON data for a single resource or a list of'
              ' resources of the same type. If omitted then the standard input'
              ' is read.'))
    parser.display_info.AddFormat('json')
    parser.display_info.AddCacheUpdater(None)  # No resource URIs.

  def Run(self, args):
    if args.json_file:
      with open(args.json_file, 'r') as f:
        resources = json.load(f)
    else:
      resources = json.load(sys.stdin)
    return resources
