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


"""Command to cancel a bio operation."""

from StringIO import StringIO

from googlecloudsdk.api_lib.bio import bio
from googlecloudsdk.api_lib.bio import errors
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import display
from googlecloudsdk.command_lib.bio import flags
from googlecloudsdk.command_lib.bio import util as command_lib_util
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.resource import resource_printer


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class Delete(base.Command):
  """Cancel a bio operation.

  Cancels the operation with the given operation name.

  This command can fail for the following reasons:
  * The operation specified does not exist.
  * The active account does not have Writer permissions for the operation's
  project.

  ## EXAMPLES

  The following command cancels the operation with the name
  `OP-NAMES-ARE-A-UNIQUE-HASH`:

    $ {command} OP-NAMES-ARE-A-UNIQUE-HASH
  """

  @staticmethod
  def Args(parser):
    flags.GetOperationNameFlag('cancel').AddToParser(parser)

  def Run(self, args):
    operations = bio.Operations(properties.VALUES.core.project.Get())

    operation_ref = command_lib_util.ParseOperation(args.name)
    op = operations.Get(operation_ref)

    operation_string = StringIO()
    print_format = display.Displayer(self, args).GetFormat()
    resource_printer.Print(op, print_format, out=operation_string)

    if not console_io.PromptContinue(message='{0}\n{1}'.format(
        operation_string.getvalue(), 'This operation will be canceled')):
      raise errors.BioError('Cancel aborted by user.')

    operations.Cancel(operation_ref)

    log.status.Print('Canceled [{0}].'.format(args.name))
