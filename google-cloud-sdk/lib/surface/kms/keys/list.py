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
"""List the keys within a keyring."""

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.cloudkms import base as cloudkms_base
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.kms import flags
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


class List(base.ListCommand):
  """List the keys within a keyring.

  Lists all keys within the given keyring.

  ## EXAMPLES

  The following command lists all keys within the
  keyring `fellowship` and location `global`:

    $ {command} --keyring fellowship --location global
  """

  @staticmethod
  def Args(parser):
    # The format of a CryptoKeyVersion name is:
    # 'projects/*/locations/*/keyRings/*/cryptoKeys/*/cryptoKeyVersions/*'
    # The CryptoKeyVersionId is captured by segment(9).
    parser.display_info.AddFormat("""
        table(
          name,
          purpose,
          primary.name.segment(9):label=PRIMARY_ID,
          primary.state:label=PRIMARY_STATE)
    """)

  def Run(self, args):
    client = cloudkms_base.GetClientInstance()
    messages = cloudkms_base.GetMessagesModule()

    key_ring_ref = resources.REGISTRY.Create(
        flags.KEY_RING_COLLECTION,
        keyRingsId=args.MakeGetOrRaise('--keyring'),
        locationsId=args.MakeGetOrRaise('--location'),
        projectsId=properties.VALUES.core.project.GetOrFail)

    request = messages.CloudkmsProjectsLocationsKeyRingsCryptoKeysListRequest(
        parent=key_ring_ref.RelativeName())

    return list_pager.YieldFromList(
        client.projects_locations_keyRings_cryptoKeys,
        request,
        field='cryptoKeys',
        limit=args.limit,
        batch_size_attribute='pageSize')
