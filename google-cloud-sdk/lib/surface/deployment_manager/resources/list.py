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

"""resources list command."""

from apitools.base.py import list_pager

from googlecloudsdk.api_lib.deployment_manager import dm_api_util
from googlecloudsdk.api_lib.deployment_manager import dm_base
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.deployment_manager import dm_v2_base


class List(base.ListCommand):
  """List resources in a deployment.

  Prints a table with summary information on all resources in the deployment.
  """

  detailed_help = {
      'EXAMPLES': """\
          To print out a list of resources in the deployment with some summary information about each, run:

            $ {command} --deployment my-deployment

          To print only the name of each resource, run:

            $ {command} --deployment my-deployment --simple-list
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
    dm_api_util.SIMPLE_LIST_FLAG.AddToParser(parser)
    parser.display_info.AddFormat("""
          table(
            name,
            type,
            update.state.yesno(no="COMPLETED"),
            update.error.errors.group(code),
            update.intent
          )
    """)

  def Run(self, args):
    """Run 'resources list'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      The list of resources for the specified deployment.

    Raises:
      HttpException: An http error response was received while executing api
          request.
    """
    request = dm_v2_base.GetMessages().DeploymentmanagerResourcesListRequest(
        project=dm_base.GetProject(),
        deployment=args.deployment,
    )
    return dm_api_util.YieldWithHttpExceptions(
        list_pager.YieldFromList(dm_v2_base.GetClient().resources,
                                 request,
                                 field='resources',
                                 limit=args.limit,
                                 batch_size=args.page_size))
