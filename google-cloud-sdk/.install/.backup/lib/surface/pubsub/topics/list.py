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
"""Cloud Pub/Sub topics list command."""
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.pubsub import util
from googlecloudsdk.core.resource import resource_printer_base
from googlecloudsdk.core.resource import resource_projector


class List(base.ListCommand):
  """Lists Cloud Pub/Sub topics within a project.

  Lists all of the Cloud Pub/Sub topics that exist in a given project that
  match the given topic name filter.
  """

  detailed_help = {
      'EXAMPLES': """\
          To filter results by topic name (ie. only show topic 'mytopic'), run:

            $ {command} --filter=topicId:mytopic

          To combine multiple filters (with AND or OR), run:

            $ {command} --filter="topicId:mytopic AND topicId:myothertopic"

          To filter topics that match an expression:

            $ {command} --filter="topicId:mytopic_*"
          """,
  }

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Yields:
      Topic paths that match the regular expression in args.name_filter.
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
      list_topics_request = msgs.PubsubProjectsTopicsListRequest(
          project=util.ProjectFormat(),
          pageToken=page_token,
          pageSize=page_size)

      list_topics_response = pubsub.projects_topics.List(
          list_topics_request)

      for topic in list_topics_response.topics:
        yield TopicDict(topic)

      page_token = list_topics_response.nextPageToken
      if not page_token:
        break
      yield resource_printer_base.PageMarker()


def TopicDict(topic):
  topic_dict = resource_projector.MakeSerializable(topic)
  topic_info = util.TopicIdentifier(topic.name)
  topic_dict['topic'] = topic.name
  topic_dict['topicId'] = topic_info.resource_name
  del topic_dict['name']
  return topic_dict
