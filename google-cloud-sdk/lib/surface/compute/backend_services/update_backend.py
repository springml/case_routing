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

"""Command for updating a backend in a backend service."""

from apitools.base.py import encoding

from googlecloudsdk.api_lib.compute import backend_services_utils
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute import flags as compute_flags
from googlecloudsdk.command_lib.compute.backend_services import backend_flags
from googlecloudsdk.command_lib.compute.backend_services import flags


@base.ReleaseTracks(base.ReleaseTrack.GA)
class UpdateBackend(base.UpdateCommand):
  """Update an existing backend in a backend service.

  *{command}* updates a backend that is part of a backend
  service. This is useful for changing the way a backend
  behaves. Example changes that can be made include changing the
  load balancing policy and `draining` a backend by setting
  its capacity scaler to zero.

  Backends are named by their associated instances groups, and one
  of the `--group` or `--instance-group` flags is required to
  identify the backend that you are modifying.  You cannot "change"
  the instance group associated with a backend, but you can accomplish
  something similar with `backend-services remove-backend` and
  `backend-services add-backend`.

  `gcloud compute backend-services edit` can also be used to
  update a backend if the use of a text editor is desired.
  """

  @staticmethod
  def Args(parser):
    flags.GLOBAL_REGIONAL_BACKEND_SERVICE_ARG.AddArgument(parser)
    backend_flags.AddDescription(parser)
    flags.MULTISCOPE_INSTANCE_GROUP_ARG.AddArgument(
        parser, operation_type='update the backend service')
    backend_flags.AddBalancingMode(parser)
    backend_flags.AddCapacityLimits(parser)
    backend_flags.AddCapacityScalar(parser)

  def _GetGetRequest(self, client, backend_service_ref):
    if backend_service_ref.Collection() == 'compute.regionBackendServices':
      return (client.apitools_client.regionBackendServices,
              'Get',
              client.messages.ComputeRegionBackendServicesGetRequest(
                  backendService=backend_service_ref.Name(),
                  region=backend_service_ref.region,
                  project=backend_service_ref.project))
    return (client.apitools_client.backendServices,
            'Get',
            client.messages.ComputeBackendServicesGetRequest(
                backendService=backend_service_ref.Name(),
                project=backend_service_ref.project))

  def _GetSetRequest(self, client, backend_service_ref, replacement):
    if backend_service_ref.Collection() == 'compute.regionBackendServices':
      return (client.apitools_client.regionBackendServices,
              'Update',
              client.messages.ComputeRegionBackendServicesUpdateRequest(
                  backendService=backend_service_ref.Name(),
                  backendServiceResource=replacement,
                  region=backend_service_ref.region,
                  project=backend_service_ref.project))
    return (client.apitools_client.backendServices,
            'Update',
            client.messages.ComputeBackendServicesUpdateRequest(
                backendService=backend_service_ref.Name(),
                backendServiceResource=replacement,
                project=backend_service_ref.project))

  def _Modify(self, client, resources, backend_service_ref, args, existing):
    replacement = encoding.CopyProtoMessage(existing)

    group_ref = flags.MULTISCOPE_INSTANCE_GROUP_ARG.ResolveAsResource(
        args,
        resources,
        scope_lister=compute_flags.GetDefaultScopeLister(client))

    backend_to_update = None
    for backend in replacement.backends:
      if group_ref.SelfLink() == backend.group:
        backend_to_update = backend

    if not backend_to_update:
      scope_type = None
      scope_name = None
      if hasattr(group_ref, 'zone'):
        scope_type = 'zone'
        scope_name = group_ref.zone
      if hasattr(group_ref, 'region'):
        scope_type = 'region'
        scope_name = group_ref.region
      raise exceptions.ToolException(
          'No backend with name [{0}] in {1} [{2}] is part of the backend '
          'service [{3}].'.format(group_ref.Name(), scope_type, scope_name,
                                  backend_service_ref.Name()))

    if args.description:
      backend_to_update.description = args.description
    elif args.description is not None:
      backend_to_update.description = None

    self._ModifyBalancingModeArgs(client, args, backend_to_update)

    return replacement

  def _ModifyBalancingModeArgs(self, client, args, backend_to_update):
    """Update balancing mode fields in backend_to_update according to args.

    Args:
      client: The compute client.
      args: The arguments given to the update-backend command.
      backend_to_update: The backend message to modify.
    """

    _ModifyBalancingModeArgs(client.messages, args, backend_to_update)

  def Run(self, args):
    """Issues requests necessary to update backend of the Backend Service."""
    if not any([
        args.description is not None,
        args.balancing_mode,
        args.max_utilization is not None,
        args.max_rate is not None,
        args.max_rate_per_instance is not None,
        args.max_connections is not None,
        args.max_connections_per_instance is not None,
        args.capacity_scaler is not None,
    ]):
      raise exceptions.ToolException('At least one property must be modified.')

    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    client = holder.client

    backend_service_ref = (
        flags.GLOBAL_REGIONAL_BACKEND_SERVICE_ARG.ResolveAsResource(
            args,
            holder.resources,
            scope_lister=compute_flags.GetDefaultScopeLister(client)))
    get_request = self._GetGetRequest(client, backend_service_ref)

    backend_service = client.MakeRequests([get_request])[0]

    modified_backend_service = self._Modify(
        client, holder.resources, backend_service_ref, args, backend_service)

    return client.MakeRequests([
        self._GetSetRequest(client, backend_service_ref,
                            modified_backend_service)
    ])


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class UpdateBackendBeta(UpdateBackend):
  """Update an existing backend in a backend service.

  *{command}* updates a backend that is part of a backend
  service. This is useful for changing the way a backend
  behaves. Example changes that can be made include changing the
  load balancing policy and `draining` a backend by setting
  its capacity scaler to zero.

  Backends are named by their associated instances groups, and one
  of the `--group` or `--instance-group` flags is required to
  identify the backend that you are modifying.  You cannot "change"
  the instance group associated with a backend, but you can accomplish
  something similar with `backend-services remove-backend` and
  `backend-services add-backend`.

  `gcloud compute backend-services edit` can also be used to
  update a backend if the use of a text editor is desired.
  """

  @classmethod
  def Args(cls, parser):
    flags.GLOBAL_REGIONAL_BACKEND_SERVICE_ARG.AddArgument(parser)
    backend_flags.AddDescription(parser)
    flags.MULTISCOPE_INSTANCE_GROUP_ARG.AddArgument(
        parser, operation_type='update the backend service')
    backend_flags.AddBalancingMode(parser)
    backend_flags.AddCapacityLimits(parser)
    backend_flags.AddCapacityScalar(parser)


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class UpdateBackendAlpha(UpdateBackend):
  """Update an existing backend in a backend service.

  *{command}* updates a backend that is part of a backend
  service. This is useful for changing the way a backend
  behaves. Example changes that can be made include changing the
  load balancing policy and `draining` a backend by setting
  its capacity scaler to zero.

  Backends are named by their associated instances groups, and one
  of the `--group` or `--instance-group` flags is required to
  identify the backend that you are modifying.  You cannot "change"
  the instance group associated with a backend, but you can accomplish
  something similar with `backend-services remove-backend` and
  `backend-services add-backend`.

  `gcloud compute backend-services edit` can also be used to
  update a backend if the use of a text editor is desired.
  """

  @classmethod
  def Args(cls, parser):
    flags.GLOBAL_REGIONAL_BACKEND_SERVICE_ARG.AddArgument(parser)
    backend_flags.AddDescription(parser)
    flags.MULTISCOPE_INSTANCE_GROUP_ARG.AddArgument(
        parser, operation_type='update the backend service')
    backend_flags.AddBalancingMode(parser)
    backend_flags.AddCapacityLimits(parser)
    backend_flags.AddCapacityScalar(parser)


