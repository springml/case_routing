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
"""Command for setting IAM policies for registries."""

from googlecloudsdk.api_lib.cloudiot import registries
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.iam import base_classes
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.command_lib.iot import flags
from googlecloudsdk.command_lib.iot import util
from googlecloudsdk.core import log


class SetIamPolicy(base_classes.BaseIamCommand):
  """Set the IAM policy for a device registry.

  This command replaces the existing IAM policy for a device registry, given
  a REGISTRY and a file encoded in JSON or YAML that contains the IAM
  policy. If the given policy file specifies an "etag" value, then the
  replacement will succeed only if the policy already in place matches that
  etag. (An etag obtained via $ gcloud iot registries get-iam-policy will
  prevent the replacement if the policy for the device registry has been
  subsequently updated.) A policy file that does not contain an etag value will
  replace any existing policy for the device registry.
  """

  detailed_help = iam_util.GetDetailedHelpForSetIamPolicy(
      'device registry', 'my-registry', additional_flags='--region us-central1')

  @staticmethod
  def Args(parser):
    flags.AddRegistryResourceFlags(parser, 'for which to set IAM policy')
    flags.GetIamPolicyFileFlag().AddToParser(parser)

  def Run(self, args):
    client = registries.RegistriesClient()
    messages = apis.GetMessagesModule('cloudiot', 'v1beta1')

    policy = iam_util.ParsePolicyFile(args.policy_file, messages.Policy)
    registry_ref = util.ParseRegistry(args.id, region=args.region)

    response = client.SetIamPolicy(
        registry_ref,
        set_iam_policy_request=messages.SetIamPolicyRequest(policy=policy))
    log.status.Print(
        'Set IAM policy for registry [{}].'.format(registry_ref.Name()))
    return response
