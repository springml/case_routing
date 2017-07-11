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
"""The `gcloud compute xpn associated-projects add` command."""
from googlecloudsdk.api_lib.compute import xpn_api
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute.xpn import flags


class Add(base.Command):
  """Associate the given project with a given host project via XPN."""

  detailed_help = {
      'EXAMPLES': """
          To enable the project `xpn-user` to use the project `xpn-host` via
          XPN, run:

            $ {command} --host-project=xpn-host xpn-user
      """
  }

  @staticmethod
  def Args(parser):
    flags.GetProjectIdArgument('add to the host project').AddToParser(parser)
    flags.GetHostProjectFlag('add an associated project to').AddToParser(parser)

  def Run(self, args):
    xpn_client = xpn_api.GetXpnClient()
    xpn_client.EnableXpnAssociatedProject(args.host_project, args.project)
