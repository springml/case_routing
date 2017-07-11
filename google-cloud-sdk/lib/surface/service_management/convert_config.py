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

"""service-management convert-config command."""

import os

from apitools.base.py import encoding

from googlecloudsdk.api_lib.service_management import exceptions
from googlecloudsdk.api_lib.service_management import services_util

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import log


@base.ReleaseTracks(base.ReleaseTrack.ALPHA, base.ReleaseTrack.BETA)
class ConvertConfig(base.Command):
  """Convert Swagger specification to Google service configuration.

  DEPRECATED: This command is deprecated and will be removed soon.
  """

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument(
        'open_api_file',
        help='The file path containing the Open API specification to convert.')
    parser.add_argument(
        'output_file', nargs='?', default='',
        help=('The file path of the output file containing the converted '
              'configuration. Output to standard output if omitted.'))
    parser.display_info.AddFormat('json')

  def Run(self, args):
    """Run 'service-management convert-config'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      The response from the ConvertConfig API call.

    Raises:
      IOError: An IOError is returned if the input file cannot be read, or
          the output file cannot be written to.
    """
    log.warn('This command is deprecated and will be removed soon.')

    messages = services_util.GetMessagesModule()
    client = services_util.GetClientInstance()

    # TODO(b/36057355): Add support for swagger file references later
    # This requires the API to support multiple files first. b/23353397
    try:
      with open(args.open_api_file) as f:
        open_api_spec = messages.OpenApiSpec(openApiFiles=[
            messages.ConfigFile(
                filePath=os.path.basename(args.open_api_file),
                contents=f.read())
        ])
    except IOError:
      raise calliope_exceptions.NewErrorFromCurrentException(
          exceptions.FileOpenError,
          'Cannot open {f} file'.format(f=args.open_api_file))

    request = messages.ConvertConfigRequest(openApiSpec=open_api_spec)

    converted_config = client.v1.ConvertConfig(request)
    diagnostics = converted_config.diagnostics
    if diagnostics:
      kind = messages.Diagnostic.KindValueValuesEnum
      for diagnostic in diagnostics:
        logger = log.error if diagnostic.kind == kind.ERROR else log.warning
        logger('{l}: {m}'.format(l=diagnostic.location, m=diagnostic.message))

    service = converted_config.serviceConfig
    if service:
      if args.output_file:
        try:
          with open(args.output_file, 'w') as out:
            out.write(encoding.MessageToJson(service))
        except IOError:
          raise calliope_exceptions.NewErrorFromCurrentException(
              exceptions.FileOpenError,
              'Cannot open output file \'{f}\''.format(f=args.output_file))
      else:
        return service
