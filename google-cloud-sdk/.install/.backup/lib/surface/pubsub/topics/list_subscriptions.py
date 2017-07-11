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
"""Cloud Pub/Sub topics list_subscriptions command."""
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.pubsub import util
from googlecloudsdk.core.resource import resource_printer_base
from googlecloudsdk.core.resource import resource_projector


class ListSubscriptions(base.ListCommand):
  """Lists Cloud Pub/Sub subscriptions from a given topic.

  Lists all of the Cloud Pub/Sub subscriptions attached to the given topic and
  that match the given filter.
  """

  detailed_help = {
      'EXAMPLES': """\
          To filter results by subscription name
          (ie. only show subscription 'mysubs'), run:

            $ {command} --topic mytopic --filter=subscriptionId:mysubs

          To combine multiple filters (with AND or OR), run:

            $ {command} --topic mytopic --filter="subscriptionId:mysubs1 AND subscriptionId:mysubs2"

          To filter subscriptions that match an expression:

            $ {command} --topic mytopic --filter="subscriptionId:subs_*"
          """,
  }

  @staticmethod
  def Args(parser):
    """Register flags for this command."""

    parser.add_argument(
        'topic',
        help=('The name of the topic to list subscriptions for.'))

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Yields:
      Subscriptions paths that match the regular expression in args.name_filter.
    """
    msgs = self.context['pubsub_msgs']
    pubsub = self.context['pubsub']

    page_size = None
    page_token = None

    if args.page_size:
      page_size = min(args.page_size, util.MAX_LIST_RESULTS)

    if not args.filter and args.limit:
      page_size = min(args.limit, page_size or util.MAX_LIST_RESULTS)

    while True:
      list_subscriptions_req = (
          msgs.PubsubProjectsTopicsSubscriptionsListRequest(
              topic=util.TopicFormat(args.topic),
              pageSize=page_size,
              pageToken=page_token))

      list_subscriptions_result = pubsub.projects_topics_subscriptions.List(
          list_subscriptions_req)

      for subscription in list_subscriptions_result.subscriptions:
        yield TopicSubscriptionDict(subscription)

      page_token = list_subscriptions_result.nextPageToken
      if not page_token:
        break

      yield resource_printer_base.PageMarker()


def TopicSubscriptionDict(topic_subscription):
  """Returns a topic_subscription dict with additional fields."""
  result = resource_projector.MakeSerializable(
      {'subscription': topic_subscription})

  subscription_info = util.SubscriptionIdentifier(topic_subscription)
  result['projectId'] = subscription_info.project.project_name
  result['subscriptionId'] = subscription_info.resource_name
  return result
