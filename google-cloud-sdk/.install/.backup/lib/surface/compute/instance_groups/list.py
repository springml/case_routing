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
"""Command for listing instance groups."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import instance_groups_utils
from googlecloudsdk.calliope import base


@base.ReleaseTracks(base.ReleaseTrack.GA)
class List(base_classes.MultiScopeLister):
  """List Google Compute Engine instance groups."""

  SCOPES = (base_classes.ScopeType.regional_scope,
            base_classes.ScopeType.zonal_scope)

  @staticmethod
  def Args(parser):
    base_classes.MultiScopeLister.AddScopeArgs(parser, List.SCOPES)
    # TODO(b/36050942): deprecate --only-managed and --only-unmanaged flags.
    managed_args_group = parser.add_mutually_exclusive_group()
    managed_args_group.add_argument(
        '--only-managed',
        action='store_true',
        help='If provided, a list of managed instance groups will be returned.')
    managed_args_group.add_argument(
        '--only-unmanaged',
        action='store_true',
        help=('If provided, a list of unmanaged instance groups '
              'will be returned.'))

  @property
  def service(self):
    return self.compute.instanceGroups

  @property
  def global_service(self):
    return None

  @property
  def regional_service(self):
    return self.compute.regionInstanceGroups

  @property
  def zonal_service(self):
    return self.compute.instanceGroups

  @property
  def aggregation_service(self):
    return self.compute.instanceGroups

  @property
  def resource_type(self):
    return 'instanceGroups'

  def ComputeDynamicProperties(self, args, items):
    mode = instance_groups_utils.InstanceGroupFilteringMode.ALL_GROUPS
    if args.only_managed:
      mode = (instance_groups_utils.InstanceGroupFilteringMode
              .ONLY_MANAGED_GROUPS)
    elif args.only_unmanaged:
      mode = (instance_groups_utils.InstanceGroupFilteringMode
              .ONLY_UNMANAGED_GROUPS)
    return instance_groups_utils.ComputeInstanceGroupManagerMembership(
        compute=self.compute,
        resources=self.resources,
        http=self.http,
        batch_url=self.batch_url,
        items=items,
        filter_mode=mode)


@base.ReleaseTracks(base.ReleaseTrack.BETA, base.ReleaseTrack.ALPHA)
class ListBetaAlpha(List):
  """List Google Compute Engine managed instance groups."""

  @staticmethod
  def Args(parser):
    base_classes.MultiScopeLister.AddScopeArgs(parser, List.SCOPES)

  def ComputeDynamicProperties(self, args, items):
    return instance_groups_utils.ComputeInstanceGroupManagerMembership(
        compute=self.compute,
        resources=self.resources,
        http=self.http,
        batch_url=self.batch_url,
        items=items,
        filter_mode=instance_groups_utils.InstanceGroupFilteringMode.ALL_GROUPS)


List.detailed_help = base_classes.GetMultiScopeListerHelp(
    'instance groups', List.SCOPES)
ListBetaAlpha.detailed_help = List.detailed_help
