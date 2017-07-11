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
"""Command to set an OrgPolicy."""

from googlecloudsdk.api_lib.resource_manager import org_policies
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.resource_manager import org_policies_base
from googlecloudsdk.command_lib.resource_manager import org_policies_flags as flags


@base.Hidden
@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class SetPolicy(base.DescribeCommand):
  """Set OrgPolicy.

  Sets an OrgPolicy associated with the specified resource from
  a file that contains the JSON or YAML encoded OrgPolicy.

  ## EXAMPLES

  The following command sets an OrgPolicy for a constraint
  on project `foo-project` from file `/tmp/policy.yaml`:

    $ {command} --project=foo-project /tmp/policy.yaml
  """

  @staticmethod
  def Args(parser):
    flags.AddResourceFlagsToParser(parser)
    base.Argument(
        'policy_file',
        help='JSON or YAML file with the OrgPolicy.').AddToParser(parser)

  def Run(self, args):
    flags.CheckResourceFlags(args)
    service = org_policies_base.OrgPoliciesService(args)
    messages = org_policies.OrgPoliciesMessages()

    return service.SetOrgPolicy(
        org_policies_base.SetOrgPolicyRequest(args,
                                              org_policies.GetFileAsMessage(
                                                  args.policy_file,
                                                  messages.OrgPolicy)))
