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
"""Command for listing grantable roles for a given resource."""

import re
import textwrap

from apitools.base.py import list_pager

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.iam import base_classes


class ListGrantableRoles(base_classes.BaseIamCommand):
  """List IAM grantable roles for a resource.

  This command displays the list of grantable roles for a resource.
  The resource can be referenced either via the full resource name or via a URI.
  User can then add IAM policy bindings to grant the roles.
  """

  detailed_help = {
      'EXAMPLES': textwrap.dedent("""\
          List grantable roles for a project:

            $ {command} //cloudresourcemanager.googleapis.com/projects/PROJECT_ID

          List grantable roles for a resource identified via full resource name:

            $ {command} //compute.googleapis.com/projects/example-project/zones/us-central1-f/instances/example-instance

          List grantable roles for a resource identified via URI:

            $ {command} https://www.googleapis.com/compute/v1/projects/example-project/zones/us-central1-f/instances/example-instance
      """),
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'resource',
        help=('The full resource name to get the list of roles for.'))
    base.FILTER_FLAG.AddToParser(parser)
    base.PAGE_SIZE_FLAG.AddToParser(parser)
    base.PAGE_SIZE_FLAG.SetDefault(parser, 100)

  def Run(self, args):
    resource = None
    if args.resource.startswith('//'):
      # The atomic resource path inputted, just use this
      resource = args.resource
    if args.resource.startswith('http'):
      # This is a full resource URL that needs to be converted to an atomic path
      resource_ref = self.resources.REGISTRY.Parse(args.resource)
      full_name = resource_ref.SelfLink()
      full_name = re.sub(r'\w+://', '//', full_name)  # no protocol at the start
      full_name = re.sub(r'/v[0-9]+[0-9a-zA-z]*/', '/', full_name)  # no version
      if full_name.startswith('//www.'):
        # Convert '//www.googleapis.com/compute/' to '//compute.googleapis.com/'
        splitted_list = full_name.split('/')
        service = full_name.split('/')[3]
        splitted_list.pop(3)
        full_name = '/'.join(splitted_list)
        full_name = full_name.replace('//www.', '//{0}.'.format(service))
      resource = full_name

    if not resource:
      raise exceptions.ToolException(
          'The given resource is not a valid full resource name or URL.')

    return list_pager.YieldFromList(
        self.iam_client.roles,
        self.messages.QueryGrantableRolesRequest(fullResourceName=resource),
        field='roles',
        method='QueryGrantableRoles',
        batch_size=args.page_size,
        batch_size_attribute='pageSize')
