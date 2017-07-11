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
"""The `gcloud compute xpn disable` command."""
from googlecloudsdk.api_lib.compute import xpn_api
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute.xpn import flags


class Disable(base.Command):
  """Disable the given project as an XPN host.

  That is, after running this command, one *cannot* enable another project to
  use this project via XPN.
  """

  detailed_help = {
      'EXAMPLES': """
          To disable the project `myproject` as an XPN host, run:

            $ {command} myproject
      """
  }

  @staticmethod
  def Args(parser):
    flags.GetProjectIdArgument('disable as an XPN host').AddToParser(parser)

  def Run(self, args):
    xpn_client = xpn_api.GetXpnClient()
    xpn_client.DisableHost(args.project)
