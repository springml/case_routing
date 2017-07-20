# Copyright 2015 Google Inc. All Rights Reserved.
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
"""Command for adding public keys to users."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import file_utils
from googlecloudsdk.api_lib.compute import request_helper
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute.users import utils as user_utils
from googlecloudsdk.command_lib.util import gaia
from googlecloudsdk.command_lib.util import time_util
from googlecloudsdk.core import properties


class AddKeys(base.SilentCommand):
  """Add public keys to a Google Compute Engine user.

  *{command}* adds public keys to a Google Compute Engine user.
  """

  @staticmethod
  def Args(parser):
    user_utils.AddUserArgument(parser, '', custom_help=(
        'If provided, the name of the user to add a public key to. '
        'Else, the default user will be used.'))

    parser.add_argument(
        '--public-key-files',
        required=True,
        type=arg_parsers.ArgList(min_length=1),
        metavar='LOCAL_FILE_PATH',
        help='The path to a public-key file.')

    parser.add_argument(
        '--description',
        help='A description of the public keys')

    parser.add_argument(
        '--expire',
        type=arg_parsers.Duration(),
        help="""\
        Public keys can be configured to expire after a specified amount
        of time. For example, specifying ``12h'' will cause the key to expire
        after 12 hours. Valid units for this flag are ``s'' for seconds, ``m''
        for minutes, ``h'' for hours, and ''d'' for days.
        """)

  def Run(self, args):
    holder = base_classes.ComputeUserAccountsApiHolder(self.ReleaseTrack())
    client = holder.client

    name = args.name
    if not name:
      name = gaia.GetDefaultAccountName(client.http)

    user_ref = holder.resources.Parse(
        name,
        params={'project': properties.VALUES.core.project.GetOrFail},
        collection='clouduseraccounts.users')

    valid_key_types = [
        'ssh-rsa', 'ssh-dss', 'ecdsa-sha2-nistp256', 'ssh-ed25519']

    public_keys = []
    for key_file in args.public_key_files:
      key_text = file_utils.ReadFile(key_file, 'public-key')

      if key_text.split(' ', 1)[0] not in valid_key_types:
        raise exceptions.ToolException(
            'You must specify a public key file that contains a key of a '
            'supported form. Supported forms are {0}.'
            .format(', '.join(valid_key_types))
        )
      public_keys.append(key_text)

    formatted_expiration = time_util.CalculateExpiration(args.expire)

    requests = []
    for key in public_keys:
      public_key_message = client.MESSAGES_MODULE.PublicKey(
          description=args.description,
          expirationTimestamp=formatted_expiration,
          key=key)

      request = (
          client.MESSAGES_MODULE.ClouduseraccountsUsersAddPublicKeyRequest(
              project=user_ref.project,
              publicKey=public_key_message,
              user=user_ref.Name()))
      requests.append((client.users, 'AddPublicKey', request))

    errors = []
    responses = list(request_helper.MakeRequests(
        requests=requests,
        http=client.http,
        batch_url='https://www.googleapis.com/batch/',
        errors=errors))
    if errors:
      utils.RaiseToolException(
          errors, error_message='Could not fetch resource:')
    return responses

AddKeys.detailed_help = {
    'EXAMPLES': """\
        To add a public key to a user, run:

          $ {command} example-user --public-key-files ~/.ssh/pubkey.pub

        Multiple public keys can be specified by providing multiple paths
        to key files on the local machine.
        """,
}
