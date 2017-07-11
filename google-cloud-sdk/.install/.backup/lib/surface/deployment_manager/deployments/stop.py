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

"""deployments stop command."""
from apitools.base.py import exceptions as apitools_exceptions

from googlecloudsdk.api_lib.deployment_manager import dm_v2_util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.deployment_manager import dm_base
from googlecloudsdk.command_lib.deployment_manager import dm_util
from googlecloudsdk.command_lib.deployment_manager import dm_write
from googlecloudsdk.command_lib.deployment_manager import flags
from googlecloudsdk.core import log

# Number of seconds (approximately) to wait for stop operation to complete.
OPERATION_TIMEOUT = 20 * 60  # 20 mins


class Stop(base.Command):
  """Stop a pending or running deployment update or creation.

  This command will stop a currently running or pending operation on
  a deployment.
  """

  detailed_help = {
      'EXAMPLES': """\
          To stop a running operation on a deployment, run:

            $ {command} my-deployment

          To issue a stop command without waiting for the operation to complete, run:

            $ {command} my-deployment --async

          To stop a running operation on a deployment providing a fingerprint, run:

            $ {command} my-deployment --fingerprint deployment-fingerprint
          """,
  }

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    flags.AddAsyncFlag(parser)
    flags.AddDeploymentNameFlag(parser)
    flags.AddFingerprintFlag(parser)

  def Run(self, args):
    """Run 'deployments stop'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      If --async=true, returns Operation to poll.
      Else, returns boolean indicating whether stop operation succeeded.

    Raises:
      HttpException: An http error response was received while executing api
          request.
    """
    if args.fingerprint:
      fingerprint = dm_util.DecodeFingerprint(args.fingerprint)
    else:
      # If no fingerprint is present, default to an empty fingerprint.
      # TODO(b/34966984): Remove the empty default after cleaning up all
      # deployments that has no fingerprint
      fingerprint = dm_v2_util.FetchDeploymentFingerprint(
          dm_base.GetClient(),
          dm_base.GetMessages(),
          dm_base.GetProject(),
          args.deployment_name) or ''
    try:
      operation = dm_base.GetClient().deployments.Stop(
          dm_base.GetMessages().DeploymentmanagerDeploymentsStopRequest(
              project=dm_base.GetProject(),
              deployment=args.deployment_name,
              deploymentsStopRequest=(
                  dm_base.GetMessages().DeploymentsStopRequest(
                      fingerprint=fingerprint)
              ),
          )
      )
    except apitools_exceptions.HttpError as error:
      raise exceptions.HttpException(error, dm_v2_util.HTTP_ERROR_FORMAT)
    if args.async:
      return operation
    else:
      op_name = operation.name
      try:
        dm_write.WaitForOperation(op_name,
                                  'stop',
                                  dm_base.GetProject(),
                                  timeout=OPERATION_TIMEOUT)
        log.status.Print('Stop operation ' + op_name
                         + ' completed successfully.')
      except apitools_exceptions.HttpError as error:
        raise exceptions.HttpException(error, dm_v2_util.HTTP_ERROR_FORMAT)
      try:
        # Fetch a list of the stopped resources.
        response = dm_base.GetClient().resources.List(
            dm_base.GetMessages().DeploymentmanagerResourcesListRequest(
                project=dm_base.GetProject(),
                deployment=args.deployment_name,
            )
        )
        # TODO(b/36055861): Pagination
        return response.resources if response.resources else []
      except apitools_exceptions.HttpError as error:
        raise exceptions.HttpException(error, dm_v2_util.HTTP_ERROR_FORMAT)
