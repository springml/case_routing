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

"""Package for the service-management/versions CLI subcommands."""

from googlecloudsdk.calliope import base


# NOTE: These are deprecated, so not included in the GA release track
#       Users should use the functionally identical configs subcommand group.
@base.ReleaseTracks(base.ReleaseTrack.BETA)
@base.Hidden
class Versions(base.Group):
  """Manage versions for various services.

  DEPRECATED: This command group is deprecated and will be removed.
  Use 'gcloud beta service-management configs' instead.
  """
