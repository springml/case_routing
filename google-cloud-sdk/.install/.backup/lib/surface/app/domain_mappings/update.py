# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Surface for updating an App Engine domain mapping."""

from googlecloudsdk.api_lib.app.api import appengine_domains_api_client as api_client
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.app import flags
from googlecloudsdk.core import log


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class UpdateBeta(base.UpdateCommand):
  """Updates a domain mapping."""

  detailed_help = {
      'DESCRIPTION':
          '{description}',
      'EXAMPLES':
          """\
          To update an App Engine domain mapping, run:

              $ {command} '*.example.com' \
                  --certificate-id=1234

          To remove a certificate from a domain:

              $ {command} '*.example.com' \
                  --no-certificate-id
          """,
  }

  @staticmethod
  def Args(parser):
    flags.DOMAIN_FLAG.AddToParser(parser)
    flags.AddCertificateIdFlag(parser, include_no_cert=True)

  def Run(self, args):
    client = api_client.AppengineDomainsApiClient.GetApiClient()
    mapping = client.UpdateDomainMapping(args.domain,
                                         args.certificate_id,
                                         args.no_certificate_id)
    log.UpdatedResource(args.domain)
    return mapping


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class UpdateAlpha(UpdateBeta):
  """Updates a domain mapping with an Alpha client."""

  @staticmethod
  def Args(parser):
    super(UpdateAlpha, UpdateAlpha).Args(parser)
    flags.AddNoManagedCertificateFlag(parser)

  def Run(self, args):
    client = api_client.AppengineDomainsApiAlphaClient.GetApiClient()
    mapping = client.UpdateDomainMapping(args.domain,
                                         args.certificate_id,
                                         args.no_certificate_id,
                                         args.no_managed_certificate)
    log.UpdatedResource(args.domain)
    return mapping
