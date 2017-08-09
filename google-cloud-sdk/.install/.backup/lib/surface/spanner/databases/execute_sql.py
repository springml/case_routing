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
"""Command for spanner databases query."""

from googlecloudsdk.api_lib.spanner import database_sessions
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.spanner import flags
from googlecloudsdk.command_lib.spanner import sql
from googlecloudsdk.core import log


@base.UnicodeIsSupported
class Query(base.Command):
  """Executes a read-only SQL query against a Cloud Spanner database."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Please add arguments in alphabetical order except for no- or a clear-
    pair for that argument which can follow the argument itself.
    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    flags.Instance(positional=False).AddToParser(parser)
    flags.Database().AddToParser(parser)
    parser.add_argument(
        '--sql',
        required=True,
        help='The SQL query to issue to the database. Cloud Spanner SQL is '
             'described at https://cloud.google.com/spanner/docs/query-syntax')

    query_mode_choices = {
        'NORMAL':
            'Returns only the query result, without any information about '
            'the query plan.',
        'PLAN': 'Returns only the query plan, without any result rows or '
                'execution statistics information.',
        'PROFILE':
            'Returns both the query plan and the execution statistics along '
            'with the result rows.'
    }

    parser.add_argument(
        '--query-mode',
        default='NORMAL',
        type=str.upper,
        choices=query_mode_choices,
        help='Mode in which the query must be processed.')

  def Run(self, args):
    """Runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      Some value that we want to have printed later.
    """
    session = database_sessions.Create(args.instance, args.database)
    try:
      return database_sessions.ExecuteSql(session, args.sql, args.query_mode)
    finally:
      database_sessions.Delete(session)

  def Display(self, args, result):
    """Displays the server response to a query.

    This is called higher up the stack to over-write default display behavior.
    What gets displayed depends on the mode in which the query was run.
    'NORMAL': query result rows
    'PLAN': query plan without execution statistics
    'PROFILE': query result rows and the query plan with execution statistics

    Args:
      args: The arguments originally passed to the command.
      result: The output of the command before display.
    Raises:
      ValueError: The query mode is not valid.
    """
    if args.query_mode == 'NORMAL':
      sql.DisplayQueryResults(result, log.out)
    elif args.query_mode == 'PLAN':
      sql.DisplayQueryPlan(result, log.out)
    elif args.query_mode == 'PROFILE':
      if sql.QueryHasAggregateStats(result):
        sql.DisplayQueryAggregateStats(result.stats.queryStats, log.out)
      sql.DisplayQueryPlan(result, log.out)
      sql.DisplayQueryResults(result, log.status)
    else:
      raise ValueError('Invalid query mode: {}'.format(args.query_mode))
