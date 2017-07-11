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
"""ml-engine project initialization command."""

from googlecloudsdk.api_lib.cloudresourcemanager import projects_api
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_io


DEPRECATION_WARNING = """\
The `init-project` command is deprecated and will be removed in the 160.0.0
Cloud SDK release. This command is no longer necessary; Cloud ML Engine will
work without having run it."""
DEPRECATION_ERROR = """\
The `init-project` command has been removed. This command is no longer
necessary; Cloud ML Engine will work without having run it."""


EDITOR_ROLE = 'roles/editor'


def _InitProject(version):
  """Initialize the current project."""
  client = apis.GetClientInstance('ml', version)
  msgs = apis.GetMessagesModule('ml', version)

  project = properties.VALUES.core.project.GetOrFail()
  project_ref = resources.REGISTRY.Create('ml.projects', projectsId=project)
  console_io.PromptContinue(
      message='\nCloud ML Engine needs to add its service accounts to your '
      'project [{0}] as Editors. This will enable Cloud Machine Learning to '
      'access resources in your project when running your training and '
      'prediction jobs. This operation requires OWNER permissions.'.format(
          project),
      cancel_on_no=True)

  # Get service account information from Cloud ML Engine service.
  req = msgs.MlProjectsGetConfigRequest(name=project_ref.RelativeName())
  resp = client.projects.GetConfig(req)

  # Add Cloud ML Engine service account.
  cloud_ml_service_account = 'serviceAccount:' + resp.serviceAccount
  cloudresourcemanager_project_ref = resources.REGISTRY.Create(
      'cloudresourcemanager.projects', projectId=project)
  projects_api.AddIamPolicyBinding(
      cloudresourcemanager_project_ref, cloud_ml_service_account, EDITOR_ROLE)
  log.status.Print('Added {0} as an Editor to project \'{1}\'.'.format(
      cloud_ml_service_account, project))


# TODO(b/36970124): Remove completely
@base.Deprecate(is_removed=True, warning=DEPRECATION_WARNING,
                error=DEPRECATION_ERROR)
class InitProject(base.Command):
  """Initialize project for Cloud ML Engine."""

  def Run(self, args):
    _InitProject('v1')

_DETAILED_HELP = {
    'DESCRIPTION': """\
        {command} initializes the current project for use with Google Cloud
        Machine Learning Engine. Specifically, it adds the required Cloud
        Machine Learning Engine service accounts to the current project as
        editors.
  """
}

InitProject.detailed_help = _DETAILED_HELP
