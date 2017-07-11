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
"""Cloud Pub/Sub subscription pull command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.pubsub import util


class Pull(base.ListCommand):
  """Pulls one or more Cloud Pub/Sub messages from a subscription.

  Returns one or more messages from the specified Cloud Pub/Sub subscription,
  if there are any messages enqueued.
  """

  @staticmethod
  def Args(parser):
    """Registers flags for this command."""

    parser.add_argument('subscription',
                        help='Name of subscription to pull messages from.')
    parser.add_argument(
        '--max-messages', type=int, default=1,
        help=('The maximum number of messages that Cloud Pub/Sub can return'
              ' in this response.'))
    parser.add_argument(
        '--auto-ack', action='store_true', default=False,
        help=('Automatically ACK every message pulled from this subscription.'))
    parser.display_info.AddFormat("""
          table[box](
            message.data.decode(base64),
            message.messageId,
            message.attributes.list(separator=' '),
            ackId.if(NOT auto_ack)
          )
        """)

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      A PullResponse message with the response of the Pull operation.
    """
    msgs = self.context['pubsub_msgs']
    pubsub = self.context['pubsub']

    subscription = util.SubscriptionFormat(args.subscription)
    pull_req = msgs.PubsubProjectsSubscriptionsPullRequest(
        pullRequest=msgs.PullRequest(
            maxMessages=args.max_messages, returnImmediately=True),
        subscription=subscription)

    pull_response = pubsub.projects_subscriptions.Pull(pull_req)

    if args.auto_ack and pull_response.receivedMessages:
      ack_ids = [message.ackId for message in pull_response.receivedMessages]

      ack_req = msgs.PubsubProjectsSubscriptionsAcknowledgeRequest(
          acknowledgeRequest=msgs.AcknowledgeRequest(ackIds=ack_ids),
          subscription=subscription)
      pubsub.projects_subscriptions.Acknowledge(ack_req)

    return pull_response.receivedMessages
