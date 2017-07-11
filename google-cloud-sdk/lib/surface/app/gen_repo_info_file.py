# Copyright 2014 Google Inc. All Rights Reserved.
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

"""The gen_repo_info_file command."""

import json
import os

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core.util import files
from googlecloudsdk.third_party.appengine.tools import context_util


@base.Hidden
@base.ReleaseTracks(base.ReleaseTrack.GA, base.ReleaseTrack.BETA)
class GenRepoInfoFile(base.Command):
  """[DEPRECATED] Saves repository information in a file.

  DEPRECATED, use `gcloud beta debug source gen-repo-info-file` instead.  The
  generated file is an opaque blob representing which source revision the
  application was built at, and which Google-hosted repository this revision
  will be pushed to.
  """

  detailed_help = {
      'DESCRIPTION': """\
          DEPRECATED, use `gcloud beta debug source gen-repo-info-file`
          instead.

          This command generates two files, {old_name} and
          {contexts_filename}, containing information on the source revision
          and remote repository associated with the given source directory.

          {contexts_filename} contains information on all remote repositories
          associated with the directory, while {old_name} contains
          information only on one repository. It will refer to the associated
          Cloud Repository if there is one, or the remote Git repository if
          there is no Cloud Repository.

          {old_name} is deprecated in favor of {contexts_filename}.
          It is generated solely for compatibility with existing tools during
          the transition.
          """.format(old_name=context_util.CONTEXT_FILENAME,
                     contexts_filename=context_util.EXT_CONTEXT_FILENAME),
      'EXAMPLES': """\
          To generate repository information files for your app,
          from your source directory run:

            $ {command}
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--source-directory',
        default='.',
        help='The path to directory containing the source code for the build.')
    # TODO(b/25215149) Remove this option.
    parser.add_argument(
        '--output-file',
        help=(
            '(Deprecated; use --output-directory instead.) '
            'Specifies the full name of the output file to contain a single '
            'source context.  The file name must be "{old_name}" in '
            'order to work with cloud diagnostic tools.').format(
                old_name=context_util.CONTEXT_FILENAME))
    parser.add_argument(
        '--output-directory',
        default='',
        help=(
            'The directory in which to create the source context files. '
            'Defaults to the current directory, or the directory containing '
            '--output-file if that option is provided with a file name that '
            'includes a directory path.'))

  def Run(self, args):
    log.warn('This command is deprecated. Please use '
             '`gcloud beta source debug gen-repo-info-file` instead.')
    contexts = context_util.CalculateExtendedSourceContexts(
        args.source_directory)

    # First create the old-style source-context.json file
    if args.output_file:
      log.warn(
          'The --output-file option is deprecated and will soon be removed.')
      output_directory = os.path.dirname(args.output_file)
      output_file = args.output_file
    else:
      output_directory = ''
      output_file = context_util.CONTEXT_FILENAME

    if not output_directory:
      if args.output_directory:
        output_directory = args.output_directory
        output_file = os.path.join(output_directory, output_file)
      else:
        output_directory = '.'

    best_context = context_util.BestSourceContext(contexts)
    files.MakeDir(output_directory)
    with open(output_file, 'w') as f:
      json.dump(best_context, f, indent=2, sort_keys=True)

    # Create the new source-contexts.json file.
    if args.output_directory and args.output_directory != output_directory:
      output_directory = args.output_directory
      files.MakeDir(output_directory)
    with open(os.path.join(output_directory, context_util.EXT_CONTEXT_FILENAME),
              'w') as f:
      json.dump(contexts, f, indent=2, sort_keys=True)
