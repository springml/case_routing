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
"""Command for adding access configs to virtual machine instances."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import constants
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute.instances import flags


DETAILED_HELP = {
    'DESCRIPTION': """\
        *{command}* is used to create access configurations for network
        interfaces of Google Compute Engine virtual machines.
        """,
}


def _Args(parser, support_public_dns, support_network_tier):
  """Register parser args common to all tracks."""

  parser.add_argument(
      '--access-config-name',
      default=constants.DEFAULT_ACCESS_CONFIG_NAME,
      help="""\
      Specifies the name of the new access configuration. ``{0}''
      is used as the default if this flag is not provided.
      """.format(constants.DEFAULT_ACCESS_CONFIG_NAME))

  parser.add_argument(
      '--address',
      action=arg_parsers.StoreOnceAction,
      help="""\
      Specifies the external IP address of the new access
      configuration. If this is not specified, then the service will
      choose an available ephemeral IP address. If an explicit IP
      address is given, then that IP address must be reserved by the
      project and not be in use by another resource.
      """)

  flags.AddNetworkInterfaceArgs(parser)
  if support_public_dns:
    flags.AddPublicDnsArgs(parser, instance=False)
  if support_network_tier:
    flags.AddNetworkTierArgs(parser, instance=False)
  flags.INSTANCE_ARG.AddArgument(parser)


@base.ReleaseTracks(base.ReleaseTrack.GA, base.ReleaseTrack.BETA)
class AddAccessConfigInstances(base.SilentCommand):
  """Create a Google Compute Engine virtual machine access configuration."""

  _support_public_dns = False

  @classmethod
  def Args(cls, parser):
    _Args(
        parser,
        support_public_dns=cls._support_public_dns,
        support_network_tier=False)

  def Run(self, args):
    """Invokes request necessary for adding an access config."""
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    client = holder.client

    instance_ref = flags.INSTANCE_ARG.ResolveAsResource(
        args,
        holder.resources,
        scope_lister=flags.GetInstanceZoneScopeLister(client))

    access_config = client.messages.AccessConfig(
        name=args.access_config_name,
        natIP=args.address,
        type=client.messages.AccessConfig.TypeValueValuesEnum.ONE_TO_ONE_NAT)

    if self._support_public_dns:
      flags.ValidatePublicDnsFlags(args)

      if args.no_public_dns is True:
        access_config.setPublicDns = False
      elif args.public_dns is True:
        access_config.setPublicDns = True

      if args.no_public_ptr is True:
        access_config.setPublicPtr = False
      elif args.public_ptr is True:
        access_config.setPublicPtr = True

      if (args.no_public_ptr_domain is not True and
          args.public_ptr_domain is not None):
        access_config.publicPtrDomainName = args.public_ptr_domain

    network_tier = getattr(args, 'network_tier', None)
    if network_tier is not None:
      access_config.networkTier = (client.messages.AccessConfig.
                                   NetworkTierValueValuesEnum(network_tier))

    request = client.messages.ComputeInstancesAddAccessConfigRequest(
        accessConfig=access_config,
        instance=instance_ref.Name(),
        networkInterface=args.network_interface,
        project=instance_ref.project,
        zone=instance_ref.zone)

    return client.MakeRequests([(client.apitools_client.instances,
                                 'AddAccessConfig', request)])


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class AddAccessConfigInstancesAlpha(AddAccessConfigInstances):
  """Create a Google Compute Engine virtual machine access configuration."""

  _support_public_dns = True

  @classmethod
  def Args(cls, parser):
    _Args(
        parser,
        support_public_dns=cls._support_public_dns,
        support_network_tier=True)

AddAccessConfigInstances.detailed_help = DETAILED_HELP
