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

"""datapol taxonomies create command."""

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.datapol import create_lib


@base.Hidden
@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class Create(base.Command):
  """Create a DataPol taxonomy."""

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('name',
                        default='',
                        metavar='TAXONOMY_NAME',
                        help='Name of the taxonomy.')
    parser.add_argument('--administrators',
                        required=True,
                        type=arg_parsers.ArgList(min_length=1),
                        default=[],
                        metavar='username',
                        help='Comma-separated list of administrator(s) who '
                        'can modify / delete this taxonomy or add other '
                        'administrators and users.')
    parser.add_argument('--users',
                        required=False,
                        type=arg_parsers.ArgList(min_length=1),
                        default=[],
                        metavar='username',
                        help='Comma-separated list of users who can use the '
                        'annotations in this taxonomy to tag data objects.')
    parser.add_argument('--load',
                        required=False,
                        default='',
                        metavar='FILE_PATH',
                        help='Import a pre-defined taxonomy from a file.')
    parser.add_argument('--description',
                        required=False,
                        default='',
                        metavar='DESCRIPTION',
                        help='Taxonomy description.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
      command invocation.

    Returns:
      Status of command execution.
    """
    return create_lib.CreateTaxonomy(args.name, args.administrators, args.users,
                                     args.load, args.description)
