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
"""Command for creating backend buckets."""

from googlecloudsdk.api_lib.compute import backend_buckets_utils
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute.backend_buckets import flags as backend_buckets_flags


class Create(base.CreateCommand):
  """Create a backend bucket.

  *{command}* is used to create backend buckets. Backend buckets
  define a Google Cloud Storage bucket that can serve content. URL
  maps define which requests are sent to which backend buckets.
  """

  BACKEND_BUCKET_ARG = None

  @staticmethod
  def Args(parser):
    parser.display_info.AddFormat(backend_buckets_flags.DEFAULT_LIST_FORMAT)
    backend_buckets_utils.AddUpdatableArgs(Create, parser, 'create')
    backend_buckets_flags.REQUIRED_GCS_BUCKET_ARG.AddArgument(parser)

  def Run(self, args):
    """Issues the request necessary for creating a backend bucket."""
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    client = holder.client

    backend_buckets_ref = Create.BACKEND_BUCKET_ARG.ResolveAsResource(
        args, holder.resources)

    enable_cdn = args.enable_cdn or False

    request = client.messages.ComputeBackendBucketsInsertRequest(
        backendBucket=client.messages.BackendBucket(
            description=args.description,
            name=backend_buckets_ref.Name(),
            bucketName=args.gcs_bucket_name,
            enableCdn=enable_cdn),
        project=backend_buckets_ref.project)

    return client.MakeRequests([(client.apitools_client.backendBuckets,
                                 'Insert', request)])
