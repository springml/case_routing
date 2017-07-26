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

"""Command for listing backend services."""

from googlecloudsdk.api_lib.compute import base_classes


class List(base_classes.GlobalRegionalLister):
  """List backend services."""

  def Collection(self):
    return 'compute.backendServices.alpha'

  @property
  def aggregation_service(self):
    return self.compute.backendServices

  @property
  def global_service(self):
    return self.compute.backendServices

  @property
  def regional_service(self):
    return self.compute.regionBackendServices

  @property
  def resource_type(self):
    return 'backendServices'

  @property
  def allowed_filtering_types(self):
    return ['regionBackendServices', 'backendServices']


List.detailed_help = base_classes.GetGlobalRegionalListerHelp(
    'backend services')
