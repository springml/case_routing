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
"""Commands for updating backend buckets."""

from apitools.base.py import encoding

from googlecloudsdk.api_lib.compute import backend_buckets_utils
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute.backend_buckets import flags as backend_buckets_flags
from googlecloudsdk.core import log


class Update(base.UpdateCommand):
  """Update a backend bucket.

  *{command}* is used to update backend buckets.
  """

  BACKEND_BUCKET_ARG = None

  @staticmethod
  def Args(parser):
    backend_buckets_utils.AddUpdatableArgs(Update, parser, 'update')
    backend_buckets_flags.GCS_BUCKET_ARG.AddArgument(parser)

  def GetGetRequest(self, client, backend_bucket_ref):
    return (
        client.apitools_client.backendBuckets,
        'Get',
        client.messages.ComputeBackendBucketsGetRequest(
            project=backend_bucket_ref.project,
            backendBucket=backend_bucket_ref.Name()))

  def GetSetRequest(self, client, backend_bucket_ref, replacement):
    return (
        client.apitools_client.backendBuckets,
        'Update',
        client.messages.ComputeBackendBucketsUpdateRequest(
            project=backend_bucket_ref.project,
            backendBucket=backend_bucket_ref.Name(),
            backendBucketResource=replacement))

  def Modify(self, args, existing):
    replacement = encoding.CopyProtoMessage(existing)

    if args.description:
      replacement.description = args.description
    elif args.description == '':  # pylint: disable=g-explicit-bool-comparison
      replacement.description = None

    if args.gcs_bucket_name:
      replacement.bucketName = args.gcs_bucket_name

    if args.enable_cdn is not None:
      replacement.enableCdn = args.enable_cdn

    return replacement

  def Run(self, args):
    if not any([
        args.description is not None,
        args.gcs_bucket_name is not None,
        args.enable_cdn is not None,
    ]):
      raise exceptions.ToolException('At least one property must be modified.')

    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    client = holder.client

    backend_bucket_ref = Update.BACKEND_BUCKET_ARG.ResolveAsResource(
        args, holder.resources)
    get_request = self.GetGetRequest(client, backend_bucket_ref)

    objects = client.MakeRequests([get_request])

    new_object = self.Modify(args, objects[0])

    # If existing object is equal to the proposed object or if
    # Modify() returns None, then there is no work to be done, so we
    # print the resource and return.
    if objects[0] == new_object:
      log.status.Print(
          'No change requested; skipping update for [{0}].'.format(
              objects[0].name))
      return objects

    return client.MakeRequests(
        [self.GetSetRequest(client, backend_bucket_ref, new_object)])
