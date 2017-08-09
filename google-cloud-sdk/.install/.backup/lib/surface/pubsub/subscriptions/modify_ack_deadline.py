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
"""Cloud Pub/Sub subscription modify command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.pubsub import util


class ModifyAckDeadline(base.Command):
  """Modifies the ACK deadline for a specific Cloud Pub/Sub message.

  This method is useful to indicate that more time is needed to process a
  message by the subscriber, or to make the message available for
  redelivery if the processing was interrupted.
  """

  @staticmethod
  def Args(parser):
    """Registers flags for this command."""

    parser.add_argument('subscription',
                        help='Name of the subscription messages belong to.')
    parser.add_argument('ackid', nargs='+',
                        help=('One or more ACK_ID that identify the messages'
                              ' to modify the deadline for.'))
    parser.add_argument(
        '--ack-deadline', type=int, required=True,
        help=('The number of seconds the system will wait for a subscriber to'
              ' acknowledge receiving a message before re-attempting'
              ' delivery.'))

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      Display dictionary with information about the new ACK deadline seconds
      for the given subscription and ackId.
    """
    msgs = self.context['pubsub_msgs']
    pubsub = self.context['pubsub']

    subscription = util.SubscriptionFormat(args.subscription)
    mod_req = msgs.PubsubProjectsSubscriptionsModifyAckDeadlineRequest(
        modifyAckDeadlineRequest=msgs.ModifyAckDeadlineRequest(
            ackDeadlineSeconds=args.ack_deadline,
            ackIds=args.ackid),
        subscription=subscription)

    pubsub.projects_subscriptions.ModifyAckDeadline(mod_req)
    return {'subscriptionId': subscription,
            'ackId': args.ackid,
            'ackDeadlineSeconds': args.ack_deadline}