def _ClearMutualExclusiveBackendCapacityThresholds(backend):
  """Initialize the backend's mutually exclusive capacity thresholds."""
  backend.maxRate = None
  backend.maxRatePerInstance = None
  backend.maxConnections = None
  backend.maxConnectionsPerInstance = None


def _ModifyBalancingModeArgs(messages, args, backend_to_update):
  """Update balancing mode fields in backend_to_update according to args.

  Args:
    messages: API messages class, determined by the release track.
    args: The arguments given to the update-backend command.
    backend_to_update: The backend message to modify.
  """

  backend_services_utils.ValidateBalancingModeArgs(
      messages,
      args,
      backend_to_update.balancingMode)

  if args.balancing_mode:
    backend_to_update.balancingMode = (
        messages.Backend.BalancingModeValueValuesEnum(
            args.balancing_mode))

    # If the balancing mode is being changed to RATE (CONNECTION), we must
    # clear the max utilization and max connections (rate) fields, otherwise
    # the server will reject the request.
    if (backend_to_update.balancingMode ==
        messages.Backend.BalancingModeValueValuesEnum.RATE):
      backend_to_update.maxUtilization = None
      backend_to_update.maxConnections = None
      backend_to_update.maxConnectionsPerInstance = None
    elif (backend_to_update.balancingMode ==
          messages.Backend.BalancingModeValueValuesEnum.CONNECTION):
      backend_to_update.maxUtilization = None
      backend_to_update.maxRate = None
      backend_to_update.maxRatePerInstance = None

  # Now, we set the parameters that control load balancing.
  # ValidateBalancingModeArgs takes care that the control parameters
  # are compatible with the balancing mode.
  if args.max_utilization is not None:
    backend_to_update.maxUtilization = args.max_utilization

  # max_rate, max_rate_per_instance, max_connections and
  # max_connections_per_instance are mutually exclusive arguments.
  if args.max_rate is not None:
    _ClearMutualExclusiveBackendCapacityThresholds(backend_to_update)
    backend_to_update.maxRate = args.max_rate
  elif args.max_rate_per_instance is not None:
    _ClearMutualExclusiveBackendCapacityThresholds(backend_to_update)
    backend_to_update.maxRatePerInstance = args.max_rate_per_instance
  elif args.max_connections is not None:
    _ClearMutualExclusiveBackendCapacityThresholds(backend_to_update)
    backend_to_update.maxConnections = args.max_connections
  elif args.max_connections_per_instance is not None:
    _ClearMutualExclusiveBackendCapacityThresholds(backend_to_update)
    backend_to_update.maxConnectionsPerInstance = (
        args.max_connections_per_instance)

  if args.capacity_scaler is not None:
    backend_to_update.capacityScaler = args.capacity_scaler
