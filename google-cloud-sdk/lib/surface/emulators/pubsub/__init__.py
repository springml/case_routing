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
"""The gcloud pubsub emulator group."""

from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.emulators import pubsub_util
from googlecloudsdk.command_lib.emulators import util
from googlecloudsdk.command_lib.util import java


@base.ReleaseTracks(base.ReleaseTrack.ALPHA, base.ReleaseTrack.BETA)
class PubSub(base.Group):
  """Manage your local pubsub emulator.

  This set of commands allows you to start and use a local pubsub emulator.
  """

  detailed_help = {
      'EXAMPLES': """\
          To start a local pubsub emulator, run:

            $ {command} start
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--data-dir',
        required=False,
        help='The directory to be used to store/retrieve data/config for an'
        ' emulator run.')

  # Override
  def Filter(self, context, args):
    java.CheckIfJavaIsInstalled(pubsub_util.PUBSUB_TITLE)
    util.EnsureComponentIsInstalled('pubsub-emulator', pubsub_util.PUBSUB_TITLE)

    if not args.data_dir:
      args.data_dir = pubsub_util.GetDataDir()
