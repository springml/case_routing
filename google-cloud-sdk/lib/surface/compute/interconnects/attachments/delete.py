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

"""Command for deleting interconnects attachments."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.api_lib.compute.interconnects.attachments import client
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute.interconnects.attachments import flags


class Delete(base.DeleteCommand):
  """Delete interconnects.

  *{command}* deletes Google Compute Engine interconnect attachment.
  """

  INTERCONNECT_ATTACHMENT_ARG = None

  @classmethod
  def Args(cls, parser):
    cls.INTERCONNECT_ATTACHMENT_ARG = flags.InterconnectAttachmentArgument(
        plural=True)
    cls.INTERCONNECT_ATTACHMENT_ARG.AddArgument(parser, operation_type='delete')

  def Run(self, args):
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    refs = self.INTERCONNECT_ATTACHMENT_ARG.ResolveAsResource(
        args, holder.resources)
    utils.PromptForDeletion(refs)

    requests = []
    for ref in refs:
      interconnect_attachment = client.InterconnectAttachment(
          ref, compute_client=holder.client)
      requests.extend(
          interconnect_attachment.Delete(only_generate_request=True))

    return holder.client.MakeRequests(requests)
