# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Command for removing an interface from a Google Compute Engine router."""

from apitools.base.py import encoding
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute.routers import flags
from googlecloudsdk.core import exceptions


class InterfaceNotFoundError(exceptions.Error):
  """Raised when an interface is not found."""

  def __init__(self, name):
    self.name = name
    msg = 'interface `{0}` not found'.format(name)
    super(InterfaceNotFoundError, self
         ).__init__(msg)


class RemoveBgpPeer(base.UpdateCommand):
  """Remove an interface from a Google Compute Engine router.

  *{command}* removes an interface from a Google Compute Engine router.
  """

  ROUTER_ARG = None

  @classmethod
  def Args(cls, parser):
    cls.ROUTER_ARG = flags.RouterArgument()
    cls.ROUTER_ARG.AddArgument(parser, operation_type='update')

    parser.add_argument(
        '--interface-name',
        required=True,
        help='The name of the interface being removed.')

  def GetGetRequest(self, client, router_ref):
    return (client.apitools_client.routers,
            'Get',
            client.messages.ComputeRoutersGetRequest(
                router=router_ref.Name(),
                region=router_ref.region,
                project=router_ref.project))

  def GetSetRequest(self, client, router_ref, replacement):
    return (client.apitools_client.routers,
            'Update',
            client.messages.ComputeRoutersUpdateRequest(
                router=router_ref.Name(),
                routerResource=replacement,
                region=router_ref.region,
                project=router_ref.project))

  def Modify(self, args, existing):
    replacement = encoding.CopyProtoMessage(existing)

    # remove interface if exists
    interface = None
    for i in replacement.interfaces:
      if i.name == args.interface_name:
        interface = i
        replacement.interfaces.remove(interface)
        break

    if interface is None:
      raise InterfaceNotFoundError(args.interface_name)

    return replacement

  def Run(self, args):
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    client = holder.client

    router_ref = self.ROUTER_ARG.ResolveAsResource(args, holder.resources)
    get_request = self.GetGetRequest(client, router_ref)

    objects = client.MakeRequests([get_request])

    new_object = self.Modify(args, objects[0])

    return client.MakeRequests(
        [self.GetSetRequest(client, router_ref, new_object)])
