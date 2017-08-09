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

"""Create a Google Cloud Platform git repository.
"""

from apitools.base.py import exceptions
from googlecloudsdk.api_lib.service_management import enable_api
from googlecloudsdk.api_lib.service_management import services_util
from googlecloudsdk.api_lib.sourcerepo import sourcerepo
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as c_exc
from googlecloudsdk.command_lib.source import flags
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_io

_ERROR_FORMAT = ('ResponseError: status=[{status_description}], '
                 'code=[{status_code}], message=[{message}]. '
                 '{details.message?\ndetails{?COLON?}\n{?}}')
_BILLING_URL = 'https://cloud.google.com/source-repositories/docs/pricing'
_SOURCEREPO_SERVICE_NAME = 'sourcerepo.googleapis.com'


@base.ReleaseTracks(base.ReleaseTrack.GA, base.ReleaseTrack.ALPHA,
                    base.ReleaseTrack.BETA)
class Create(base.CreateCommand):
  """Create a cloud source repository.

  This command creates a named git repository for the currently
  active Google Cloud Platform project.

  ## EXAMPLES

  To create a named repository in the current project issue the
  following commands:

    $ gcloud init
    $ {command} REPOSITORY_NAME

  Once you push contents to it, they can be browsed in the
  Developers Console.
  """

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'repository_name',
        help="""\
        Name of the repository. May contain between 3 and 63 (inclusive)
        lowercase letters, digits, and hyphens. Must start with a letter, and
        may not end with a hyphen.
        """)

  def Run(self, args):
    """Create a GCP repository to the current directory.

    Args:
      args: argparse.Namespace, the arguments this command is run with.

    Returns:
      (sourcerepo_v1_messages.Repo) The created respository.

    Raises:
      ToolException: on project initialization errors, on missing billing
        account, and when the repo name is already in use.
    """
    res = resources.REGISTRY.Parse(
        args.repository_name,
        params={'projectsId': properties.VALUES.core.project.GetOrFail},
        collection='sourcerepo.projects.repos')
    # check that the name does not have forbidden characters.
    # we'd like to do this by putting the validator in the flag type, but
    # we cannot for now because it needs to work on the parsed name.
    flags.REPO_NAME_VALIDATOR(res.Name())
    source_handler = sourcerepo.Source()

    # This service enabled check can be removed when cl/148491846 is ready
    if not enable_api.IsServiceEnabled(res.projectsId,
                                       _SOURCEREPO_SERVICE_NAME):
      message = ('{api} is required for repository creation and is not '
                 'enabled.'.format(api=_SOURCEREPO_SERVICE_NAME))
      if console_io.PromptContinue(
          message=message,
          prompt_string='Would you like to enable it?',
          default=True):
        operation = enable_api.EnableServiceApiCall(res.projectsId,
                                                    _SOURCEREPO_SERVICE_NAME)
        # wait for the operation to complete, will raise an exception if the
        # operation fails.
        services_util.ProcessOperationResult(operation, async=False)
      else:
        error_message = ('Cannot create a repository without enabling '
                         '{api}'.format(api=_SOURCEREPO_SERVICE_NAME))
        raise exceptions.Error(error_message)
    try:
      repo = source_handler.CreateRepo(res)
      if repo:
        log.CreatedResource(res.Name())
        log.Print('You may be billed for this repository. '
                  'See {url} for details.'.format(url=_BILLING_URL))
        return repo
    except exceptions.HttpError as error:
      exc = c_exc.HttpException(error)
      exc.error_format = _ERROR_FORMAT
      raise exc
