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

"""'logging metrics create' command."""

from googlecloudsdk.api_lib.logging import util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log


class Create(base.CreateCommand):
  """Creates a logs-based metric."""

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('metric_name', help='The name of the new metric.')
    parser.add_argument(
        '--description', required=True,
        help='The metric\'s description.')
    parser.add_argument(
        '--log-filter', required=True,
        help='The metric\'s filter expression. '
             'The filter must be for a V2 LogEntry.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      The created metric.
    """
    messages = util.GetMessages()
    new_metric = messages.LogMetric(name=args.metric_name,
                                    description=args.description,
                                    filter=args.log_filter)

    result = util.GetClient().projects_metrics.Create(
        messages.LoggingProjectsMetricsCreateRequest(
            parent=util.GetCurrentProjectParent(), logMetric=new_metric))
    log.CreatedResource(args.metric_name)
    return result


Create.detailed_help = {
    'DESCRIPTION': """\
        Creates a logs-based metric to count the number of log entries that
        match a filter expression.
        When creating a metric, the filter expression must not be empty.
    """,
    'EXAMPLES': """\
        To create a metric that counts the number of log entries with a
        severity level higher than WARNING, run:

          $ {command} high_severity_count --description="Number of high severity log entries" --log-filter="severity > WARNING"

        Detailed information about filters can be found at:
        [](https://cloud.google.com/logging/docs/view/advanced_filters)
    """,
}
