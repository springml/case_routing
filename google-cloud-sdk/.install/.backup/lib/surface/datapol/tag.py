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

"""datapol tag command."""

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.datapol import tag_lib


@base.Hidden
@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class Tag(base.Command):
  """Tag a data asset with Datapol annotations.

  For example:

    gcloud alpha datapol tag path1,path2,path3 taxonomy::annotation

  Will tag the data assets specified by path1,path2,path3 with the annotation.

  If --remove is specified, the specified annotation will be removed from
  specified data assets.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('data_asset',
                        type=arg_parsers.ArgList(min_length=1),
                        default=[],
                        metavar='DATA_ASSET_PATH',
                        help='Comma-separated paths to the data assets.')
    parser.add_argument('annotation',
                        default='',
                        metavar='TAXONOMY_ANNOTATION',
                        help='Annotation to tag the data asset(s) with.')
    parser.add_argument('--load',
                        required=False,
                        metavar='FILE_PATH',
                        help='Tag data assets with annotations specified in a '
                        'text file.')
    parser.add_argument('--remove',
                        required=False,
                        action='store_true',
                        default=False,
                        help='If set, remove the specified annotations on data '
                        'assets.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
      command invocation.

    Returns:
      Status of command execution.
    """
    return tag_lib.TagDataAsset(args.data_asset, args.annotation, args.load,
                                args.remove)
