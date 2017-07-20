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

"""Get Server Config."""

from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.container import flags
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


@base.ReleaseTracks(base.ReleaseTrack.GA, base.ReleaseTrack.BETA)
class GetServerConfig(base.Command):
  """Get Container Engine server config."""

  @staticmethod
  def Args(parser):
    """Add arguments to the parser.

    Args:
      parser: argparse.ArgumentParser, This is a standard argparser parser with
        which you can register arguments.  See the public argparse documentation
        for its capabilities.
    """
    flags.AddZoneFlag(parser)

  def Run(self, args):
    adapter = self.context['api_adapter']

    project_id = properties.VALUES.core.project.Get(required=True)
    location = getattr(args, 'region', None)
    if not location:
      location = properties.VALUES.compute.zone.Get(required=True)

    log.status.Print('Fetching server config for {zone}'.format(zone=location))
    return adapter.GetServerConfig(project_id, location)


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class GetServerConfigAlpha(GetServerConfig):
  """Get Container Engine server config."""

  @staticmethod
  def Args(parser):
    """Add arguments to the parser.

    Args:
      parser: argparse.ArgumentParser, This is a standard argparser parser with
        which you can register arguments.  See the public argparse documentation
        for its capabilities.
    """
    flags.AddZoneAndRegionFlags(parser, region_hidden=True)
