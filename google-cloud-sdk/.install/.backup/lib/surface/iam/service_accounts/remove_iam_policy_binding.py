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
"""Command for removing IAM policies for service accounts."""

import httplib

from googlecloudsdk.api_lib.util import http_retry
from googlecloudsdk.command_lib.iam import base_classes
from googlecloudsdk.command_lib.iam import iam_util


class RemoveIamPolicyBinding(base_classes.BaseIamCommand):
  """Remove an IAM policy binding from a service account.

  This command removes a policy binding to the IAM policy of a service account,
  given an IAM_ACCOUNT and the binding.
  """

  detailed_help = iam_util.GetDetailedHelpForRemoveIamPolicyBinding(
      'service account', 'my-iam-account@somedomain.com')

  @staticmethod
  def Args(parser):
    iam_util.AddServiceAccountNameArg(
        parser,
        action='to remove the policy binding from')
    iam_util.AddArgsForRemoveIamPolicyBinding(parser)

  @http_retry.RetryOnHttpStatus(httplib.CONFLICT)
  def Run(self, args):
    policy = self.iam_client.projects_serviceAccounts.GetIamPolicy(
        self.messages.IamProjectsServiceAccountsGetIamPolicyRequest(
            resource=iam_util.EmailToAccountResourceName(args.service_account)))

    iam_util.RemoveBindingFromIamPolicy(policy, args.member, args.role)

    return self.iam_client.projects_serviceAccounts.SetIamPolicy(
        self.messages.IamProjectsServiceAccountsSetIamPolicyRequest(
            resource=iam_util.EmailToAccountResourceName(args.service_account),
            setIamPolicyRequest=self.messages.SetIamPolicyRequest(
                policy=policy)))
