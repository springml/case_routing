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
"""Command for listing instances in instance groups."""
from googlecloudsdk.api_lib.compute import instance_groups_utils
from googlecloudsdk.command_lib.compute import flags
from googlecloudsdk.command_lib.compute import scope as compute_scope
from googlecloudsdk.command_lib.compute.instance_groups import flags as instance_groups_flags


class ListInstances(instance_groups_utils.InstanceGroupListInstancesBase):
  """List Google Compute Engine instances present in instance group."""

  @staticmethod
  def Args(parser):
    instance_groups_flags.MULTISCOPE_INSTANCE_GROUP_ARG.AddArgument(parser)
    flags.AddRegexArg(parser)

  def GetResources(self, args):
    """Retrieves response with instance in the instance group."""
    group_ref = (
        instance_groups_flags.MULTISCOPE_INSTANCE_GROUP_ARG.ResolveAsResource(
            args, self.resources,
            default_scope=compute_scope.ScopeEnum.ZONE,
            scope_lister=flags.GetDefaultScopeLister(self.compute_client)))

    if args.regexp:
      # Regexp interprested as RE2 by Instance Group API
      filter_expr = 'instance eq {0}'.format(args.regexp)
    else:
      filter_expr = None

    if group_ref.Collection() == 'compute.instanceGroups':
      service = self.compute.instanceGroups
      request = service.GetRequestType(self.method)(
          instanceGroup=group_ref.Name(),
          instanceGroupsListInstancesRequest=(
              self.messages.InstanceGroupsListInstancesRequest()),
          zone=group_ref.zone,
          filter=filter_expr,
          project=group_ref.project)
    else:
      service = self.compute.regionInstanceGroups
      request = service.GetRequestType(self.method)(
          instanceGroup=group_ref.Name(),
          regionInstanceGroupsListInstancesRequest=(
              self.messages.RegionInstanceGroupsListInstancesRequest()),
          region=group_ref.region,
          filter=filter_expr,
          project=group_ref.project)

    errors = []
    results = self.compute_client.MakeRequests(
        requests=[(service, self.method, request)],
        errors_to_collect=errors)

    return results, errors

  def DeprecatedFormat(self, unused_args):
    return """table(instance.basename():label=NAME,
                    instance.scope().segment(0):label=ZONE,
                    status)"""
