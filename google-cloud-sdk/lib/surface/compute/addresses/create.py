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
"""Command for reserving IP addresses."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import name_generator
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute import flags as compute_flags
from googlecloudsdk.command_lib.compute.addresses import flags


def _Args(cls, parser):
  """Argument parsing."""

  cls.ADDRESSES_ARG = flags.AddressArgument(required=False)
  cls.ADDRESSES_ARG.AddArgument(parser, operation_type='create')
  flags.AddDescription(parser)


@base.ReleaseTracks(base.ReleaseTrack.GA)
class Create(base.CreateCommand):
  """Reserve IP addresses.

  *{command}* is used to reserve one or more IP addresses. Once
  an IP address is reserved, it will be associated with the
  project until it is released using 'gcloud compute addresses
  delete'. Ephemeral IP addresses that are in use by resources
  in the project can be reserved using the `--addresses`
  flag.

  ## EXAMPLES
  To reserve three IP addresses in the `us-central1` region,
  run:

    $ {command} ADDRESS-1 ADDRESS-2 ADDRESS-3 --region us-central1

  To reserve ephemeral IP addresses 162.222.181.198 and
  23.251.146.189 which are being used by virtual machine
  instances in the `us-central1` region, run:

    $ {command} --addresses 162.222.181.198,23.251.146.189 --region us-central1

  In the above invocation, the two addresses will be assigned
  random names.
  """

  ADDRESSES_ARG = None

  @classmethod
  def Args(cls, parser):
    _Args(cls, parser)
    flags.AddAddresses(parser)

  def GetAddress(self, messages, args, address, address_ref):
    return messages.Address(
        address=address,
        description=args.description,
        name=address_ref.Name())

  def Run(self, args):
    """Issues requests necessary to create Addresses."""
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    client = holder.client

    names, addresses = self._GetNamesAndAddresses(args)
    if not args.name:
      args.name = names

    address_refs = self.ADDRESSES_ARG.ResolveAsResource(
        args, holder.resources,
        scope_lister=compute_flags.GetDefaultScopeLister(client))

    requests = []
    for address, address_ref in zip(addresses, address_refs):
      address_msg = self.GetAddress(
          client.messages,
          args,
          address,
          address_ref)

      if address_ref.Collection() == 'compute.globalAddresses':
        requests.append((client.apitools_client.globalAddresses, 'Insert',
                         client.messages.ComputeGlobalAddressesInsertRequest(
                             address=address_msg, project=address_ref.project)))
      elif address_ref.Collection() == 'compute.addresses':
        requests.append((client.apitools_client.addresses, 'Insert',
                         client.messages.ComputeAddressesInsertRequest(
                             address=address_msg,
                             region=address_ref.region,
                             project=address_ref.project)))

    return client.MakeRequests(requests)

  def _GetNamesAndAddresses(self, args):
    """Returns names and addresses provided in args."""
    if not args.addresses and not args.name:
      raise exceptions.ToolException(
          'At least one name or address must be provided.')

    if args.name:
      names = args.name
    else:
      # If we dont have any names then we must some addresses.
      names = [name_generator.GenerateRandomName() for _ in args.addresses]

    if args.addresses:
      addresses = args.addresses
    else:
      # If we dont have any addresses then we must some names.
      addresses = [None] * len(args.name)

    if len(addresses) != len(names):
      raise exceptions.ToolException(
          'If providing both, you must specify the same number of names as '
          'addresses.')

    return names, addresses


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class CreateBeta(Create):
  """Reserve IP addresses.

  *{command}* is used to reserve one or more IP addresses. Once
  an IP address is reserved, it will be associated with the
  project until it is released using 'gcloud compute addresses
  delete'. Ephemeral IP addresses that are in use by resources
  in the project, can be reserved using the ``--addresses''
  flag.

  ## EXAMPLES
  To reserve three IP addresses in the ``us-central1'' region,
  run:

    $ {command} ADDRESS-1 ADDRESS-2 ADDRESS-3 --region us-central1

  To reserve ephemeral IP addresses 162.222.181.198 and
  23.251.146.189 which are being used by virtual machine
  instances in the ``us-central1'' region, run:

    $ {command} --addresses 162.222.181.198,23.251.146.189 --region us-central1

  In the above invocation, the two addresses will be assigned
  random names.
  """

  @classmethod
  def Args(cls, parser):
    _Args(cls, parser)
    flags.AddAddressesAndIPVersions(parser, required=False)

  def GetAddress(self, messages, args, address, address_ref):
    """Override."""
    if args.ip_version or (
        address is None and
        address_ref.Collection() == 'compute.globalAddresses'):
      ip_version = messages.Address.IpVersionValueValuesEnum(
          args.ip_version or 'IPV4')
    else:
      # IP version is only specified in global requests if an address is not
      # specified to determine whether an ipv4 or ipv6 address should be
      # allocated.
      ip_version = None

    return messages.Address(
        address=address,
        description=args.description,
        ipVersion=ip_version,
        name=address_ref.Name())


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class CreateAlpha(Create):
  """Reserve IP addresses.

  *{command}* is used to reserve one or more IP addresses. Once
  an IP address is reserved, it will be associated with the
  project until it is released using 'gcloud compute addresses
  delete'. Ephemeral IP addresses that are in use by resources
  in the project, can be reserved using the ``--addresses''
  flag.

  ## EXAMPLES
  To reserve three IP addresses in the ``us-central1'' region,
  run:

    $ {command} ADDRESS-1 ADDRESS-2 ADDRESS-3 --region us-central1

  To reserve ephemeral IP addresses 162.222.181.198 and
  23.251.146.189 which are being used by virtual machine
  instances in the ``us-central1'' region, run:

    $ {command} --addresses 162.222.181.198,23.251.146.189 --region us-central1

  In the above invocation, the two addresses will be assigned
  random names.

  To reserve an IP address from the subnet ``default'' in the ``us-central1''
  region, run:

    $ {command} SUBNET-ADDRESS-1 --region us-central1 --subnet default

  """

  SUBNETWORK_ARG = None

  @classmethod
  def Args(cls, parser):
    _Args(cls, parser)
    flags.AddAddressesAndIPVersions(parser, required=False)
    flags.AddNetworkTier(parser)

    cls.SUBNETWORK_ARG = flags.SubnetworkArgument()
    cls.SUBNETWORK_ARG.AddArgument(parser)

  def ConstructNetworkTier(self, messages, args):
    if args.network_tier:
      return messages.Address.NetworkTierValueValuesEnum(args.network_tier)
    else:
      return None

  def GetAddress(self, messages, args, address, address_ref):
    """Override."""
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    network_tier = self.ConstructNetworkTier(messages, args)

    if args.ip_version or (
        address is None and
        address_ref.Collection() == 'compute.globalAddresses'):
      ip_version = messages.Address.IpVersionValueValuesEnum(
          args.ip_version or 'IPV4')
    else:
      # IP version is only specified in global requests if an address is not
      # specified to determine whether an ipv4 or ipv6 address should be
      # allocated.
      ip_version = None

    # TODO(b/36862747): get rid of args.subnet check
    if args.subnet:
      if address_ref.Collection() == 'compute.globalAddresses':
        raise exceptions.ToolException(
            '[--subnet] may not be specified for global addresses.')
      if not args.subnet_region:
        args.subnet_region = address_ref.region
      subnetwork_url = flags.SubnetworkArgument().ResolveAsResource(
          args, holder.resources).SelfLink()
    else:
      subnetwork_url = None

    return messages.Address(
        address=address,
        description=args.description,
        networkTier=network_tier,
        ipVersion=ip_version,
        name=address_ref.Name(),
        addressType=(
            messages.Address.AddressTypeValueValuesEnum.INTERNAL
            if subnetwork_url else None),
        subnetwork=subnetwork_url)
