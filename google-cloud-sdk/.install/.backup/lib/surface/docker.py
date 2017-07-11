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

"""Provides the docker CLI access to the Google Container Registry.

Sets docker up to authenticate with the Google Container Registry,
and passes all flags after -- to the docker CLI.
"""

import argparse

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.docker import constants
from googlecloudsdk.core.docker import docker


# By default, we'll set up authentication for these registries.
# If the user changes the --server argument to something not in this list,
# we'll just give them a warning that they're using an unexpected server.
_DEFAULT_REGISTRIES = constants.ALL_SUPPORTED_REGISTRIES


@base.ReleaseTracks(base.ReleaseTrack.GA)
class Docker(base.Command):
  """Provides the docker CLI access to the Google Container Registry.

  The {command} command group wraps docker commands, so that gcloud can
  inject the appropriate fresh authentication token into requests that interact
  with the docker registry.

  All docker-specific flags are passed through to the underlying docker command.
  A full reference of docker's command line options available after -- can be
  found here: [](https://docs.docker.com/engine/reference/commandline/cli/).

  You may also run `{command} -- --help` to view the docker CLI's help directly.

  More information on Google Container Registry can be found here:
  https://cloud.google.com/container-registry/ and detailed documentation can be
  found here: https://cloud.google.com/container-registry/docs/

  ## EXAMPLES

  Pull the image '{registry}/google-containers/pause:1.0' from the docker
  registry:

    $ {command} -- pull {registry}/google-containers/pause:1.0

  Push the image '{registry}/example-org/example-image:latest' to our private
  docker registry.

    $ {command} -- push {registry}/example-org/example-image:latest

  Configure authentication, then simply use docker:

    $ {command} --authorize-only

    $ docker push {registry}/example-org/example-image:latest

  """

  detailed_help = {
      'registry': constants.DEFAULT_REGISTRY,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--server', '-s',
        type=arg_parsers.ArgList(min_length=1),
        metavar='SERVER',
        help='The address of the Google Cloud Registry.',
        required=False,
        default=_DEFAULT_REGISTRIES)
    parser.add_argument(
        '--authorize-only', '-a',
        help='Configure docker authorization only, do not launch the '
        'docker command-line.',
        action='store_true')

    parser.add_argument(
        '--docker-host',
        help='The URL to connect to Docker Daemon. Format: tcp://host:port or '
        'unix:///path/to/socket.')

    parser.add_argument(
        'docker_args', nargs=argparse.REMAINDER, default=[],
        help='Arguments to pass to docker.')

  def Run(self, args):
    """Executes the given docker command, after refreshing our credentials.

    Args:
      args: An argparse.Namespace that contains the values for
         the arguments specified in the .Args() method.

    Raises:
      exceptions.ExitCodeNoError: The docker command execution failed.
    """
    force_refresh = True
    for server in args.server:
      if server not in _DEFAULT_REGISTRIES:
        log.warn('Authenticating to a non-default server: {server}.'.format(
            server=server))
      docker.UpdateDockerCredentials(server, refresh=force_refresh)
      # Only force a refresh for the first server we authorize
      force_refresh = False

    if args.authorize_only:
      # NOTE: We don't know at this point how long the access token we have
      # placed in the docker configuration will last.  More information needs
      # to be exposed from all credential kinds in order for us to have an
      # accurate awareness of lifetime here.
      log.err.Print('Short-lived access for {server} configured.'.format(
          server=args.server))
      return

    docker_args = args.docker_args or []
    docker_args = (docker_args if not args.docker_host else
                   ['-H', args.docker_host] + docker_args)

    result = docker.Execute(docker_args)
    # Explicitly avoid displaying an error message that might
    # distract from the docker error message already displayed.
    if result:
      raise exceptions.ExitCodeNoError(exit_code=result)
    return
