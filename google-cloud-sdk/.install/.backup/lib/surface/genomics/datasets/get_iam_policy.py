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

"""Implementation of gcloud genomics datasets get-iam-policy.
"""

from googlecloudsdk.api_lib.genomics import genomics_util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import resources


class GetIamPolicy(base.ListCommand):
  """Get IAM policy for a dataset.

  This command gets the IAM policy for a dataset, given a dataset ID.
  """

  @staticmethod
  def Args(parser):
    parser.add_argument('id', type=str,
                        help='The ID of the dataset.')
    base.URI_FLAG.RemoveFromParser(parser)

  def Run(self, args):
    apitools_client = genomics_util.GetGenomicsClient()
    messages = genomics_util.GetGenomicsMessages()

    dataset_resource = resources.REGISTRY.Parse(
        args.id, collection='genomics.datasets')

    policy_request = messages.GenomicsDatasetsGetIamPolicyRequest(
        resource='datasets/{0}'.format(dataset_resource.Name()),
        getIamPolicyRequest=messages.GetIamPolicyRequest(),
    )
    return apitools_client.datasets.GetIamPolicy(policy_request)
