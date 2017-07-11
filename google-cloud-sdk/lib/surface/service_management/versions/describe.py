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

"""service-management versions describe command."""

from googlecloudsdk.api_lib.service_management import services_util
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.service_management import common_flags


class Describe(base.DescribeCommand):
  """Describes the configuration for a given version of a service.

  DEPRECATED: This command is deprecated and will be removed.
  Use 'gcloud beta service-management configs describe' instead.
  """

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    common_flags.producer_service_flag(
        suffix='from which to retrieve the configuration').AddToParser(parser)

    parser.add_argument('--version',
                        help='The particular version for which to retrieve '
                             'the configuration. Defaults to the active '
                             'version.')

  def Run(self, args):
    """Run 'service-management versions describe'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      The response from the Get API call.
    """

    # Check if the user wants the latest version or a specified version.
    if args.version:
      return self._GetSpecificVersionConfig(args.service, args.version)
    else:
      return self._GetLatestVersionConfig(args.service)

  def _GetSpecificVersionConfig(self, service, version):
    messages = services_util.GetMessagesModule()
    client = services_util.GetClientInstance()
    request = messages.ServicemanagementServicesConfigsGetRequest(
        serviceName=service, configId=version)
    return client.services_configs.Get(request)

  def _GetLatestVersionConfig(self, service):
    messages = services_util.GetMessagesModule()
    client = services_util.GetClientInstance()
    request = messages.ServicemanagementServicesGetRequest(
        serviceName=service, expand='service_config')
    service_result = client.services.Get(request)

    # Return the service config from the service result
    return service_result.serviceConfig
