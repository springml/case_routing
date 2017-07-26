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
"""`gcloud iot registries create` command."""
from googlecloudsdk.api_lib.cloudiot import registries
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.iot import flags
from googlecloudsdk.command_lib.iot import util
from googlecloudsdk.core import log


class Create(base.CreateCommand):
  """Create a new device registry."""

  @staticmethod
  def Args(parser):
    noun = 'device registry'
    flags.GetIdFlag(noun, 'to create', 'REGISTRY_ID').AddToParser(parser)
    flags.GetRegionFlag(noun).AddToParser(parser)
    for flag in flags.GetDeviceRegistrySettingsFlags():
      flag.AddToParser(parser)

  def Run(self, args):
    client = registries.RegistriesClient()

    location_ref = util.ParseLocation(region=args.region)
    mqtt_state = util.ParseEnableMqttConfig(args.enable_mqtt_config,
                                            client=client)
    pubsub_topic_ref = util.ParsePubsubTopic(args.pubsub_topic)

    response = client.Create(
        location_ref, args.id,
        pubsub_topic=pubsub_topic_ref,
        mqtt_config_state=mqtt_state)
    log.CreatedResource(args.id, 'registry')
    return response
