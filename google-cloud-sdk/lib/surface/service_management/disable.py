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

"""service-management disable command."""

from googlecloudsdk.api_lib.service_management import services_util
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.service_management import arg_parsers
from googlecloudsdk.command_lib.service_management import common_flags
from googlecloudsdk.core import properties


_DETAILED_HELP = {
    'DESCRIPTION': """\
        This command disables a previously-enabled service for consumption.

        To see a list of the enabled services for a project, run:

          $ {parent_command} list --enabled

        More information on listing services can be found at:
        https://cloud.google.com/service-management/list-services and on
        disabling a service at:
        https://cloud.google.com/service-management/enable-disable#disabling_services
        """,
    'EXAMPLES': """\
        To disable a service called `my-consumed-service` for the active
        project, run:

          $ {command} my-consumed-service

        To run the same command asynchronously (non-blocking), run:

          $ {command} my-consumed-service --async
        """,
}


class Disable(base.SilentCommand):
  """Disables a service for consumption for a project."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    common_flags.consumer_service_flag(suffix='to disable').AddToParser(parser)
    base.ASYNC_FLAG.AddToParser(parser)

  def Run(self, args):
    """Run 'service-management disable'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      The response from the consumer settings API call.
    """
    messages = services_util.GetMessagesModule()
    client = services_util.GetClientInstance()

    project = properties.VALUES.core.project.Get(required=True)
    service = arg_parsers.GetServiceNameFromArg(args.service)
    request = messages.ServicemanagementServicesDisableRequest(
        serviceName=service,
        disableServiceRequest=messages.DisableServiceRequest(
            consumerId='project:' + project))
    operation = client.services.Disable(request)
    return services_util.ProcessOperationResult(operation, args.async)


Disable.detailed_help = _DETAILED_HELP
