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
"""The `gcloud compute xpn get-host-project` command."""
from googlecloudsdk.api_lib.compute import xpn_api
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute.xpn import flags


class GetHostProject(base.Command):
  """Get the XPN host project that the given project is linked to.

  Get the shared VPC network (XPN) host project of this project, whose
  networks can be accessed from this one via XPN.
  """

  detailed_help = {
      'EXAMPLES': """
          If the project `xpn-user` can use the project `xpn-host` via XPN,

            $ {command} xpn-user

          will show the `xpn-host` project.
      """
  }

  @staticmethod
  def Args(parser):
    flags.GetProjectIdArgument('get the host project for').AddToParser(parser)

  def Run(self, args):
    xpn_client = xpn_api.GetXpnClient()
    return xpn_client.GetHostProject(args.project)
