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
"""bigtable instances update command."""

from googlecloudsdk.api_lib.bigtable import util as bigtable_util
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.bigtable import arguments
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


class UpdateInstance(base.UpdateCommand):
  """Modify an existing Bigtable instance."""

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    (arguments.ArgAdder(parser).AddInstance().AddInstanceDescription()
     .AddInstanceType(
         help_text='Change the instance type. Note development instances can '
         'be promoted to production instances, but production instances '
         'cannot be downgraded to development.'))

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      Some value that we want to have printed later.
    """
    cli = bigtable_util.GetAdminClient()
    ref = resources.REGISTRY.Parse(
        args.instance,
        params={
            'projectsId': properties.VALUES.core.project.GetOrFail,
        },
        collection='bigtableadmin.projects.instances')
    msgs = bigtable_util.GetAdminMessages()
    instance = cli.projects_instances.Get(
        msgs.BigtableadminProjectsInstancesGetRequest(name=ref.RelativeName()))
    instance.state = None  # must be unset when calling Update
    if args.description:
      instance.displayName = args.description
    if args.instance_type:
      instance.type = msgs.Instance.TypeValueValuesEnum(args.instance_type)
    instance = cli.projects_instances.Update(instance)
    log.UpdatedResource(instance.name, kind='instance')
    return instance
