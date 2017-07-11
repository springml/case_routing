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
"""Implementation of the gcloud genomics operations list command.
"""

from apitools.base.py import list_pager

from googlecloudsdk.api_lib.genomics import genomics_util
from googlecloudsdk.calliope import base


class List(base.Command):
  """List Genomics operations in a project.

  Prints a table with summary information on operations in the project.
  """

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    base.LIMIT_FLAG.AddToParser(parser)
    parser.add_argument(
        '--where',
        default='',
        type=str,
        help="""\
        A string for filtering operations. The following filter fields are
        supported:

            createTime - The time this job was created, in seconds from the
                         epoch. Can use '>=' and/or '<=' operators.
            status     - Can be 'RUNNING', 'SUCCESS', 'FAILURE' or 'CANCELED'.
                         Only one status may be specified.
            labels.key - 'key' is a label key to match against a target value.

        Example:

            'createTime >= 1432140000 AND
             createTime <= 1432150000 AND
             labels.batch = test AND
             status = RUNNING'

        To calculate the timestamp as seconds from the epoch, on UNIX-like
        systems (e.g.: Linux, Mac) use the 'date' command:

          $ date --date '20150701' '+%s'

          1435734000

        or with Python (e.g.: Linux, Mac, Windows):

          $ python -c 'from time import mktime, strptime; print int(mktime(strptime("01 July 2015", "%d %B %Y")))'

          1435734000
        """)

  def Run(self, args):
    """Run 'operations list'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      The list of operations for this project.
    """
    apitools_client = genomics_util.GetGenomicsClient()
    genomics_messages = genomics_util.GetGenomicsMessages()

    if args.where:
      args.where += ' AND '

    args.where += 'projectId=%s' % genomics_util.GetProjectId()

    request = genomics_messages.GenomicsOperationsListRequest(
        name='operations',
        filter=args.where)

    return list_pager.YieldFromList(
        apitools_client.operations, request,
        limit=args.limit,
        batch_size_attribute='pageSize',
        batch_size=args.limit,  # Use limit if any, else server default.
        field='operations')
