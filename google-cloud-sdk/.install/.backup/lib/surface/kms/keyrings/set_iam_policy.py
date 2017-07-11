# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Set the IAM policy for a keyring."""

from googlecloudsdk.api_lib.cloudkms import base as cloudkms_base
from googlecloudsdk.api_lib.cloudkms import iam
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.command_lib.kms import flags


class SetIamPolicy(base.Command):
  """Set the IAM policy for a keyring.

  Sets the IAM policy for the given keyring as defined in a JSON file.

  See https://cloud.google.com/iam/docs/managing-policies for details of
  the policy file format and contents.

  ## EXAMPLES
  The following command will read am IAM policy defined in a JSON file
  'policy.json' and set it for the keyring `fellowship` with location `global`:

    $ {command} fellowship policy.json --location global
  """

  @staticmethod
  def Args(parser):
    flags.AddKeyRingArgument(parser, 'whose IAM policy to update')
    parser.add_argument('policy_file', help='JSON file with the IAM policy')

  def Run(self, args):
    messages = cloudkms_base.GetMessagesModule()

    policy = iam_util.ParseJsonPolicyFile(args.policy_file, messages.Policy)
    update_mask = iam_util.ConstructUpdateMaskFromPolicy(args.policy_file)

    keyring_ref = flags.ParseKeyRingName(args)
    result = iam.SetKeyRingIamPolicy(keyring_ref, policy, update_mask)
    iam_util.LogSetIamPolicy(keyring_ref.Name(), 'keyring')
    return result
