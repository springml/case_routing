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
"""Implementation of gcloud genomics operations cancel.
"""

from StringIO import StringIO

from googlecloudsdk.api_lib.genomics import genomics_util
from googlecloudsdk.api_lib.genomics.exceptions import GenomicsError
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import display
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.resource import resource_printer

_OPERATIONS_PREFIX = 'operations/'


class Cancel(base.Command):
  """Cancels an operation.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('name',
                        type=str,
                        help='The name of the operation to be canceled. The '
                        '"{0}" prefix for the name is optional.'
                        .format(_OPERATIONS_PREFIX))

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.

    Raises:
      HttpException: An http error response was received while executing api
          request.
    Returns:
      None
    """
    apitools_client = genomics_util.GetGenomicsClient()
    genomics_messages = genomics_util.GetGenomicsMessages()

    name = args.name
    if not name.startswith(_OPERATIONS_PREFIX):
      name = _OPERATIONS_PREFIX + name

    # Look up the operation so we can display it in the confirmation prompt
    op = apitools_client.operations.Get(
        genomics_messages.GenomicsOperationsGetRequest(name=name))
    operation_string = StringIO()
    print_format = display.Displayer(self, args).GetFormat()
    resource_printer.Print(op, print_format, out=operation_string)

    if not console_io.PromptContinue(message='%s\n%s' % (
        operation_string.getvalue(), 'This operation will be canceled')):
      raise GenomicsError('Cancel aborted by user.')

    apitools_client.operations.Cancel(
        genomics_messages.GenomicsOperationsCancelRequest(name=name))
    log.status.write('Canceled [{0}].\n'.format(name))
