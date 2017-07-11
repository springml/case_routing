# Copyright 2016 Google Inc. All Rights Reserved.
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

"""Command to describe a bio operation."""

from googlecloudsdk.api_lib.bio import bio
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.bio import flags
from googlecloudsdk.command_lib.bio import util as command_lib_util
from googlecloudsdk.core import properties


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class Describe(base.DescribeCommand):
  """Show metadata about a bio operation.

  Shows metadata for a bio operation given a valid operation name.

  This command can fail for the following reasons:
  * The operation specified does not exist.
  * The active account does not have permission to access the given operation.

  ## EXAMPLES

  The following command prints metadata for an operation with the name
  `OP-NAMES-ARE-A-UNIQUE-HASH`:

    $ {command} OP-NAMES-ARE-A-UNIQUE-HASH
  """

  @staticmethod
  def Args(parser):
    flags.GetOperationNameFlag('describe').AddToParser(parser)

  def Run(self, args):
    operation_ref = command_lib_util.ParseOperation(args.name)
    return bio.Operations(properties.VALUES.core.project.Get()).Get(
        operation_ref)
