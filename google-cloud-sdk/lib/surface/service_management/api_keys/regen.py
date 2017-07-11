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

"""Implementation of the service-management api-keys regen command."""

from googlecloudsdk.api_lib.service_management import services_util
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.service_management import common_flags
from googlecloudsdk.core import properties


class Regen(base.Command):
  """Regenerates the keystring for the specified API key.

     After regenerating the keystring for the API key, the old keystring is
     stored in the 'previous_key' field. You can switch back to using the
     previous_key by calling the revert command.
  """

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    common_flags.key_flag(suffix='to regenerate').AddToParser(parser)

  def Run(self, args):
    """Run 'service-management api-keys regen'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      The response from the keys API call.
    """
    messages = services_util.GetApiKeysMessagesModule()
    client = services_util.GetApiKeysClientInstance()

    # Construct the Regenerate API Key request object
    request = messages.ApikeysProjectsApiKeysRegenerateRequest(
        projectId=properties.VALUES.core.project.Get(required=True),
        keyId=args.key)

    return client.projects_apiKeys.Regenerate(request)
