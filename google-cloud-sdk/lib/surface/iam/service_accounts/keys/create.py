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
"""Command to create private keys for service accounts."""


import textwrap

from googlecloudsdk.command_lib.iam import base_classes
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.core import log


class Create(base_classes.BaseIamCommand):
  """Create a private key for a service account."""

  detailed_help = {
      'NOTES': textwrap.dedent("""\
          The option --key-file-type=p12 is available here only for legacy
          reasons; all new use cases are encouraged to use the default 'json'
          format.
          """),
      'EXAMPLES': textwrap.dedent("""\
          To create a new private key for a service account, and save a copy
          of it locally, run:

            $ {command} --iam-account my-iam-account@somedomain.com key.json
          """),
  }

  @staticmethod
  def Args(parser):
    parser.add_argument('--key-file-type',
                        choices=['json', 'p12'],
                        default='json',
                        help='The type of key to create.')

    parser.add_argument('--iam-account',
                        required=True,
                        type=iam_util.GetIamAccountFormatValidator(),
                        help='The service account for which to create a key.')

    parser.add_argument('output',
                        metavar='OUTPUT-FILE',
                        help='The path where the resulting private key should '
                        'be written.')

  def Run(self, args):
    result = self.iam_client.projects_serviceAccounts_keys.Create(
        self.messages.IamProjectsServiceAccountsKeysCreateRequest(
            name=iam_util.EmailToAccountResourceName(args.iam_account),
            createServiceAccountKeyRequest=
            self.messages.CreateServiceAccountKeyRequest(
                privateKeyType=iam_util.KeyTypeToCreateKeyType(
                    iam_util.KeyTypeFromString(args.key_file_type)))))

    # Only the creating user has access. Set file permission to "-rw-------".
    self.WriteFile(args.output, result.privateKeyData, make_private=True)
    log.status.Print(
        'created key [{0}] of type [{1}] as [{2}] for [{3}]'.format(
            iam_util.GetKeyIdFromResourceName(result.name),
            iam_util.KeyTypeToString(result.privateKeyType),
            args.output,
            args.iam_account))
