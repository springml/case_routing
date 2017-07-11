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
"""gcloud pubsub emulator env_init command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.emulators import util


@base.ReleaseTracks(base.ReleaseTrack.ALPHA, base.ReleaseTrack.BETA)
class EnvInit(base.Command):
  """Print the commands required to export pubsub emulator's env variables."""

  detailed_help = {
      'EXAMPLES': """\
          To print the env variables exports for a pubsub emulator, run:

            $ {command} --data-dir DATA-DIR
          """,
  }

  @staticmethod
  def Args(parser):
    parser.display_info.AddFormat('config[export]')

  def Run(self, args):
    return util.ReadEnvYaml(args.data_dir)
