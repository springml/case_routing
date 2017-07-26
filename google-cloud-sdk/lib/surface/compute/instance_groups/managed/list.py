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
"""Command for listing managed instance groups."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.core import log


class List(base_classes.InstanceGroupManagerDynamicProperiesMixin,
           base_classes.MultiScopeLister):
  """List Google Compute Engine managed instance groups."""

  SCOPES = [base_classes.ScopeType.regional_scope,
            base_classes.ScopeType.zonal_scope]

  @staticmethod
  def Args(parser):
    base_classes.MultiScopeLister.AddScopeArgs(parser, List.SCOPES)

  @property
  def global_service(self):
    return None

  @property
  def regional_service(self):
    return self.compute.regionInstanceGroupManagers

  @property
  def zonal_service(self):
    return self.compute.instanceGroupManagers

  @property
  def aggregation_service(self):
    return self.compute.instanceGroupManagers

  @property
  def resource_type(self):
    return 'instanceGroupManagers'

  def GetResources(self, args, errors):
    # GetResources() may set _had_errors True if it encounters errors that don't
    # stop processing. If True then Epilog() below emits one error message.
    self._had_errors = False
    return super(List, self).GetResources(args, errors)

  def Epilog(self, unused_resources_were_displayed):
    if self._had_errors:
      log.err.Print('(*) - there are errors in your autoscaling setup, please '
                    'describe the resource to see details')


List.detailed_help = base_classes.GetMultiScopeListerHelp(
    'managed instance groups', List.SCOPES)
