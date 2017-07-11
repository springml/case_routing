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
"""Cloud Pub/Sub topics create command."""

from apitools.base.py import exceptions as api_ex

from googlecloudsdk.api_lib.util import exceptions
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.pubsub import util
from googlecloudsdk.core import log


class Create(base.CreateCommand):
  """Creates one or more Cloud Pub/Sub topics.

  Creates one or more Cloud Pub/Sub topics.

  ## EXAMPLES

  To create a Cloud Pub/Sub topic, run:

    $ {command} mytopic
  """

  @staticmethod
  def Args(parser):
    """Registers flags for this command."""
    parser.add_argument('topic', nargs='+',
                        help='One or more topic names to create.')

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

    for topic in args.topic:
      topic_name = topic
      topic = msgs.Topic(name=util.TopicFormat(topic_name))

      try:
        result = pubsub.projects_topics.Create(topic)
        failed = None
      except api_ex.HttpError as error:
        result = topic
        exc = exceptions.HttpException(error)
        failed = exc.payload.status_message

      result = util.TopicDisplayDict(result, failed)
      log.CreatedResource(topic_name, kind='topic', failed=failed)
      yield result
