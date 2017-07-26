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

"""Capture a project repository.

TODO(b/36053571) make capture a group with "create", "list", etc.
"""

import json
import os

from googlecloudsdk.api_lib.source import capture
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.util import files
from googlecloudsdk.third_party.appengine.tools import context_util


class Upload(base.CreateCommand):
  """Upload a source capture from given input files.

  This command uploads a capture of the specified source directory to
  a Google-hosted Git repository accessible with the current project's
  credentials. If the name of an existing capture is provided, the
  existing capture will be modified to include the new files.
  Otherwise a new capture will be created to hold the files.

  When creating a capture, this command can also produce a source
  context json file describing the capture.

  See https://cloud.google.com/tools/cloud-debugger/ for details on
  where to deploy the source context json file in order to enable
  Cloud Diagnostic tools to display the captured sources.
  """

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'source_location', metavar='PATH',
        help="""\
            The directory or archive containing the sources to capture. Files
            and subdirectories contained in that directory or archive will be
            added to the capture. If PATH refers to a file, the file may be
            a Java source jar or a zip archive.
        """)
    parser.add_argument(
        '--capture-id', metavar='ID',
        help="""\
            The ID of the capture to create or modify.
        """)
    parser.add_argument(
        '--target-path', metavar='PATH', default='',
        help="""\
            The directory tree under source-location will be uploaded under
            target-path in the capture's directory tree.
        """)
    parser.add_argument('--context-file', metavar='json-file-name', hidden=True)
    parser.add_argument(
        '--output-directory',
        default='.',
        help="""\
            The directory in which to create the source context files. Two
            files (source-context.json and source-contexts.json) will be
            created in that directory.
        """)
    parser.display_info.AddFormat("""
          flattened(
            capture.id,
            context_file,
            extended_context_file
          )
        """)

  def Run(self, args):
    """Run the capture upload command."""

    mgr = capture.CaptureManager()
    result = mgr.UploadCapture(args.capture_id, args.source_location,
                               args.target_path)
    if args.context_file:
      raise exceptions.ToolException(
          'The [--context-file] argument has been deprecated. Use '
          '[--output-directory] instead.')
    else:
      output_dir = args.output_directory
      files.MakeDir(output_dir)
    output_dir = os.path.realpath(output_dir)
    extended_contexts = result['source_contexts']

    result = dict(result)
    result['extended_context_file'] = os.path.join(output_dir,
                                                   'source-contexts.json')
    with open(result['extended_context_file'], 'w') as f:
      json.dump(extended_contexts, f)

    result['context_file'] = os.path.join(output_dir, 'source-context.json')
    best_context = context_util.BestSourceContext(extended_contexts)
    result['best_context'] = context_util.BestSourceContext(extended_contexts)
    with open(result['context_file'], 'w') as f:
      json.dump(best_context, f)

    log.status.write('Wrote {0} file(s), {1} bytes.\n'.format(
        result['files_written'], result['size_written']))
    files_skipped = result['files_skipped']
    if files_skipped:
      log.status.write('Skipped {0} file(s) due to size limitations.\n'.format(
          files_skipped))
    return [result]
