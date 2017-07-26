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
"""Command to get IAM policy for a resource."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute import flags as compute_flags
from googlecloudsdk.command_lib.compute.instances import flags


@base.Hidden
@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class GetIamPolicy(base.ListCommand):
  """Get the IAM Policy for a Google Compute Engine instance.

  *{command}* displays the Iam Policy associated with a Google Compute Engine
  instance in a project.
  """

  @staticmethod
  def Args(parser):
    flags.INSTANCE_ARG.AddArgument(
        parser, operation_type='describe the IAM Policy of')
    base.URI_FLAG.RemoveFromParser(parser)

  def Run(self, args):
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    client = holder.client

    instance_ref = flags.INSTANCE_ARG.ResolveAsResource(
        args,
        holder.resources,
        scope_lister=compute_flags.GetDefaultScopeLister(client))

    # TODO(b/36051087): determine how this output should look when empty.

    # GetIamPolicy always returns either an error or a valid policy.
    # If no policy has been set it returns a valid empty policy (just an etag.)
    # It is not possible to have multiple policies for one resource.
    return client.MakeRequests(
        [(client.apitools_client.instances, 'GetIamPolicy',
          client.messages.ComputeInstancesGetIamPolicyRequest(
              resource=instance_ref.instance,
              zone=instance_ref.zone,
              project=instance_ref.project))])[0]
