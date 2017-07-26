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
"""Command for updating service accounts."""

import httplib

from googlecloudsdk.api_lib.util import http_retry
from googlecloudsdk.command_lib.iam import base_classes
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.core import log


class Update(base_classes.BaseIamCommand):
  """Update the metadata of an IAM service account."""

  @staticmethod
  def Args(parser):
    parser.add_argument('--display-name',
                        help='The new textual name to display for the account.')

    iam_util.AddServiceAccountNameArg(
        parser, action='to update')

  @http_retry.RetryOnHttpStatus(httplib.CONFLICT)
  def Run(self, args):
    resource_name = iam_util.EmailToAccountResourceName(args.service_account)
    current = self.iam_client.projects_serviceAccounts.Get(
        self.messages.IamProjectsServiceAccountsGetRequest(name=resource_name))

    result = self.iam_client.projects_serviceAccounts.Update(
        self.messages.ServiceAccount(
            name=resource_name,
            etag=current.etag,
            displayName=args.display_name))
    log.UpdatedResource(args.service_account, kind='service account')
    return result
