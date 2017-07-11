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
"""Command to update labels for forwarding-rules."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute.operations import poller
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.command_lib.compute import flags as compute_flags
from googlecloudsdk.command_lib.compute.forwarding_rules import flags
from googlecloudsdk.command_lib.util import labels_util


@base.ReleaseTracks(base.ReleaseTrack.ALPHA, base.ReleaseTrack.BETA)
class Update(base.UpdateCommand):
  r"""Update a Google Compute Engine forwarding rule.

  *{command}* updates labels for a Google Compute Engine
  forwarding rule.  For example:

    $ {command} example-fr --region us-central1 \
      --update-labels=k0=value1,k1=value2 --remove-labels=k3

  will add/update labels ``k0'' and ``k1'' and remove labels with key ``k3''.

  Labels can be used to identify the forwarding rule and to filter them as in

    $ {parent_command} list --filter='labels.k1:value2'

  To list existing labels

    $ {parent_command} describe example-fr --format='default(labels)'

  """

  FORWARDING_RULE_ARG = None

  @classmethod
  def Args(cls, parser):
    cls.FORWARDING_RULE_ARG = flags.ForwardingRuleArgument()
    cls.FORWARDING_RULE_ARG.AddArgument(parser)
    labels_util.AddUpdateLabelsFlags(parser)

  def Run(self, args):
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    client = holder.client.apitools_client
    messages = holder.client.messages

    forwarding_rule_ref = self.FORWARDING_RULE_ARG.ResolveAsResource(
        args,
        holder.resources,
        scope_lister=compute_flags.GetDefaultScopeLister(holder.client))

    update_labels = labels_util.GetUpdateLabelsDictFromArgs(args)
    remove_labels = labels_util.GetRemoveLabelsListFromArgs(args)
    if update_labels is None and remove_labels is None:
      raise calliope_exceptions.RequiredArgumentException(
          'LABELS', 'At least one of --update-labels or '
          '--remove-labels must be specified.')

    if forwarding_rule_ref.Collection() == 'compute.globalForwardingRules':
      forwarding_rule = client.globalForwardingRules.Get(
          messages.ComputeGlobalForwardingRulesGetRequest(
              **forwarding_rule_ref.AsDict()))
      labels_value = messages.GlobalSetLabelsRequest.LabelsValue
    else:
      forwarding_rule = client.forwardingRules.Get(
          messages.ComputeForwardingRulesGetRequest(
              **forwarding_rule_ref.AsDict()))
      labels_value = messages.RegionSetLabelsRequest.LabelsValue

    replacement = labels_util.UpdateLabels(
        forwarding_rule.labels,
        labels_value,
        update_labels=update_labels,
        remove_labels=remove_labels)

    if not replacement:
      return forwarding_rule

    if forwarding_rule_ref.Collection() == 'compute.globalForwardingRules':
      request = messages.ComputeGlobalForwardingRulesSetLabelsRequest(
          project=forwarding_rule_ref.project,
          resource=forwarding_rule_ref.Name(),
          globalSetLabelsRequest=messages.GlobalSetLabelsRequest(
              labelFingerprint=forwarding_rule.labelFingerprint,
              labels=replacement))

      operation = client.globalForwardingRules.SetLabels(request)
      operation_ref = holder.resources.Parse(
          operation.selfLink, collection='compute.globalOperations')

      operation_poller = poller.Poller(client.globalForwardingRules)
    else:
      request = messages.ComputeForwardingRulesSetLabelsRequest(
          project=forwarding_rule_ref.project,
          resource=forwarding_rule_ref.Name(),
          region=forwarding_rule_ref.region,
          regionSetLabelsRequest=messages.RegionSetLabelsRequest(
              labelFingerprint=forwarding_rule.labelFingerprint,
              labels=replacement))

      operation = client.forwardingRules.SetLabels(request)
      operation_ref = holder.resources.Parse(
          operation.selfLink, collection='compute.regionOperations')

      operation_poller = poller.Poller(client.forwardingRules)

    return waiter.WaitFor(operation_poller, operation_ref,
                          'Updating labels of forwarding rule [{0}]'.format(
                              forwarding_rule_ref.Name()))
