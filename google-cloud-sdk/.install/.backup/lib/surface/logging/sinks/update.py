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

"""'logging sinks update' command."""

from apitools.base.py import exceptions as apitools_exceptions

from googlecloudsdk.api_lib.logging import util
from googlecloudsdk.api_lib.util import exceptions
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_io


class Update(base.UpdateCommand):
  """Updates a sink.

  Changes the *[destination]* or *--log-filter* associated with a sink.
  The new destination must already exist and Stackdriver Logging must have
  permission to write to it.
  Log entries are exported to the new destination immediately.

  ## EXAMPLES

  To only update a sink filter, run:

    $ {command} my-sink --log-filter='severity>=ERROR'

  Detailed information about filters can be found at:
  [](https://cloud.google.com/logging/docs/view/advanced_filters)
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        'sink_name', help='The name of the sink to update.')
    parser.add_argument(
        'destination', nargs='?',
        help=('A new destination for the sink. '
              'If omitted, the sink\'s existing destination is unchanged.'))
    parser.add_argument(
        '--log-filter', required=False,
        help=('A new filter expression for the sink. '
              'If omitted, the sink\'s existing filter (if any) is unchanged.'))
    parser.add_argument(
        '--output-version-format', required=False,
        help=('DEPRECATED. Format of the log entries being exported. '
              'Detailed information: '
              'https://cloud.google.com/logging/docs/api/introduction_v2'),
        choices=('V2',))
    util.AddNonProjectArgs(parser, 'Update a sink')

  def GetSink(self, parent, sink_ref):
    """Returns a sink specified by the arguments."""
    return util.GetClient().projects_sinks.Get(
        util.GetMessages().LoggingProjectsSinksGetRequest(
            sinkName=util.CreateResourceName(
                parent, 'sinks', sink_ref.sinksId)))

  def UpdateSink(self, parent, sink_data):
    """Updates a sink specified by the arguments."""
    messages = util.GetMessages()
    # Change string value to enum.
    sink_data['outputVersionFormat'] = getattr(
        messages.LogSink.OutputVersionFormatValueValuesEnum,
        sink_data['outputVersionFormat'])
    return util.GetClient().projects_sinks.Update(
        messages.LoggingProjectsSinksUpdateRequest(
            sinkName=util.CreateResourceName(
                parent, 'sinks', sink_data['name']),
            logSink=messages.LogSink(**sink_data),
            uniqueWriterIdentity=True))

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      The updated sink with its new destination.
    """
    if args.output_version_format:
      log.warn(
          '--output-version-format is deprecated and will soon be removed.')

    # One of the flags is required to update the sink.
    # log_filter can be an empty string, so check explicitly for None.
    if not (args.destination or args.log_filter is not None or
            args.output_version_format):
      raise calliope_exceptions.ToolException(
          '[destination], --log-filter or --output-version-format is required')

    sink_ref = resources.REGISTRY.Parse(
        args.sink_name,
        params={'projectsId': properties.VALUES.core.project.GetOrFail},
        collection='logging.projects.sinks')

    # Calling Update on a non-existing sink creates it.
    # We need to make sure it exists, otherwise we would create it.
    try:
      sink = self.GetSink(util.GetParentFromArgs(args), sink_ref)
    except apitools_exceptions.HttpError as error:
      if exceptions.HttpException(error).payload.status_code == 404:
        log.status.Print('Sink was not found.')
      raise error

    # Only update fields that were passed to the command.
    if args.destination:
      destination = args.destination
    else:
      destination = sink.destination

    if args.log_filter is not None:
      log_filter = args.log_filter
    else:
      log_filter = sink.filter

    if args.output_version_format:
      output_format = args.output_version_format
    else:
      output_format = sink.outputVersionFormat.name

    sink_data = {
        'name': sink_ref.sinksId,
        'destination': destination,
        'filter': log_filter,
        'outputVersionFormat': output_format,
        'includeChildren': sink.includeChildren,
        'startTime': sink.startTime,
        'endTime': sink.endTime
    }

    # Check for legacy configuration, and let users decide if they still want
    # to update the sink with new settings.
    if 'cloud-logs@' in sink.writerIdentity:
      console_io.PromptContinue(
          'This update will create a new writerIdentity (service account) for '
          'the sink. In order for the sink to continue working, grant that '
          'service account correct permission on the destination. The service '
          'account will be displayed after a successful update operation.',
          cancel_on_no=True, default=False)

    result = util.TypedLogSink(
        self.UpdateSink(util.GetParentFromArgs(args), sink_data))

    log.UpdatedResource(sink_ref, kind='sink')
    util.PrintPermissionInstructions(result.destination, result.writer_identity)
    return result
