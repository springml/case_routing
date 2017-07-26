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
"""Command for creating VM instances running Docker images."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import containers_utils
from googlecloudsdk.api_lib.compute import instance_utils
from googlecloudsdk.api_lib.compute import metadata_utils
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.api_lib.compute import zone_utils
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute import flags
from googlecloudsdk.command_lib.compute.instances import flags as instances_flags
from googlecloudsdk.command_lib.util import labels_util


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class CreateFromContainer(base.CreateCommand):
  """Command for creating VM instances running Docker images."""

  @staticmethod
  def Args(parser):
    """Register parser args."""
    parser.display_info.AddFormat(instances_flags.DEFAULT_LIST_FORMAT)
    metadata_utils.AddMetadataArgs(parser)
    instances_flags.AddDiskArgs(parser, True)
    instances_flags.AddCreateDiskArgs(parser)
    instances_flags.AddLocalSsdArgsWithSize(parser)
    instances_flags.AddCanIpForwardArgs(parser)
    instances_flags.AddAddressArgs(parser, instances=True)
    instances_flags.AddMachineTypeArgs(parser)
    instances_flags.AddMaintenancePolicyArgs(parser)
    instances_flags.AddNoRestartOnFailureArgs(parser)
    instances_flags.AddPreemptibleVmArgs(parser)
    instances_flags.AddServiceAccountAndScopeArgs(parser, False)
    instances_flags.AddTagsArgs(parser)
    instances_flags.AddCustomMachineTypeArgs(parser)
    instances_flags.AddNetworkArgs(parser)
    instances_flags.AddPrivateNetworkIpArgs(parser)
    instances_flags.AddDockerArgs(parser)
    instances_flags.AddPublicDnsArgs(parser, instance=True)
    instances_flags.AddNetworkTierArgs(parser, instance=True)
    instances_flags.AddMinCpuPlatformArgs(parser, base.ReleaseTrack.ALPHA)
    labels_util.AddCreateLabelsFlags(parser)

    parser.add_argument(
        '--description',
        help='Specifies a textual description of the instances.')

    instances_flags.INSTANCES_ARG.AddArgument(parser, operation_type='create')

    CreateFromContainer.SOURCE_INSTANCE_TEMPLATE = (
        instances_flags.MakeSourceInstanceTemplateArg())
    CreateFromContainer.SOURCE_INSTANCE_TEMPLATE.AddArgument(parser)

  def GetSourceInstanceTemplate(self, args, resources):
    if not args.IsSpecified('source_instance_template'):
      return None
    ref = self.SOURCE_INSTANCE_TEMPLATE.ResolveAsResource(args, resources)
    return ref.SelfLink()

  def Run(self, args):
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    client = holder.client

    source_instance_template = self.GetSourceInstanceTemplate(
        args, holder.resources)
    # gcloud creates default values for some fields in Instance resource
    # when no value was specified on command line.
    # When --source-instance-template was specified, defaults are taken from
    # Instance Template and gcloud flags are used to override them - by default
    # fields should not be initialized.
    skip_defaults = source_instance_template is not None

    instances_flags.ValidateDockerArgs(args)
    instances_flags.ValidateDiskCommonFlags(args)
    instances_flags.ValidateLocalSsdFlags(args)
    instances_flags.ValidateServiceAccountAndScopeArgs(args)
    if instance_utils.UseExistingBootDisk(args.disk or []):
      raise exceptions.InvalidArgumentException(
          '--disk',
          'Boot disk specified for containerized VM.')

    if (skip_defaults and not args.IsSpecified('maintenance_policy') and
        not args.IsSpecified('preemptible') and
        not args.IsSpecified('restart_on_failure')):
      scheduling = None
    else:
      scheduling = instance_utils.CreateSchedulingMessage(
          messages=client.messages,
          maintenance_policy=args.maintenance_policy,
          preemptible=args.preemptible,
          restart_on_failure=args.restart_on_failure)

    if args.no_service_account:
      service_account = None
    else:
      service_account = args.service_account
    if (skip_defaults and not args.IsSpecified('scopes') and
        not args.IsSpecified('no_scopes') and
        not args.IsSpecified('service_account') and
        not args.IsSpecified('no_service_account')):
      service_accounts = []
    else:
      service_accounts = instance_utils.CreateServiceAccountMessages(
          messages=client.messages,
          scopes=[] if args.no_scopes else args.scopes,
          service_account=service_account)

    user_metadata = metadata_utils.ConstructMetadataMessage(
        client.messages,
        metadata=args.metadata,
        metadata_from_file=args.metadata_from_file)
    containers_utils.ValidateUserMetadata(user_metadata)

    boot_disk_size_gb = utils.BytesToGb(args.boot_disk_size)
    utils.WarnIfDiskSizeIsTooSmall(boot_disk_size_gb, args.boot_disk_type)

    instance_refs = instances_flags.INSTANCES_ARG.ResolveAsResource(
        args,
        holder.resources,
        scope_lister=flags.GetDefaultScopeLister(client))

    # Check if the zone is deprecated or has maintenance coming.
    zone_resource_fetcher = zone_utils.ZoneResourceFetcher(client)
    zone_resource_fetcher.WarnForZonalCreation(instance_refs)

    instances_flags.ValidatePublicDnsFlags(args)

    if (skip_defaults and not args.IsSpecified('network') and
        not args.IsSpecified('subnet') and
        not args.IsSpecified('private_network_ip') and
        not args.IsSpecified('no_address') and
        not args.IsSpecified('address') and
        not args.IsSpecified('network_tier') and
        not args.IsSpecified('no_public_dns') and
        not args.IsSpecified('public_dns') and
        not args.IsSpecified('no_public_ptr') and
        not args.IsSpecified('public_ptr') and
        not args.IsSpecified('no_public_ptr_domain') and
        not args.IsSpecified('public_ptr_domain')):
      network_interfaces = []
    else:
      network_interfaces = [instance_utils.CreateNetworkInterfaceMessage(
          resources=holder.resources,
          compute_client=client,
          network=args.network,
          subnet=args.subnet,
          private_network_ip=args.private_network_ip,
          no_address=args.no_address,
          address=args.address,
          instance_refs=instance_refs,
          network_tier=args.network_tier,
          no_public_dns=getattr(args, 'no_public_dns', None),
          public_dns=getattr(args, 'public_dns', None),
          no_public_ptr=getattr(args, 'no_public_ptr', None),
          public_ptr=getattr(args, 'public_ptr', None),
          no_public_ptr_domain=getattr(args, 'no_public_ptr_domain', None),
          public_ptr_domain=getattr(args, 'public_ptr_domain', None))]

    if (skip_defaults and not args.IsSpecified('machine_type') and
        not args.IsSpecified('custom_cpu') and
        not args.IsSpecified('custom_memory')):
      machine_type_uris = [None for _ in instance_refs]
    else:
      machine_type_uris = instance_utils.CreateMachineTypeUris(
          resources=holder.resources,
          compute_client=client,
          machine_type=args.machine_type,
          custom_cpu=args.custom_cpu,
          custom_memory=args.custom_memory,
          ext=getattr(args, 'custom_extensions', None),
          instance_refs=instance_refs)

    image_uri = containers_utils.ExpandCosImageFlag(client)

    args_labels = getattr(args, 'labels', None)
    labels = None
    if args_labels:
      labels = client.messages.Instance.LabelsValue(
          additionalProperties=[
              client.messages.Instance.LabelsValue.AdditionalProperty(
                  key=key, value=value)
              for key, value in sorted(args.labels.iteritems())])

    if skip_defaults and not args.IsSpecified('can_ip_forward'):
      can_ip_forward = None
    else:
      can_ip_forward = args.can_ip_forward

    requests = []
    for instance_ref, machine_type_uri in zip(instance_refs, machine_type_uris):
      metadata = containers_utils.CreateMetadataMessage(
          client.messages, args.run_as_privileged, args.container_manifest,
          args.docker_image, args.port_mappings, args.run_command,
          user_metadata, instance_ref.Name())
      request = client.messages.ComputeInstancesInsertRequest(
          instance=client.messages.Instance(
              canIpForward=can_ip_forward,
              disks=(self._CreateDiskMessages(holder, args, boot_disk_size_gb,
                                              image_uri, instance_ref,
                                              skip_defaults)),
              description=args.description,
              machineType=machine_type_uri,
              metadata=metadata,
              minCpuPlatform=args.min_cpu_platform,
              name=instance_ref.Name(),
              networkInterfaces=network_interfaces,
              serviceAccounts=service_accounts,
              scheduling=scheduling,
              tags=containers_utils.CreateTagsMessage(client.messages,
                                                      args.tags)),
          project=instance_ref.project,
          zone=instance_ref.zone)
      if labels:
        request.instance.labels = labels
      if source_instance_template:
        request.sourceInstanceTemplate = source_instance_template

      requests.append((client.apitools_client.instances,
                       'Insert', request))

    return client.MakeRequests(requests)

  def _CreateDiskMessages(self, holder, args, boot_disk_size_gb, image_uri,
                          instance_ref, skip_defaults):
    """Creates API messages with disks attached to VM instance."""
    if (skip_defaults and not args.IsSpecified('disk') and
        not args.IsSpecified('create_disk') and
        not args.IsSpecified('local_ssd') and
        not args.IsSpecified('boot_disk_type') and
        not args.IsSpecified('boot_disk_device_name') and
        not args.IsSpecified('boot_disk_auto_delete')):
      return []
    else:
      persistent_disks, _ = (
          instance_utils.CreatePersistentAttachedDiskMessages(
              holder.resources, holder.client, None, args.disk or [],
              instance_ref))
      persistent_create_disks = (
          instance_utils.CreatePersistentCreateDiskMessages(
              holder.client, holder.resources, None,
              getattr(args, 'create_disk', []), instance_ref))
      local_ssds = []
      for x in args.local_ssd or []:
        local_ssd = instance_utils.CreateLocalSsdMessage(
            holder.resources,
            holder.client.messages,
            x.get('device-name'),
            x.get('interface'),
            x.get('size'),
            instance_ref.zone,
            instance_ref.project)
        local_ssds.append(local_ssd)
      boot_disk = instance_utils.CreateDefaultBootAttachedDiskMessage(
          holder.client, holder.resources,
          disk_type=args.boot_disk_type,
          disk_device_name=args.boot_disk_device_name,
          disk_auto_delete=args.boot_disk_auto_delete,
          disk_size_gb=boot_disk_size_gb,
          require_csek_key_create=None,
          image_uri=image_uri,
          instance_ref=instance_ref,
          csek_keys=None)
      return (
          [boot_disk] + persistent_disks + persistent_create_disks + local_ssds)


CreateFromContainer.detailed_help = {
    'brief': """\
    Command for creating Google Compute engine virtual machine instances running Docker images.
    """,
    'DESCRIPTION': """\
        *{command}* facilitates the creation of Google Compute Engine virtual
        machines that runs a Docker image. For example, running:

          $ {command} instance-1 --zone us-central1-a --docker-image=gcr.io/google-containers/busybox

        will create an instance called instance-1, in the us-central1-a zone,
        running the 'busybox' image.

        For more examples, refer to the *EXAMPLES* section below.
        """,
    'EXAMPLES': """\
        To run the gcr.io/google-containers/busybox image on an instance named
        'instance-1' that exposes port 80, run:

          $ {command} instance-1 --docker-image=gcr.io/google-containers/busybox --port-mappings=80:80:TCP

        To run the gcr.io/google-containers/busybox image on an instance named
        'instance-1' that executes 'echo "Hello world"' as a run command, run:

          $ {command} instance-1 --docker-image=gcr.io/google-containers/busybox --run-command='echo "Hello world"'

        To run the gcr.io/google-containers/busybox image in privileged mode, run:

          $ {command} instance-1 --docker-image=gcr.io/google-containers/busybox --run-as-privileged
        """
}
