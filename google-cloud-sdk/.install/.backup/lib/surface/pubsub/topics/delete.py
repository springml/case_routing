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
"""Cloud Pub/Sub topics delete command."""

from apitools.base.py import exceptions as api_ex

from googlecloudsdk.api_lib.util import exceptions
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.pubsub import util
from googlecloudsdk.core import log


class Delete(base.DeleteCommand):
  """Deletes one or more Cloud Pub/Sub topics.

  Deletes one or more Cloud Pub/Sub topics.

  ## EXAMPLES

  To delete a Cloud Pub/Sub topic, run:

      $ {command} mytopic
  """

  @staticmethod
  def Args(parser):
    parser.add_argument('topic', nargs='+',
                        help='One or more topic names to delete.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Yields:
      A serialized object (dict) describing the results of the operation.
      This description fits the Resource described in the ResourceRegistry under
      'pubsub.projects.topics'.
    """
    msgs = self.context['pubsub_msgs']
    pubsub = self.context['pubsub']

    for topic_name in args.topic:
      topic = msgs.Topic(name=util.TopicFormat(topic_name))
      delete_req = msgs.PubsubProjectsTopicsDeleteRequest(
          topic=util.TopicFormat(topic.name))

      try:
        pubsub.projects_topics.Delete(delete_req)
        failed = None
      except api_ex.HttpError as error:
        exc = exceptions.HttpException(error)
        failed = exc.payload.status_message

      result = util.TopicDisplayDict(topic, failed)
      log.DeletedResource(topic.name, kind='topic', failed=failed)
      yield result
