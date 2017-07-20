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
"""Command for creating instance templates."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import image_utils
from googlecloudsdk.api_lib.compute import instance_template_utils
from googlecloudsdk.api_lib.compute import instance_utils
from googlecloudsdk.api_lib.compute import metadata_utils
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute import flags
from googlecloudsdk.command_lib.compute.instance_templates import flags as instance_templates_flags
from googlecloudsdk.command_lib.compute.instances import flags as instances_flags


def _CommonArgs(parser,
                multiple_network_interface_cards,
                release_track,
                support_alias_ip_ranges,
                support_network_tier,
                support_local_ssd_size=False):
  """Common arguments used in Alpha, Beta, and GA."""
  parser.display_info.AddFormat(instance_templates_flags.DEFAULT_LIST_FORMAT)
  metadata_utils.AddMetadataArgs(parser)
  instances_flags.AddDiskArgs(parser)
  if release_track in [base.ReleaseTrack.ALPHA]:
    instances_flags.AddCreateDiskArgs(parser)
  if support_local_ssd_size:
    instances_flags.AddLocalSsdArgsWithSize(parser)
  else:
    instances_flags.AddLocalSsdArgs(parser)
  instances_flags.AddCanIpForwardArgs(parser)
  instances_flags.AddAddressArgs(
      parser, instances=False,
      multiple_network_interface_cards=multiple_network_interface_cards,
      support_alias_ip_ranges=support_alias_ip_ranges,
      support_network_tier=support_network_tier)
  instances_flags.AddAcceleratorArgs(parser)
  instances_flags.AddMachineTypeArgs(parser)
  instances_flags.AddMaintenancePolicyArgs(parser)
  instances_flags.AddNoRestartOnFailureArgs(parser)
  instances_flags.AddPreemptibleVmArgs(parser)
  instances_flags.AddServiceAccountAndScopeArgs(parser, False)
  instances_flags.AddTagsArgs(parser)
  instances_flags.AddCustomMachineTypeArgs(parser)
  instances_flags.AddImageArgs(parser)
  instances_flags.AddNetworkArgs(parser)

  if support_network_tier:
    instances_flags.AddNetworkTierArgs(parser, instance=True)

  flags.AddRegionFlag(
      parser,
      resource_type='subnetwork',
      operation_type='attach')

  parser.add_argument(
      '--description',
      help='Specifies a textual description for the instance template.')

  Create.InstanceTemplateArg = (
      instance_templates_flags.MakeInstanceTemplateArg())
  Create.InstanceTemplateArg.AddArgument(parser, operation_type='create')


@base.ReleaseTracks(base.ReleaseTrack.GA)
class Create(base.CreateCommand):
  """Create a Compute Engine virtual machine instance template.

  *{command}* facilitates the creation of Google Compute Engine
  virtual machine instance templates. For example, running:

      $ {command} INSTANCE-TEMPLATE

  will create one instance templates called 'INSTANCE-TEMPLATE'.

  Instance templates are global resources, and can be used to create
  instances in any zone.
  """
  _support_network_tier = False

  @classmethod
  def Args(cls, parser):
    _CommonArgs(parser, multiple_network_interface_cards=False,
                release_track=base.ReleaseTrack.GA,
                support_alias_ip_ranges=False,
                support_network_tier=cls._support_network_tier)

  def ValidateDiskFlags(self, args):
    """Validates the values of all disk-related flags."""
    instances_flags.ValidateDiskCommonFlags(args)
    instances_flags.ValidateDiskBootFlags(args)
    instances_flags.ValidateCreateDiskFlags(args)

  def Run(self, args):
    """Creates and runs an InstanceTemplates.Insert request.

    Args:
      args: argparse.Namespace, An object that contains the values for the
          arguments specified in the .Args() method.

    Returns:
      A resource object dispatched by display.Displayer().
    """
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    client = holder.client

    self.ValidateDiskFlags(args)
    instances_flags.ValidateLocalSsdFlags(args)
    instances_flags.ValidateNicFlags(args)
    instances_flags.ValidateServiceAccountAndScopeArgs(args)
    instances_flags.ValidateAcceleratorArgs(args)

    boot_disk_size_gb = utils.BytesToGb(args.boot_disk_size)
    utils.WarnIfDiskSizeIsTooSmall(boot_disk_size_gb, args.boot_disk_type)

    instance_template_ref = (
        Create.InstanceTemplateArg.ResolveAsResource(
            args, holder.resources))

    metadata = metadata_utils.ConstructMetadataMessage(
        client.messages,
        metadata=args.metadata,
        metadata_from_file=args.metadata_from_file)

    if hasattr(args, 'network_interface') and args.network_interface:
      network_interfaces = (
          instance_template_utils.CreateNetworkInterfaceMessages)(
              resources=holder.resources,
              scope_lister=flags.GetDefaultScopeLister(client),
              messages=client.messages,
              network_interface_arg=args.network_interface,
              region=args.region,
              support_network_tier=self._support_network_tier)
    else:
      network_tier = getattr(args, 'network_tier', None)
      network_interfaces = [
          instance_template_utils.CreateNetworkInterfaceMessage(
              resources=holder.resources,
              scope_lister=flags.GetDefaultScopeLister(client),
              messages=client.messages,
              network=args.network,
              region=args.region,
              subnet=args.subnet,
              address=(instance_template_utils.EPHEMERAL_ADDRESS
                       if not args.no_address and not args.address
                       else args.address),
              network_tier=network_tier)
      ]

    scheduling = instance_utils.CreateSchedulingMessage(
        messages=client.messages,
        maintenance_policy=args.maintenance_policy,
        preemptible=args.preemptible,
        restart_on_failure=args.restart_on_failure)

    if args.no_service_account:
      service_account = None
    else:
      service_account = args.service_account
    service_accounts = instance_utils.CreateServiceAccountMessages(
        messages=client.messages,
        scopes=[] if args.no_scopes else args.scopes,
        service_account=service_account)

    create_boot_disk = not instance_utils.UseExistingBootDisk(args.disk or [])
    if create_boot_disk:
      image_expander = image_utils.ImageExpander(client, holder.resources)
      try:
        image_uri, _ = image_expander.ExpandImageFlag(
            user_project=instance_template_ref.project,
            image=args.image,
            image_family=args.image_family,
            image_project=args.image_project,
            return_image_resource=True)
      except utils.ImageNotFoundError as e:
        if args.IsSpecified('image_project'):
          raise e
        image_uri, _ = image_expander.ExpandImageFlag(
            user_project=instance_template_ref.project,
            image=args.image,
            image_family=args.image_family,
            image_project=args.image_project,
            return_image_resource=False)
        raise utils.ImageNotFoundError(
            'The resource [{}] was not found. Is the image located in another '
            'project? Use the --image-project flag to specify the '
            'project where the image is located.'.format(image_uri))
    else:
      image_uri = None

    if args.tags:
      tags = client.messages.Tags(items=args.tags)
    else:
      tags = None

    persistent_disks = (
        instance_template_utils.CreatePersistentAttachedDiskMessages(
            client.messages, args.disk or []))

    persistent_create_disks = (
        instance_template_utils.CreatePersistentCreateDiskMessages(
            client, holder.resources, instance_template_ref.project,
            getattr(args, 'create_disk', [])))

    if create_boot_disk:
      boot_disk_list = [
          instance_template_utils.CreateDefaultBootAttachedDiskMessage(
              messages=client.messages,
              disk_type=args.boot_disk_type,
              disk_device_name=args.boot_disk_device_name,
              disk_auto_delete=args.boot_disk_auto_delete,
              disk_size_gb=boot_disk_size_gb,
              image_uri=image_uri)]
    else:
      boot_disk_list = []

    local_ssds = []
    for x in args.local_ssd or []:
      local_ssd = instance_utils.CreateLocalSsdMessage(
          holder.resources,
          client.messages,
          x.get('device-name'),
          x.get('interface'),
          x.get('size'))
      local_ssds.append(local_ssd)

    disks = (
        boot_disk_list + persistent_disks + persistent_create_disks + local_ssds
    )

    machine_type = instance_utils.InterpretMachineType(
        machine_type=args.machine_type,
        custom_cpu=args.custom_cpu,
        custom_memory=args.custom_memory,
        ext=getattr(args, 'custom_extensions', None))

    guest_accelerators = (
        instance_template_utils.CreateAcceleratorConfigMessages(
            client.messages, getattr(args, 'accelerator', None)))

    request = client.messages.ComputeInstanceTemplatesInsertRequest(
        instanceTemplate=client.messages.InstanceTemplate(
            properties=client.messages.InstanceProperties(
                machineType=machine_type,
                disks=disks,
                canIpForward=args.can_ip_forward,
                metadata=metadata,
                networkInterfaces=network_interfaces,
                serviceAccounts=service_accounts,
                scheduling=scheduling,
                tags=tags,
                guestAccelerators=guest_accelerators,
            ),
            description=args.description,
            name=instance_template_ref.Name(),
        ),
        project=instance_template_ref.project)

    if getattr(args, 'min_cpu_platform', None):
      request.instanceTemplate.properties.minCpuPlatform = args.min_cpu_platform

    return client.MakeRequests([(client.apitools_client.instanceTemplates,
                                 'Insert', request)])


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class CreateBeta(Create):
  """Create a Compute Engine virtual machine instance template.

  *{command}* facilitates the creation of Google Compute Engine
  virtual machine instance templates. For example, running:

      $ {command} INSTANCE-TEMPLATE

  will create one instance templates called 'INSTANCE-TEMPLATE'.

  Instance templates are global resources, and can be used to create
  instances in any zone.
  """

  _support_network_tier = False

  @classmethod
  def Args(cls, parser):
    _CommonArgs(
        parser,
        multiple_network_interface_cards=True,
        release_track=base.ReleaseTrack.BETA,
        support_alias_ip_ranges=True,
        support_network_tier=cls._support_network_tier)
    instances_flags.AddMinCpuPlatformArgs(parser, base.ReleaseTrack.BETA)


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class CreateAlpha(Create):
  """Create a Compute Engine virtual machine instance template.

  *{command}* facilitates the creation of Google Compute Engine
  virtual machine instance templates. For example, running:

      $ {command} INSTANCE-TEMPLATE

  will create one instance templates called 'INSTANCE-TEMPLATE'.

  Instance templates are global resources, and can be used to create
  instances in any zone.
  """

  _support_network_tier = True

  @classmethod
  def Args(cls, parser):
    _CommonArgs(parser, multiple_network_interface_cards=True,
                release_track=base.ReleaseTrack.ALPHA,
                support_alias_ip_ranges=True,
                support_network_tier=cls._support_network_tier,
                support_local_ssd_size=True)
    instances_flags.AddMinCpuPlatformArgs(parser, base.ReleaseTrack.ALPHA)
