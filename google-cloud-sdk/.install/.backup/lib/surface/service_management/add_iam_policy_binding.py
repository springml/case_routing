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

"""Command for adding a principal to a service's access policy."""

import httplib

from apitools.base.py import exceptions as apitools_exceptions

from googlecloudsdk.api_lib.service_management import services_util
from googlecloudsdk.api_lib.util import exceptions
from googlecloudsdk.api_lib.util import http_retry
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.command_lib.service_management import arg_parsers
from googlecloudsdk.command_lib.service_management import common_flags


class AddIamPolicyBinding(base.Command):
  """Adds IAM policy binding to a service's access policy."""

  detailed_help = iam_util.GetDetailedHelpForAddIamPolicyBinding(
      'service', 'my-service', role='roles/servicemanagement.serviceConsumer')

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    service_flag = common_flags.producer_service_flag(
        suffix='to which the member is to be added')
    service_flag.AddToParser(parser)

    iam_util.AddArgsForAddIamPolicyBinding(parser)

  @http_retry.RetryOnHttpStatus(httplib.CONFLICT)
  def Run(self, args):
    """Run 'service-management add-iam-policy-binding'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      The response from the access API call.

    Raises:
      ToolException: An error such as specifying a label that doesn't exist
        or a principal that is already a member of the service or visibility
        label.
    """
    messages = services_util.GetMessagesModule()
    client = services_util.GetClientInstance()

    service = arg_parsers.GetServiceNameFromArg(args.service)

    request = messages.ServicemanagementServicesGetIamPolicyRequest(
        servicesId=service)

    try:
      policy = client.services.GetIamPolicy(request)
    except apitools_exceptions.HttpError as error:
      # If the error is a 404, no IAM policy exists, so just create a blank one.
      exc = exceptions.HttpException(error)
      if exc.payload.status_code == 404:
        policy = messages.Policy()
      else:
        raise

    iam_util.AddBindingToIamPolicy(
        messages.Binding, policy, args.member, args.role)

    # Send updated access policy to backend
    request = messages.ServicemanagementServicesSetIamPolicyRequest(
        servicesId=service,
        setIamPolicyRequest=(messages.SetIamPolicyRequest(policy=policy)))
    return client.services.SetIamPolicy(request)
