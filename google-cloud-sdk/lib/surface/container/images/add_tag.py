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
"""Add tag command."""

import httplib

from containerregistry.client import docker_name
from containerregistry.client.v2 import docker_http as v2_docker_http
from containerregistry.client.v2 import docker_image as v2_image
from containerregistry.client.v2 import docker_session as v2_session
from containerregistry.client.v2_2 import docker_http as v2_2_docker_http
from containerregistry.client.v2_2 import docker_image as v2_2_image
from containerregistry.client.v2_2 import docker_session as v2_2_session
from googlecloudsdk.api_lib.container.images import util
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.container import flags
from googlecloudsdk.core import http
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io


class Create(base.CreateCommand):
  """Adds tags to existing image."""

  detailed_help = {
      'DESCRIPTION':
          """\
          The container images add-tag command adds the tag specified in
          the second tag parameter to the image referenced in the first
          tag parameter. Repositories must be hosted by the Google Container
          Registry.
      """,
      'EXAMPLES':
          """\
          Add a tag to another tag:

            $ {command} gcr.io/myproject/myimage:mytag1
              gcr.io/myproject/myimage:mytag2

          Add a tag to a digest

            $ {command} gcr.io/myproject/myimage@sha256:digest
              gcr.io/myproject/myimage:mytag2

          Add a tag to latest

            $ {command} gcr.io/myproject/myimage
              gcr.io/myproject/myimage:mytag2

          Promote a tag to latest

            $ {command} gcr.io/myproject/myimage:mytag1
              gcr.io/myproject/myimage:latest

      """,
  }

  @staticmethod
  def Args(parser):
    flags.AddTagOrDigestPositional(parser, arg_name='src_image',
                                   verb='add a tag for', repeated=False)
    flags.AddTagOrDigestPositional(parser, arg_name='dest_image',
                                   verb='be the new tag', repeated=False,
                                   tags_only=True)

  def Run(self, args):
    # pylint: disable=missing-docstring
    def Push(image, dest_name, creds, http_obj, src_name, session_push_type):
      with session_push_type(dest_name, creds, http_obj) as push:
        push.upload(image)
        log.CreatedResource(dest_name)
      log.UpdatedResource(src_name)

    http_obj = http.Http()

    src_name = util.GetDockerImageFromTagOrDigest(args.src_image)
    dest_name = docker_name.Tag(args.dest_image)

    console_io.PromptContinue(
        'This will tag {0} with {1}'.format(src_name, dest_name),
        default=True,
        cancel_on_no=True)
    creds = util.CredentialProvider()
    try:
      with v2_2_image.FromRegistry(src_name, creds, http_obj) as v2_2_img:
        if v2_2_img.exists():
          Push(v2_2_img, dest_name, creds, http_obj, src_name,
               v2_2_session.Push)
          return

      with v2_image.FromRegistry(src_name, creds, http_obj) as v2_img:
        Push(v2_img, dest_name, creds, http_obj, src_name, v2_session.Push)

    except (v2_docker_http.V2DiagnosticException,
            v2_2_docker_http.V2DiagnosticException) as err:
      raise util.GcloudifyRecoverableV2Errors(err, {
          httplib.FORBIDDEN: 'Add-tag failed, access denied.',
          httplib.NOT_FOUND: 'Add-tag failed, not found: {0}'.format(src_name)
      })
