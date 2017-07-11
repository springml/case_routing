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
"""Command to create a new project."""

import httplib
import sys

from apitools.base.py import exceptions as apitools_exceptions

from googlecloudsdk.api_lib.cloudresourcemanager import projects_api
from googlecloudsdk.api_lib.resource_manager import operations
from googlecloudsdk.api_lib.service_management import enable_api as services_enable_api
from googlecloudsdk.api_lib.service_management import services_util

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.projects import util as command_lib_util
from googlecloudsdk.command_lib.resource_manager import flags

from googlecloudsdk.command_lib.util import labels_util
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_io

ID_DESCRIPTION = ('Project IDs must start with a lowercase letter and can '
                  'have lowercase ASCII letters, digits or hyphens. '
                  'Project IDs must be between 6 and 30 characters.')


class _BaseCreate(object):
  """Create command base for all release tracks of project create."""

  @staticmethod
  def Args(parser):
    """Default argument specification."""

    labels_util.AddCreateLabelsFlags(parser)
    type_ = arg_parsers.RegexpValidator(r'[a-z][a-z0-9-]{5,29}', ID_DESCRIPTION)
    parser.add_argument(
        'id',
        metavar='PROJECT_ID',
        type=type_,
        nargs='?',
        help='ID for the project you want to create.\n\n{0}'.format(
            ID_DESCRIPTION))
    parser.add_argument(
        '--name',
        help='Name for the project you want to create. '
        'If not specified, will use project id as name.')
    parser.add_argument(
        '--enable-cloud-apis',
        action='store_true',
        default=True,
        help='Enable cloudapis.googleapis.com during creation.')
    parser.add_argument(
        '--set-as-default',
        action='store_true',
        default=False,
        help='Set newly created project as [core.project] property.')
    flags.OrganizationIdFlag('to use as a parent').AddToParser(parser)

  def Run(self, args):
    """Default Run method implementation."""

    flags.CheckParentFlags(args, parent_required=False)
    project_id = args.id
    if not project_id and args.name:
      candidate = command_lib_util.IdFromName(args.name)
      if candidate and console_io.PromptContinue(
          'No project id provided.',
          'Use [{}] as project id'.format(candidate),
          throw_if_unattended=True):
        project_id = candidate
    if not project_id:
      raise exceptions.RequiredArgumentException(
          'PROJECT_ID', 'an id must be provided for the new project')
    project_ref = command_lib_util.ParseProject(project_id)
    try:
      create_op = projects_api.Create(
          project_ref,
          display_name=args.name,
          parent=projects_api.ParentNameToResourceId(
              flags.GetParentFromFlags(args)),
          update_labels=labels_util.GetUpdateLabelsDictFromArgs(args))
    except apitools_exceptions.HttpError as error:
      if error.status_code == httplib.CONFLICT:
        msg = ('Project creation failed. The project ID you specified is '
               'already in use by another project. Please try an alternative '
               'ID.')
        unused_type, unused_value, traceback = sys.exc_info()
        raise exceptions.HttpException, msg, traceback
      raise
    log.CreatedResource(project_ref, async=True)
    create_op = operations.WaitForOperation(create_op)

    # Enable cloudapis.googleapis.com
    if args.enable_cloud_apis:
      log.debug('Enabling cloudapis.googleapis.com')
      services_client = apis.GetClientInstance('servicemanagement', 'v1')
      enable_operation = services_enable_api.EnableServiceApiCall(
          project_ref.Name(), 'cloudapis.googleapis.com')
      enable_operation_ref = resources.REGISTRY.Parse(
          enable_operation.name, collection='servicemanagement.operations')
      services_util.WaitForOperation(enable_operation_ref, services_client)

    if args.set_as_default:
      project_property = properties.FromString('core/project')
      properties.PersistProperty(project_property, args.id)
      log.status.Print('Updated property [core/project] to [{0}].'
                       .format(args.id))

    return operations.ExtractOperationResponse(create_op,
                                               apis.GetMessagesModule(
                                                   'cloudresourcemanager',
                                                   'v1').Project)


@base.ReleaseTracks(base.ReleaseTrack.GA)
class Create(_BaseCreate, base.CreateCommand):
  """Create a new project.

  Creates a new project with the given project ID.

  ## EXAMPLES

  The following command creates a project with ID `example-foo-bar-1`, name
  `Happy project` and label `type=happy`:

    $ {command} example-foo-bar-1 --name="Happy project" --labels=type=happy

  The following command creates a project with ID `example-3` with parent
  `organizations/2048`:

    $ {command} example-3 --organization=2048
  """


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class CreateAlpha(_BaseCreate, base.CreateCommand):
  """Create a new project.

  Creates a new project with the given project ID.

  ## EXAMPLES

  The following command creates a project with ID `example-foo-bar-1`, name
  `Happy project` and label `type=happy`:

    $ {command} example-foo-bar-1 --name="Happy project" --labels=type=happy

  The following command creates a project with ID `example-2` with parent
  `folders/12345`:

    $ {command} example-2 --folder=12345

  The following command creates a project with ID `example-3` with parent
  `organizations/2048`:

    $ {command} example-3 --organization=2048
  """

  @staticmethod
  def Args(parser):
    _BaseCreate.Args(parser)
    flags.FolderIdFlag('to use as a parent').AddToParser(parser)
