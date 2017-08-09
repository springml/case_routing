# Copyright 2014 Google Inc. All Rights Reserved.
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
"""Command for describing instances."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute.instances import flags


class Describe(base.DescribeCommand):
  """Describe a virtual machine instance.

  *{command}* displays all data associated with a Google Compute
  Engine virtual machine instance.
  """

  @staticmethod
  def Args(parser):
    flags.INSTANCE_ARG.AddArgument(parser, operation_type='describe')

  def Run(self, args):
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    client = holder.client

    instance_ref = flags.INSTANCE_ARG.ResolveAsResource(
        args,
        holder.resources,
        scope_lister=flags.GetInstanceZoneScopeLister(client))

    request = client.messages.ComputeInstancesGetRequest(
        **instance_ref.AsDict())

    return client.MakeRequests([(client.apitools_client.instances, 'Get',
                                 request)])[0]
