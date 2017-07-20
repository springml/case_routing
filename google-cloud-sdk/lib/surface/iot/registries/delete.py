# Copyright 2017 Google Inc. All Rights Reserved.
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
"""`gcloud iot registries delete` command."""
from googlecloudsdk.api_lib.cloudiot import registries
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.iot import flags
from googlecloudsdk.command_lib.iot import util
from googlecloudsdk.core import log


class Delete(base.DeleteCommand):
  """Delete a device registry."""

  @staticmethod
  def Args(parser):
    flags.AddRegistryResourceFlags(parser, 'to delete')

  def Run(self, args):
    client = registries.RegistriesClient()
    registry_ref = util.ParseRegistry(args.id, region=args.region)
    response = client.Delete(registry_ref)
    log.DeletedResource(registry_ref.Name(), 'registry')
    return response
