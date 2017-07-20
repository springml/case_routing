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
"""`gcloud iot devices create` command."""
from googlecloudsdk.api_lib.cloudiot import devices
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.iot import flags
from googlecloudsdk.command_lib.iot import util
from googlecloudsdk.core import log


class Create(base.CreateCommand):
  """Create a new device."""

  @staticmethod
  def Args(parser):
    flags.AddRegistryResourceFlags(parser, 'in which to create the device',
                                   positional=False)
    flags.GetIdFlag('device', 'to create').AddToParser(parser)
    for flag in flags.GetDeviceFlags():
      flag.AddToParser(parser)
    flags.AddDeviceCredentialFlagsToParser(parser)

  def Run(self, args):
    client = devices.DevicesClient()

    registry_ref = util.ParseRegistry(args.registry, region=args.region)
    enabled_state = util.ParseEnableDevice(args.enable_device, client=client)
    credentials = util.ParseCredentials(args.public_keys,
                                        messages=client.messages)

    response = client.Create(
        registry_ref, args.id,
        enabled_state=enabled_state,
        credentials=credentials
    )
    log.CreatedResource(args.id, 'device')
    return response
