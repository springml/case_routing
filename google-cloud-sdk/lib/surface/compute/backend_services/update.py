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
"""Commands for updating backend services.

   There are separate alpha, beta, and GA command classes in this file.
"""

from apitools.base.py import encoding

from googlecloudsdk.api_lib.compute import backend_services_utils
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute import flags as compute_flags
from googlecloudsdk.command_lib.compute.backend_services import flags
from googlecloudsdk.core import log


def AddIapFlag(parser):
  # TODO(b/34479878): It would be nice if the auto-generated help text were
  # a bit better so we didn't need to be quite so verbose here.
  flags.AddIap(
      parser,
      help="""\
      Change the Identity Aware Proxy (IAP) service configuration for the
      backend service. You can set IAP to 'enabled' or 'disabled', or modify
      the OAuth2 client configuration (oauth2-client-id and
      oauth2-client-secret) used by IAP. If any fields are unspecified, their
      values will not be modified. For instance, if IAP is enabled,
      '--iap=disabled' will disable IAP, and a subsequent '--iap=enabled' will
      then enable it with the same OAuth2 client configuration as the first
      time it was enabled. See
      https://cloud.google.com/iap/ for more information about this feature.
      """)


@base.ReleaseTracks(base.ReleaseTrack.GA)
class UpdateGA(base.UpdateCommand):
  """Update a backend service.

  *{command}* is used to update backend services.
  """

  HEALTH_CHECK_ARG = None
  HTTP_HEALTH_CHECK_ARG = None
  HTTPS_HEALTH_CHECK_ARG = None

  @classmethod
  def Args(cls, parser):
    flags.GLOBAL_REGIONAL_BACKEND_SERVICE_ARG.AddArgument(
        parser, operation_type='update')
    flags.AddDescription(parser)
    cls.HEALTH_CHECK_ARG = flags.HealthCheckArgument()
    cls.HEALTH_CHECK_ARG.AddArgument(parser, cust_metavar='HEALTH_CHECK')
    cls.HTTP_HEALTH_CHECK_ARG = flags.HttpHealthCheckArgument()
    cls.HTTP_HEALTH_CHECK_ARG.AddArgument(
        parser, cust_metavar='HTTP_HEALTH_CHECK')
    cls.HTTPS_HEALTH_CHECK_ARG = flags.HttpsHealthCheckArgument()
    cls.HTTPS_HEALTH_CHECK_ARG.AddArgument(
        parser, cust_metavar='HTTPS_HEALTH_CHECK')
    flags.AddTimeout(parser, default=None)
    flags.AddPortName(parser)
    flags.AddProtocol(parser, default=None)
    flags.AddEnableCdn(parser, default=None)
    flags.AddSessionAffinity(parser, internal_lb=True)
    flags.AddAffinityCookieTtl(parser)
    flags.AddConnectionDrainingTimeout(parser)
    flags.AddCacheKeyIncludeProtocol(parser, default=None)
    flags.AddCacheKeyIncludeHost(parser, default=None)
    flags.AddCacheKeyIncludeQueryString(parser, default=None)
    flags.AddCacheKeyQueryStringList(parser)
    AddIapFlag(parser)

  def GetGetRequest(self, client, backend_service_ref):
    """Create Backend Services get request."""
    if backend_service_ref.Collection() == 'compute.regionBackendServices':
      return (
          client.apitools_client.regionBackendServices,
          'Get',
          client.messages.ComputeRegionBackendServicesGetRequest(
              project=backend_service_ref.project,
              region=backend_service_ref.region,
              backendService=backend_service_ref.Name()))
    return (
        client.apitools_client.backendServices,
        'Get',
        client.messages.ComputeBackendServicesGetRequest(
            project=backend_service_ref.project,
            backendService=backend_service_ref.Name()))

  def GetSetRequest(self, client, backend_service_ref, replacement):
    """Create Backend Services set request."""
    if backend_service_ref.Collection() == 'compute.regionBackendServices':
      return (
          client.apitools_client.regionBackendServices,
          'Update',
          client.messages.ComputeRegionBackendServicesUpdateRequest(
              project=backend_service_ref.project,
              region=backend_service_ref.region,
              backendService=backend_service_ref.Name(),
              backendServiceResource=replacement))

    return (
        client.apitools_client.backendServices,
        'Update',
        client.messages.ComputeBackendServicesUpdateRequest(
            project=backend_service_ref.project,
            backendService=backend_service_ref.Name(),
            backendServiceResource=replacement))

  def Modify(self, client, resources, args, existing):
    """Modify Backend Service."""
    replacement = encoding.CopyProtoMessage(existing)

    if args.connection_draining_timeout is not None:
      replacement.connectionDraining = client.messages.ConnectionDraining(
          drainingTimeoutSec=args.connection_draining_timeout)

    if args.description:
      replacement.description = args.description
    elif args.description is not None:
      replacement.description = None

    health_checks = flags.GetHealthCheckUris(args, self, resources)
    if health_checks:
      replacement.healthChecks = health_checks

    if args.timeout:
      replacement.timeoutSec = args.timeout

    if args.port:
      replacement.port = args.port

    if args.port_name:
      replacement.portName = args.port_name

    if args.protocol:
      replacement.protocol = (client.messages.BackendService
                              .ProtocolValueValuesEnum(args.protocol))

    if args.enable_cdn is not None:
      replacement.enableCDN = args.enable_cdn

    if args.session_affinity is not None:
      replacement.sessionAffinity = (
          client.messages.BackendService.SessionAffinityValueValuesEnum(
              args.session_affinity))

    if args.affinity_cookie_ttl is not None:
      replacement.affinityCookieTtlSec = args.affinity_cookie_ttl

    backend_services_utils.ApplyCdnPolicyArgs(
        client, args, replacement, is_update=True)

    self._ApplyIapArgs(client, args.iap, existing, replacement)

    return replacement

  def ValidateArgs(self, args):
    """Validate arguments."""
    if not any([
        args.affinity_cookie_ttl is not None,
        args.connection_draining_timeout is not None,
        args.description is not None,
        args.enable_cdn is not None,
        args.cache_key_include_protocol is not None,
        args.cache_key_include_host is not None,
        args.cache_key_include_query_string is not None,
        args.cache_key_query_string_whitelist is not None,
        args.cache_key_query_string_blacklist is not None,
        args.health_checks,
        args.http_health_checks,
        args.https_health_checks,
        args.IsSpecified('iap'),
        args.port,
        args.port_name,
        args.protocol,
        args.session_affinity is not None,
        args.timeout is not None,
    ]):
      raise exceptions.ToolException('At least one property must be modified.')

  def Run(self, args):
    """Issues requests necessary to update the Backend Services."""
    self.ValidateArgs(args)

    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    client = holder.client

    backend_service_ref = (
        flags.GLOBAL_REGIONAL_BACKEND_SERVICE_ARG.ResolveAsResource(
            args,
            holder.resources,
            scope_lister=compute_flags.GetDefaultScopeLister(client)))
    get_request = self.GetGetRequest(client, backend_service_ref)

    objects = client.MakeRequests([get_request])

    new_object = self.Modify(client, holder.resources, args, objects[0])

    # If existing object is equal to the proposed object or if
    # Modify() returns None, then there is no work to be done, so we
    # print the resource and return.
    if objects[0] == new_object:
      log.status.Print(
          'No change requested; skipping update for [{0}].'.format(
              objects[0].name))
      return objects

    return client.MakeRequests(
        [self.GetSetRequest(client, backend_service_ref, new_object)])

  def _ApplyIapArgs(self, client, iap_arg, existing, replacement):
    if iap_arg is not None:
      existing_iap = existing.iap
      replacement.iap = backend_services_utils.GetIAP(
          iap_arg, client.messages, existing_iap_settings=existing_iap)
      if replacement.iap.enabled and not (existing_iap and
                                          existing_iap.enabled):
        log.warning(backend_services_utils.IapBestPracticesNotice())
      if (replacement.iap.enabled and replacement.protocol is not
          client.messages.BackendService.ProtocolValueValuesEnum.HTTPS):
        log.warning(backend_services_utils.IapHttpWarning())


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class UpdateAlpha(UpdateGA):
  """Update a backend service.

  *{command}* is used to update backend services.
  """

  HEALTH_CHECK_ARG = None
  HTTP_HEALTH_CHECK_ARG = None
  HTTPS_HEALTH_CHECK_ARG = None

  @classmethod
  def Args(cls, parser):
    flags.GLOBAL_REGIONAL_BACKEND_SERVICE_ARG.AddArgument(
        parser, operation_type='update')
    flags.AddDescription(parser)
    cls.HEALTH_CHECK_ARG = flags.HealthCheckArgument()
    cls.HEALTH_CHECK_ARG.AddArgument(parser, cust_metavar='HEALTH_CHECK')
    cls.HTTP_HEALTH_CHECK_ARG = flags.HttpHealthCheckArgument()
    cls.HTTP_HEALTH_CHECK_ARG.AddArgument(
        parser, cust_metavar='HTTP_HEALTH_CHECK')
    cls.HTTPS_HEALTH_CHECK_ARG = flags.HttpsHealthCheckArgument()
    cls.HTTPS_HEALTH_CHECK_ARG.AddArgument(
        parser, cust_metavar='HTTPS_HEALTH_CHECK')
    flags.AddTimeout(parser, default=None)
    flags.AddPortName(parser)
    flags.AddProtocol(parser, default=None)

    flags.AddConnectionDrainingTimeout(parser)
    flags.AddEnableCdn(parser, default=None)
    flags.AddCacheKeyIncludeProtocol(parser, default=None)
    flags.AddCacheKeyIncludeHost(parser, default=None)
    flags.AddCacheKeyIncludeQueryString(parser, default=None)
    flags.AddCacheKeyQueryStringList(parser)
    flags.AddSessionAffinity(parser, internal_lb=True)
    flags.AddAffinityCookieTtl(parser)
    AddIapFlag(parser)

  def Modify(self, client, resources, args, existing):
    """Modify Backend Service."""
    replacement = super(UpdateAlpha, self).Modify(client, resources, args,
                                                  existing)

    if args.connection_draining_timeout is not None:
      replacement.connectionDraining = client.messages.ConnectionDraining(
          drainingTimeoutSec=args.connection_draining_timeout)

    return replacement

  def ValidateArgs(self, args):
    """Validate arguments."""
    if not any([
        args.affinity_cookie_ttl is not None,
        args.connection_draining_timeout is not None,
        args.description is not None,
        args.enable_cdn is not None,
        args.cache_key_include_protocol is not None,
        args.cache_key_include_host is not None,
        args.cache_key_include_query_string is not None,
        args.cache_key_query_string_whitelist is not None,
        args.cache_key_query_string_blacklist is not None,
        args.http_health_checks,
        args.IsSpecified('iap'),
        args.port,
        args.port_name,
        args.protocol,
        args.session_affinity is not None,
        args.timeout is not None,
        getattr(args, 'health_checks', None),
        getattr(args, 'https_health_checks', None),
    ]):
      raise exceptions.ToolException('At least one property must be modified.')


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class UpdateBeta(UpdateGA):
  """Update a backend service.

  *{command}* is used to update backend services.
  """

  HEALTH_CHECK_ARG = None
  HTTP_HEALTH_CHECK_ARG = None
  HTTPS_HEALTH_CHECK_ARG = None

  @classmethod
  def Args(cls, parser):
    flags.GLOBAL_REGIONAL_BACKEND_SERVICE_ARG.AddArgument(
        parser, operation_type='update')
    flags.AddDescription(parser)
    cls.HEALTH_CHECK_ARG = flags.HealthCheckArgument()
    cls.HEALTH_CHECK_ARG.AddArgument(parser, cust_metavar='HEALTH_CHECK')
    cls.HTTP_HEALTH_CHECK_ARG = flags.HttpHealthCheckArgument()
    cls.HTTP_HEALTH_CHECK_ARG.AddArgument(
        parser, cust_metavar='HTTP_HEALTH_CHECK')
    cls.HTTPS_HEALTH_CHECK_ARG = flags.HttpsHealthCheckArgument()
    cls.HTTPS_HEALTH_CHECK_ARG.AddArgument(
        parser, cust_metavar='HTTPS_HEALTH_CHECK')
    flags.AddTimeout(parser, default=None)
    flags.AddPortName(parser)
    flags.AddProtocol(parser, default=None)

    flags.AddConnectionDrainingTimeout(parser)
    flags.AddEnableCdn(parser, default=None)
    flags.AddSessionAffinity(parser, internal_lb=True)
    flags.AddAffinityCookieTtl(parser)
    AddIapFlag(parser)
    flags.AddCacheKeyIncludeProtocol(parser, default=None)
    flags.AddCacheKeyIncludeHost(parser, default=None)
    flags.AddCacheKeyIncludeQueryString(parser, default=None)
    flags.AddCacheKeyQueryStringList(parser)

  def Modify(self, client, resources, args, existing):
    """Modify Backend Service."""
    replacement = super(UpdateBeta, self).Modify(client, resources, args,
                                                 existing)

    if args.connection_draining_timeout is not None:
      replacement.connectionDraining = client.messages.ConnectionDraining(
          drainingTimeoutSec=args.connection_draining_timeout)

    return replacement

  def ValidateArgs(self, args):
    """Validate arguments."""
    if not any([
        args.affinity_cookie_ttl is not None,
        args.connection_draining_timeout is not None,
        args.description is not None,
        args.enable_cdn is not None,
        args.cache_key_include_protocol is not None,
        args.cache_key_include_host is not None,
        args.cache_key_include_query_string is not None,
        args.cache_key_query_string_whitelist is not None,
        args.cache_key_query_string_blacklist is not None,
        args.health_checks,
        args.http_health_checks,
        args.https_health_checks,
        args.IsSpecified('iap'),
        args.port,
        args.port_name,
        args.protocol,
        args.session_affinity is not None,
        args.timeout is not None,
    ]):
      raise exceptions.ToolException('At least one property must be modified.')
