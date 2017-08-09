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
"""`gcloud iot configs describe` command."""
from googlecloudsdk.api_lib.cloudiot import devices
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.iot import flags
from googlecloudsdk.command_lib.iot import util
from googlecloudsdk.core import log


class GetValue(base.Command):
  """Show the binary data of a device's latest configuration."""

  @staticmethod
  def Args(parser):
    parser.display_info.AddFormat('none')
    flags.AddDeviceResourceFlags(parser,
                                 'for the configuration to get the value of',
                                 positional=False)

  def Run(self, args):
    client = devices.DevicesClient()

    device_ref = util.ParseDevice(
        args.device, registry=args.registry, region=args.region)

    device = client.Get(device_ref)
    try:
      data = device.config.data.binaryData
    except AttributeError:
      # This shouldn't happen, as the API puts in a config for each device.
      raise util.BadDeviceError(
          'Device [{}] is missing configuration data.'.format(
              device_ref.Name()))
    # Don't use --format=value(.) because we don't want the \n at the end.
    log.out.write(data)
    return data
