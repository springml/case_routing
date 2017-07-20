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
"""Command to add denied values to an Organization Policy list policy."""

from googlecloudsdk.api_lib.resource_manager import exceptions
from googlecloudsdk.api_lib.resource_manager import org_policies
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.resource_manager import org_policies_base
from googlecloudsdk.command_lib.resource_manager import org_policies_flags as flags


@base.ReleaseTracks(base.ReleaseTrack.ALPHA, base.ReleaseTrack.BETA)
class Deny(base.Command):
  r"""Add values to an Organization Policy denied_values list policy.

  Adds one or more values to the specified Organization Policy denied_values
  list policy associated with the specified resource.

  ## EXAMPLES

  The following command adds `devEnv` and `prodEnv` to an Organization Policy
  denied_values list policy for constraint `serviceuser.services`
  on project `foo-project`:

    $ {command} serviceuser.services --project=foo-project devEnv prodEnv
  """

  @staticmethod
  def Args(parser):
    flags.AddIdArgToParser(parser)
    flags.AddResourceFlagsToParser(parser)
    base.Argument(
        'denied_value', metavar='DENIED_VALUE', nargs='+').AddToParser(parser)

  def Run(self, args):
    flags.CheckResourceFlags(args)
    messages = org_policies.OrgPoliciesMessages()
    service = org_policies_base.OrgPoliciesService(args)

    policy = service.GetOrgPolicy(org_policies_base.GetOrgPolicyRequest(args))

    if policy.booleanPolicy or (
        policy.listPolicy and
        (policy.listPolicy.allowedValues or policy.listPolicy.allValues)):
      raise exceptions.ResourceManagerError(
          'Cannot add values to a non-denied_values list policy.')

    if policy.listPolicy and policy.listPolicy.deniedValues:
      for value in args.denied_value:
        policy.listPolicy.deniedValues.append(unicode(value))
    else:
      policy.listPolicy = messages.ListPolicy(deniedValues=args.denied_value)

    return service.SetOrgPolicy(
        org_policies_base.SetOrgPolicyRequest(args, policy))
