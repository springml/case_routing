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
"""Cloud Pub/Sub subscriptions list command."""
import re
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as sdk_ex
from googlecloudsdk.command_lib.pubsub import util
from googlecloudsdk.core.resource import resource_printer_base
from googlecloudsdk.core.resource import resource_projector


class List(base.ListCommand):
  """Lists Cloud Pub/Sub subscriptions.

  Lists all of the Cloud Pub/Sub subscriptions that exist in a given project.
  """

  @staticmethod
  def Args(parser):
    parser.display_info.AddFormat("""
          table[box](
            projectId:label=PROJECT,
            subscriptionId:label=SUBSCRIPTION,
            topicId:label=TOPIC,
            type,
            ackDeadlineSeconds:label=ACK_DEADLINE
          )
        """)

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Yields:
      Subscription paths that match the regular expression in args.name_filter.

    Raises:
      sdk_ex.HttpException if there is an error with the regular
      expression syntax.
    """
    msgs = self.context['pubsub_msgs']
    pubsub = self.context['pubsub']

    page_token = None
    if args.page_size:
      page_size = min(args.page_size, util.MAX_LIST_RESULTS)
    else:
      page_size = None
    if not args.filter and args.limit:
      page_size = min(args.limit, page_size or util.MAX_LIST_RESULTS)

    try:
      while True:
        list_subscriptions_req = msgs.PubsubProjectsSubscriptionsListRequest(
            project=util.ProjectFormat(),
            pageToken=page_token,
            pageSize=page_size)

        list_subscriptions_response = pubsub.projects_subscriptions.List(
            list_subscriptions_req)

        for subscription in list_subscriptions_response.subscriptions:
          yield SubscriptionDict(subscription)

        page_token = list_subscriptions_response.nextPageToken
        if not page_token:
          break
        yield resource_printer_base.PageMarker()

    except re.error as e:
      raise sdk_ex.HttpException(str(e))


def SubscriptionDict(subscription):
  """Returns a subscription dict with additional fields."""
  result = resource_projector.MakeSerializable(subscription)
  result['type'] = 'PUSH' if subscription.pushConfig.pushEndpoint else 'PULL'
  subscription_info = util.SubscriptionIdentifier(subscription.name)
  result['projectId'] = subscription_info.project.project_name
  result['subscriptionId'] = subscription_info.resource_name
  topic_info = util.TopicIdentifier(subscription.topic)
  result['topicId'] = topic_info.resource_name
  return result
