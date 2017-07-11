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
"""Command to list all registries in a project and location."""
from googlecloudsdk.api_lib.cloudiot import registries
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.iot import flags
from googlecloudsdk.command_lib.iot import util


_FORMAT = """\
table(
    name.scope("registries"):label=ID,
    name.scope("locations").segment(0):label=LOCATION,
    mqttConfig.mqttConfigState:label=MQTT_ENABLED
)
"""


class List(base.ListCommand):
  """List device registries."""

  @staticmethod
  def Args(parser):
    parser.display_info.AddFormat(_FORMAT)
    parser.display_info.AddUriFunc(util.RegistriesUriFunc)
    flags.GetRegionFlag('device registries').AddToParser(parser)

  def Run(self, args):
    """Run the list command."""
    client = registries.RegistriesClient()

    location_ref = util.ParseLocation(args.region)

    return client.List(location_ref, args.limit, args.page_size)
