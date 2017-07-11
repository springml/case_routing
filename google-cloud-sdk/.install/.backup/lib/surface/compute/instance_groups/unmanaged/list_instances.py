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
"""managed-instance-groups list-instances command.

It's an alias for the instance-groups list-instances command.
"""
from googlecloudsdk.api_lib.compute import instance_groups_utils
from googlecloudsdk.api_lib.compute import request_helper
from googlecloudsdk.command_lib.compute import flags
from googlecloudsdk.command_lib.compute.instance_groups import flags as instance_groups_flags
from googlecloudsdk.core import properties


class ListInstances(instance_groups_utils.InstanceGroupListInstancesBase):

  @staticmethod
  def Args(parser):
    ListInstances.ZonalInstanceGroupArg = (
        instance_groups_flags.MakeZonalInstanceGroupArg())
    ListInstances.ZonalInstanceGroupArg.AddArgument(parser)
    flags.AddRegexArg(parser)

  def GetResources(self, args):
    """Retrieves response with instance in the instance group."""
    # Note: only zonal resources parsed here.
    group_ref = self.resources.Parse(
        args.name,
        params={
            'project': properties.VALUES.core.project.GetOrFail,
            'zone': args.zone
        },
        collection='compute.' + self.resource_type)
    if args.regexp:
      filter_expr = 'instance eq {0}'.format(args.regexp)
    else:
      filter_expr = None

    request = self.service.GetRequestType(self.method)(
        instanceGroup=group_ref.Name(),
        instanceGroupsListInstancesRequest=(
            self.messages.InstanceGroupsListInstancesRequest()),
        zone=group_ref.zone,
        filter=filter_expr,
        project=group_ref.project)

    errors = []
    results = list(request_helper.MakeRequests(
        requests=[(self.service, self.method, request)],
        http=self.http,
        batch_url=self.batch_url,
        errors=errors))

    return results, errors
