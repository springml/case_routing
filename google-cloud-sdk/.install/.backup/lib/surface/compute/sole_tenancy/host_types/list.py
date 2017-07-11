# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Command for listing sole-tenancy host types."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import base


@base.Hidden
class List(base_classes.ZonalLister):
  """List Google Compute Engine sole-tenancy host types."""

  @property
  def service(self):
    return self.compute.hostTypes

  @property
  def resource_type(self):
    return 'hostTypes'


List.detailed_help = base_classes.GetZonalListerHelp('hostTypes')
