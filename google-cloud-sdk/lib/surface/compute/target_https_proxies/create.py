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
"""Command for creating target HTTPS proxies."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute.ssl_certificates import (
    flags as ssl_certificates_flags)
from googlecloudsdk.command_lib.compute.target_https_proxies import flags
from googlecloudsdk.command_lib.compute.url_maps import flags as url_map_flags
from googlecloudsdk.core import log


@base.ReleaseTracks(base.ReleaseTrack.GA, base.ReleaseTrack.BETA)
class CreateGA(base.CreateCommand):
  """Create a target HTTPS proxy.

    *{command}* is used to create target HTTPS proxies. A target
  HTTPS proxy is referenced by one or more forwarding rules which
  define which packets the proxy is responsible for routing. The
  target HTTPS proxy points to a URL map that defines the rules
  for routing the requests. The URL map's job is to map URLs to
  backend services which handle the actual requests. The target
  HTTPS proxy also points to an SSL certificate used for
  server-side authentication.
  """

  SSL_CERTIFICATE_ARG = None
  TARGET_HTTPS_PROXY_ARG = None
  URL_MAP_ARG = None

  @classmethod
  def Args(cls, parser):
    parser.display_info.AddFormat(flags.DEFAULT_LIST_FORMAT)
    cls.SSL_CERTIFICATE_ARG = (
        ssl_certificates_flags.SslCertificateArgumentForOtherResource(
            'target HTTPS proxy'))
    cls.SSL_CERTIFICATE_ARG.AddArgument(parser)
    cls.TARGET_HTTPS_PROXY_ARG = flags.TargetHttpsProxyArgument()
    cls.TARGET_HTTPS_PROXY_ARG.AddArgument(parser, operation_type='create')
    cls.URL_MAP_ARG = url_map_flags.UrlMapArgumentForTargetProxy(
        proxy_type='HTTPS')
    cls.URL_MAP_ARG.AddArgument(parser)

    parser.add_argument(
        '--description',
        help='An optional, textual description for the target HTTPS proxy.')

  def _CreateRequestsWithCertRefs(self, args, ssl_cert_refs):
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    client = holder.client

    url_map_ref = self.URL_MAP_ARG.ResolveAsResource(args, holder.resources)

    target_https_proxy_ref = self.TARGET_HTTPS_PROXY_ARG.ResolveAsResource(
        args, holder.resources)

    request = client.messages.ComputeTargetHttpsProxiesInsertRequest(
        project=target_https_proxy_ref.project,
        targetHttpsProxy=client.messages.TargetHttpsProxy(
            description=args.description,
            name=target_https_proxy_ref.Name(),
            urlMap=url_map_ref.SelfLink(),
            sslCertificates=[ref.SelfLink() for ref in ssl_cert_refs]))

    return client.MakeRequests([(client.apitools_client.targetHttpsProxies,
                                 'Insert', request)])

  def Run(self, args):
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    ssl_certificate_ref = self.SSL_CERTIFICATE_ARG.ResolveAsResource(
        args, holder.resources)

    return self._CreateRequestsWithCertRefs(args, [ssl_certificate_ref])


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class CreateAlpha(CreateGA):
  """Create a target HTTPS proxy.

    *{command}* is used to create target HTTPS proxies. A target
  HTTPS proxy is referenced by one or more forwarding rules which
  define which packets the proxy is responsible for routing. The
  target HTTPS proxy points to a URL map that defines the rules
  for routing the requests. The URL map's job is to map URLs to
  backend services which handle the actual requests. The target
  HTTPS proxy also points to at most 10 SSL certificates used for
  server-side authentication.
  """

  SSL_CERTIFICATES_ARG = None

  @classmethod
  def Args(cls, parser):
    parser.display_info.AddFormat(flags.DEFAULT_LIST_FORMAT)
    certs = parser.add_mutually_exclusive_group(required=True)
    cls.SSL_CERTIFICATE_ARG = (
        ssl_certificates_flags.SslCertificateArgumentForOtherResource(
            'target HTTPS proxy', required=False))
    cls.SSL_CERTIFICATE_ARG.AddArgument(parser, mutex_group=certs)
    cls.SSL_CERTIFICATES_ARG = (
        ssl_certificates_flags.SslCertificatesArgumentForOtherResource(
            'target HTTPS proxy', required=False))
    cls.SSL_CERTIFICATES_ARG.AddArgument(
        parser, mutex_group=certs, cust_metavar='SSL_CERTIFICATE')

    cls.TARGET_HTTPS_PROXY_ARG = flags.TargetHttpsProxyArgument()
    cls.TARGET_HTTPS_PROXY_ARG.AddArgument(parser)
    cls.URL_MAP_ARG = url_map_flags.UrlMapArgumentForTargetProxy(
        proxy_type='HTTPS')
    cls.URL_MAP_ARG.AddArgument(parser)

    parser.add_argument(
        '--description',
        help='An optional, textual description for the target HTTPS proxy.')

  def _GetSslCertificatesList(self, args):
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    if args.ssl_certificate:
      log.warn(
          'The --ssl-certificate flag is deprecated and will be removed soon. '
          'Use equivalent --ssl-certificates %s flag.', args.ssl_certificate)
      return [
          self.SSL_CERTIFICATE_ARG.ResolveAsResource(args, holder.resources)
      ]

    return self.SSL_CERTIFICATES_ARG.ResolveAsResource(args, holder.resources)

  def Run(self, args):
    ssl_certificate_refs = self._GetSslCertificatesList(args)

    return self._CreateRequestsWithCertRefs(args, ssl_certificate_refs)
