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
"""Command for listing unmanaged instance groups."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import instance_groups_utils


class List(base_classes.ZonalLister):
  """List Google Compute Engine unmanaged instance groups."""

  @staticmethod
  def Args(parser):
    base_classes.ZonalLister.Args(parser)
    parser.display_info.AddFormat("""
          table(
            name,
            zone.basename(),
            network.basename(),
            network.segment(-4):label=NETWORK_PROJECT,
            isManaged:label=MANAGED,
            size:label=INSTANCES
          )
    """)

  def GetResources(self, args, errors):
    resources = super(List, self).GetResources(args, errors)
    return (resource for resource in resources if resource.zone)

  def ComputeDynamicProperties(self, args, items):
    mode = (
        instance_groups_utils.InstanceGroupFilteringMode.ONLY_UNMANAGED_GROUPS)
    return instance_groups_utils.ComputeInstanceGroupManagerMembership(
        compute=self.compute,
        resources=self.resources,
        http=self.http,
        batch_url=self.batch_url,
        items=items,
        filter_mode=mode)

  def Collection(self):
    """Override the default collection from the base class."""
    return None

  @property
  def service(self):
    return self.compute.instanceGroups

  @property
  def resource_type(self):
    return 'instanceGroups'


List.detailed_help = base_classes.GetZonalListerHelp('unmanaged '
                                                     'instance groups')
