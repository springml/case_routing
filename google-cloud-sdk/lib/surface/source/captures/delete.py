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

"""Deletes captures in a project repository.
"""

from googlecloudsdk.api_lib.source import capture
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log


class Delete(base.DeleteCommand):
  """Delete source captures."""

  detailed_help = {
      'DESCRIPTION': """\
          This command deletes one or more source captures for a project.
      """
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'capture_id', metavar='ID', nargs='+',
        help="""\
            The ID of an existing capture to delete.
        """)

  def Run(self, args):
    """Run the delete command."""
    manager = capture.CaptureManager()
    deleted_list = []
    for name in args.capture_id:
      d = manager.DeleteCapture(name)
      log.DeletedResource(d, kind='source capture')
      deleted_list.append(d)
    return [deleted_list]
