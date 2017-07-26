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
"""The `gcloud compute xpn associated-projects list` command."""
from googlecloudsdk.api_lib.compute import xpn_api
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute.xpn import flags
from googlecloudsdk.command_lib.compute.xpn import util as command_lib_util


class List(base.ListCommand):
  """List the projects that can use the given project via XPN."""

  detailed_help = {
      'EXAMPLES': """
          If the project `xpn-user` can use the project `xpn-host` via XPN, the
          command

            $ {command} xpn-host

          yields the output

            RESOURCE_ID  RESOURCE_TYPE
            xpn-user     PROJECT
      """
  }

  @staticmethod
  def Args(parser):
    flags.GetProjectIdArgument(
        'get associated projects for').AddToParser(parser)
    parser.display_info.AddFormat(command_lib_util.XPN_RESOURCE_ID_FORMAT)

  def Run(self, args):
    xpn_client = xpn_api.GetXpnClient()
    xpn_types = xpn_client.messages.XpnResourceId.TypeValueValuesEnum
    resources = xpn_client.ListEnabledResources(args.project)
    return [resource for resource in resources if
            resource.type == xpn_types.PROJECT]
