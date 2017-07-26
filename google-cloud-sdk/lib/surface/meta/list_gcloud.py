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

"""A command that lists the gcloud group and command tree with details."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import walker_util


class ListGCloud(base.Command):
  """List the gcloud CLI command tree with flag, positional and help details."""

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--hidden',
        action='store_true',
        default=None,
        help=('Include hidden commands and groups.'))
    parser.add_argument(
        'restrict',
        metavar='COMMAND/GROUP',
        nargs='*',
        default=None,
        help=('Restrict the tree to these dotted command paths. '
              'For example: gcloud.alpha gcloud.beta.test'))

  def DeprecatedFormat(self, unused_args):
    return 'json'

  def Run(self, args):
    return walker_util.GCloudTreeGenerator(self._cli_power_users_only).Walk(
        args.hidden, args.restrict)
