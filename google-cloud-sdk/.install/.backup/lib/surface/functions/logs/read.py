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

"""'functions get-logs' command."""

from googlecloudsdk.api_lib.functions import util
from googlecloudsdk.api_lib.logging import common as logging_common
from googlecloudsdk.api_lib.logging import util as logging_util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.functions import flags
from googlecloudsdk.core import properties


class GetLogs(base.ListCommand):
  """Show logs produced by functions.

  Display log entries produced by all functions running in a region, or by a
  single function if it is specified through a command argument. By default,
  when no extra flags are specified, the most recent 20 log entries
  are displayed.
  """

  SEVERITIES = ['DEBUG', 'INFO', 'ERROR']

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    flags.AddRegionFlag(parser)
    base.LIMIT_FLAG.RemoveFromParser(parser)
    parser.add_argument(
        'name', nargs='?',
        help=('Name of the function which logs are to be displayed. If no name '
              'is specified, logs from all functions are displayed.'))
    parser.add_argument(
        '--execution-id',
        help=('Execution ID for which logs are to be displayed.'))
    parser.add_argument(
        '--start-time', required=False, type=arg_parsers.Datetime.Parse,
        help=('Return only log entries which timestamps are not earlier than '
              'the specified time. The timestamp must be in RFC3339 UTC "Zulu" '
              'format. If --start-time is specified, the command returns '
              '--limit earliest log entries which appeared after '
              '--start-time.'))
    parser.add_argument(
        '--end-time', required=False, type=arg_parsers.Datetime.Parse,
        help=('Return only log entries which timestamps are not later than '
              'the specified time. The timestamp must be in RFC3339 UTC "Zulu" '
              'format. If --end-time is specified but --start-time is not, the '
              'command returns --limit latest log entries which appeared '
              'before --end-time.'))
    parser.add_argument(
        '--limit', required=False, type=arg_parsers.BoundedInt(1, 1000),
        default=20,
        help=('Number of log entries to be fetched; must not be greater than '
              '1000.'))
    parser.add_argument(
        '--min-log-level', choices=GetLogs.SEVERITIES,
        help='Minimum level of logs to be fetched.')
    parser.add_argument(
        '--show-log-levels', action='store_true', default=True,
        help=('Print a log level of each log entry.'))
    parser.add_argument(
        '--show-function-names', action='store_true', default=True,
        help=('Print a function name before each log entry.'))
    parser.add_argument(
        '--show-execution-ids', action='store_true', default=True,
        help=('Print an execution ID before each log entry.'))
    parser.add_argument(
        '--show-timestamps', action='store_true', default=True,
        help=('Print a UTC timestamp before each log entry.'))

  @util.CatchHTTPErrorRaiseHTTPException
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      A generator of objects representing log entries.
    """
    if not args.IsSpecified('format'):
      args.format = self._Format(args)

    return self._Run(args)

  def _Run(self, args):
    region = properties.VALUES.functions.region.Get()
    log_filter = ['resource.type="cloud_function"',
                  'resource.labels.region="%s"' % region,
                  'logName:"cloud-functions"']

    if args.name:
      log_filter.append('resource.labels.function_name="%s"' % args.name)
    if args.execution_id:
      log_filter.append('labels.execution_id="%s"' % args.execution_id)
    if args.min_log_level:
      log_filter.append('severity>=%s' % args.min_log_level)
    if args.start_time:
      order = 'ASC'
      log_filter.append(
          'timestamp>="%s"' % logging_util.FormatTimestamp(args.start_time))
    else:
      order = 'DESC'
    if args.end_time:
      log_filter.append(
          'timestamp<="%s"' % logging_util.FormatTimestamp(args.end_time))
    log_filter = ' '.join(log_filter)
    # TODO(b/36057251): Consider using paging for listing more than 1000 log
    # entries. However, reversing the order of received latest N entries before
    # a specified timestamp would be problematic with paging.

    entries = logging_common.FetchLogs(
        log_filter, order_by=order, limit=args.limit)

    if order == 'DESC':
      entries = reversed(list(entries))  # Force generator expansion with list.

    for entry in entries:
      row = {'log': entry.textPayload}
      if entry.severity:
        severity = str(entry.severity)
        if severity in GetLogs.SEVERITIES:
          # Use short form (first letter) for expected severities.
          row['level'] = severity[0]
        else:
          # Print full form of unexpected severities.
          row['level'] = severity
      if entry.resource and entry.resource.labels:
        for label in entry.resource.labels.additionalProperties:
          if label.key == 'function_name':
            row['name'] = label.value
      if entry.labels:
        for label in entry.labels.additionalProperties:
          if label.key == 'execution_id':
            row['execution_id'] = label.value
      if entry.timestamp:
        row['time_utc'] = util.FormatTimestamp(entry.timestamp)
      yield row

  def _Format(self, args):
    fields = []
    if args.show_log_levels:
      fields.append('level')
    if args.show_function_names:
      fields.append('name')
    if args.show_execution_ids:
      fields.append('execution_id')
    if args.show_timestamps:
      fields.append('time_utc')
    fields.append('log')
    return 'table({0})'.format(','.join(fields))
