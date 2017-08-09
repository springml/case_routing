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

"""'logging metrics update' command."""

from googlecloudsdk.api_lib.logging import util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log


class Update(base.UpdateCommand):
  """Updates the definition of a logs-based metric."""

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        'metric_name', help='The name of the log-based metric to update.')
    parser.add_argument(
        '--description', required=False,
        help=('A new description for the metric. '
              'If omitted, the description is not changed.'))
    parser.add_argument(
        '--log-filter', required=False,
        help=('A new filter string for the metric. '
              'If omitted, the filter is not changed.'))

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to
        this command invocation.

    Returns:
      The updated metric.
    """
    # One of the flags is required to update the metric.
    if not (args.description or args.log_filter):
      raise exceptions.ToolException(
          '--description or --log-filter argument is required')

    # Calling the API's Update method on a non-existing metric creates it.
    # Make sure the metric exists so we don't accidentally create it.
    metric = util.GetClient().projects_metrics.Get(
        util.GetMessages().LoggingProjectsMetricsGetRequest(
            metricName=util.CreateResourceName(
                util.GetCurrentProjectParent(), 'metrics', args.metric_name)))

    if args.description:
      metric_description = args.description
    else:
      metric_description = metric.description
    if args.log_filter:
      metric_filter = args.log_filter
    else:
      metric_filter = metric.filter

    updated_metric = util.GetMessages().LogMetric(
        name=args.metric_name,
        description=metric_description,
        filter=metric_filter)

    result = util.GetClient().projects_metrics.Update(
        util.GetMessages().LoggingProjectsMetricsUpdateRequest(
            metricName=util.CreateResourceName(
                util.GetCurrentProjectParent(), 'metrics', args.metric_name),
            logMetric=updated_metric))
    log.UpdatedResource(args.metric_name)
    return result


Update.detailed_help = {
    'DESCRIPTION': """\
        Updates the description or the filter expression of an existing
        logs-based metric.
    """,
    'EXAMPLES': """\
        To update the description of a metric called high_severity_count, run:

          $ {command} high_severity_count --description="Count of high-severity log entries."

        To update the filter expression of the metric, run:

          $ {command} high_severity_count --log-filter="severity >= WARNING"

        Detailed information about filters can be found at:
        [](https://cloud.google.com/logging/docs/view/advanced_filters)
    """,
}
