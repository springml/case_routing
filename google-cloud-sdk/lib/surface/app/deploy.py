
# Copyright 2013 Google Inc. All Rights Reserved.
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

"""The gcloud app deploy command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.app import deploy_util


_DETAILED_HELP = {
    'brief': ('Deploy the local code and/or configuration of your app to App '
              'Engine.'),
    'DESCRIPTION': """\
        This command is used to deploy both code and configuration to the App
        Engine server.  As an input it takes one or more ``DEPLOYABLES'' that
        should be uploaded.  A ``DEPLOYABLE'' can be a service's .yaml file or a
        configuration's .yaml file.

        This command supports App Engine flexible task queue files. The format
        of task queue files can be found at:
        https://cloud.google.com/appengine/docs/python/config/queueref
        """,
    'EXAMPLES': """\
        To deploy a single service, run:

          $ {command} ~/my_app/app.yaml

        To deploy multiple services, run:

          $ {command} ~/my_app/app.yaml ~/my_app/another_service.yaml
        """,
}


@base.ReleaseTracks(base.ReleaseTrack.GA)
class DeployGA(base.SilentCommand):
  """Deploy the local code and/or configuration of your app to App Engine."""

  @staticmethod
  def Args(parser):
    """Get arguments for this command."""
    deploy_util.ArgsDeploy(parser)

  def Run(self, args):
    runtime_builder_strategy = deploy_util.GetRuntimeBuilderStrategy(
        base.ReleaseTrack.GA)
    return deploy_util.RunDeploy(
        args, runtime_builder_strategy=runtime_builder_strategy)


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class DeployBeta(base.SilentCommand):
  """Deploy the local code and/or configuration of your app to App Engine."""

  @staticmethod
  def Args(parser):
    """Get arguments for this command."""
    deploy_util.ArgsDeploy(parser)

  def Run(self, args):
    runtime_builder_strategy = deploy_util.GetRuntimeBuilderStrategy(
        base.ReleaseTrack.BETA)
    return deploy_util.RunDeploy(
        args,
        enable_endpoints=True,
        use_beta_stager=True,
        runtime_builder_strategy=runtime_builder_strategy,
        use_service_management=True,
        check_for_stopped=True
    )

DeployGA.detailed_help = _DETAILED_HELP
DeployBeta.detailed_help = _DETAILED_HELP
