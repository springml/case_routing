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
"""Command for creating target SSL proxies."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import target_proxies_utils
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute.backend_services import (
    flags as backend_service_flags)
from googlecloudsdk.command_lib.compute.ssl_certificates import (
    flags as ssl_certificates_flags)
from googlecloudsdk.command_lib.compute.target_ssl_proxies import flags
from googlecloudsdk.core import log


@base.ReleaseTracks(base.ReleaseTrack.GA, base.ReleaseTrack.BETA)
class CreateGA(base.CreateCommand):
  """Create a target SSL proxy."""

  BACKEND_SERVICE_ARG = None
  SSL_CERTIFICATE_ARG = None
  TARGET_SSL_PROXY_ARG = None

  @classmethod
  def Args(cls, parser):
    target_proxies_utils.AddProxyHeaderRelatedCreateArgs(parser)

    cls.BACKEND_SERVICE_ARG = (
        backend_service_flags.BackendServiceArgumentForTargetSslProxy())
    cls.BACKEND_SERVICE_ARG.AddArgument(parser)
    cls.SSL_CERTIFICATE_ARG = (
        ssl_certificates_flags.SslCertificateArgumentForOtherResource(
            'target SSL proxy'))
    cls.SSL_CERTIFICATE_ARG.AddArgument(parser)
    cls.TARGET_SSL_PROXY_ARG = flags.TargetSslProxyArgument()
    cls.TARGET_SSL_PROXY_ARG.AddArgument(parser, operation_type='create')

    parser.add_argument(
        '--description',
        help='An optional, textual description for the target SSL proxy.')

  def _CreateResourceWithCertRefs(self, args, ssl_cert_refs):
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())

    backend_service_ref = self.BACKEND_SERVICE_ARG.ResolveAsResource(
        args, holder.resources)

    target_ssl_proxy_ref = self.TARGET_SSL_PROXY_ARG.ResolveAsResource(
        args, holder.resources)

    client = holder.client.apitools_client
    messages = holder.client.messages
    if args.proxy_header:
      proxy_header = messages.TargetSslProxy.ProxyHeaderValueValuesEnum(
          args.proxy_header)
    else:
      proxy_header = (
          messages.TargetSslProxy.ProxyHeaderValueValuesEnum.NONE)

    request = messages.ComputeTargetSslProxiesInsertRequest(
        project=target_ssl_proxy_ref.project,
        targetSslProxy=messages.TargetSslProxy(
            description=args.description,
            name=target_ssl_proxy_ref.Name(),
            proxyHeader=proxy_header,
            service=backend_service_ref.SelfLink(),
            sslCertificates=[ref.SelfLink() for ref in ssl_cert_refs]))

    errors = []
    resources = holder.client.MakeRequests(
        [(client.targetSslProxies, 'Insert', request)], errors)

    if errors:
      utils.RaiseToolException(errors)
    return resources

  def Run(self, args):
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    ssl_certificate_ref = self.SSL_CERTIFICATE_ARG.ResolveAsResource(
        args, holder.resources)
    return self._CreateResourceWithCertRefs(args, [ssl_certificate_ref])


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class CreateAlpha(CreateGA):
  """Create a target SSL proxy."""

  SSL_CERTIFICATES_ARG = None

  @classmethod
  def Args(cls, parser):
    target_proxies_utils.AddProxyHeaderRelatedCreateArgs(parser)

    cls.BACKEND_SERVICE_ARG = (
        backend_service_flags.BackendServiceArgumentForTargetSslProxy())
    cls.BACKEND_SERVICE_ARG.AddArgument(parser)
    cls.TARGET_SSL_PROXY_ARG = flags.TargetSslProxyArgument()
    cls.TARGET_SSL_PROXY_ARG.AddArgument(parser)

    certs = parser.add_mutually_exclusive_group(required=True)
    cls.SSL_CERTIFICATE_ARG = (
        ssl_certificates_flags.SslCertificateArgumentForOtherResource(
            'target SSL proxy', required=False))
    cls.SSL_CERTIFICATE_ARG.AddArgument(parser, mutex_group=certs)
    cls.SSL_CERTIFICATES_ARG = (
        ssl_certificates_flags.SslCertificatesArgumentForOtherResource(
            'target SSL proxy', required=False))
    cls.SSL_CERTIFICATES_ARG.AddArgument(
        parser, mutex_group=certs, cust_metavar='SSL_CERTIFICATE')

    parser.add_argument(
        '--description',
        help='An optional, textual description for the target SSL proxy.')

  def _GetSslCertificatesList(self, args, holder):
    if args.ssl_certificate:
      log.warn(
          'The --ssl-certificate flag is deprecated and will be removed soon. '
          'Use equivalent --ssl-certificates %s flag.', args.ssl_certificate)
      return [
          self.SSL_CERTIFICATE_ARG.ResolveAsResource(args, holder.resources)
      ]

    return self.SSL_CERTIFICATES_ARG.ResolveAsResource(args, holder.resources)

  def Run(self, args):
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    ssl_certificate_refs = self._GetSslCertificatesList(args, holder)
    return self._CreateResourceWithCertRefs(args, ssl_certificate_refs)


CreateGA.detailed_help = {
    'brief':
        'Create a target SSL proxy',
    'DESCRIPTION':
        """
        *{command}* is used to create target SSL proxies. A target
        SSL proxy is referenced by one or more forwarding rules which
        define which packets the proxy is responsible for routing. The
        target SSL proxy points to a backend service which handle the
        actual requests. The target SSL proxy also points to an SSL
        certificate used for server-side authentication.
        """,
}

CreateAlpha.detailed_help = {
    'brief':
        'Create a target SSL proxy',
    'DESCRIPTION':
        """
        *{command}* is used to create target SSL proxies. A target
        SSL proxy is referenced by one or more forwarding rules which
        define which packets the proxy is responsible for routing. The
        target SSL proxy points to a backend service which handle the
        actual requests. The target SSL proxy also points to at most 10 SSL
        certificates used for server-side authentication.
        """,
}
