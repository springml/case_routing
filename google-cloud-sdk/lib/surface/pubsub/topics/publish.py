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
"""Cloud Pub/Sub topics publish command."""
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as sdk_ex
from googlecloudsdk.command_lib.pubsub import util
from googlecloudsdk.core.resource import resource_projector

MAX_ATTRIBUTES = 100


class Publish(base.Command):
  """Publishes a message to the specified topic.

  Publishes a message to the specified topic name for testing and
  troubleshooting. Use with caution: all associated subscribers must be
  able to consume and acknowledge any message you publish, otherwise the
  system will continuously re-attempt delivery of the bad message for 7 days.

  ## EXAMPLES

  To publish messages in a batch to a specific Cloud Pub/Sub topic,
  run:

    $ {command} mytopic "Hello World!" --attribute KEY1=VAL1,KEY2=VAL2
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""

    parser.add_argument('topic', help='Topic name to publish messages to.')
    parser.add_argument('message_body', nargs='?', default=None,
                        help=("""
The body of the message to publish to the given topic name.
Information on message formatting and size limits can be found at:
https://cloud.google.com/pubsub/docs/publisher#publish
"""))
    parser.add_argument('--attribute',
                        type=arg_parsers.ArgDict(max_length=MAX_ATTRIBUTES),
                        help=('Comma-separated list of attributes.'
                              ' Each ATTRIBUTE has the form "name=value".'
                              ' You can specify up to {0} attributes.'.format(
                                  MAX_ATTRIBUTES)))

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      PublishResponse with the response of the Publish operation.

    Raises:
      sdk_ex.HttpException: If attributes are malformed, or if none of
      MESSAGE_BODY or ATTRIBUTE are given.
    """
    msgs = self.context['pubsub_msgs']
    pubsub = self.context['pubsub']

    attributes = []
    if args.attribute:
      for key, value in sorted(args.attribute.iteritems()):
        attributes.append(
            msgs.PubsubMessage.AttributesValue.AdditionalProperty(
                key=key,
                value=value))

    if not args.message_body and not attributes:
      raise sdk_ex.HttpException(('You cannot send an empty message.'
                                  ' You must specify either a MESSAGE_BODY,'
                                  ' one or more ATTRIBUTE, or both.'))

    topic_name = args.topic

    message = msgs.PubsubMessage(
        data=args.message_body,
        attributes=msgs.PubsubMessage.AttributesValue(
            additionalProperties=attributes))

    result = pubsub.projects_topics.Publish(
        msgs.PubsubProjectsTopicsPublishRequest(
            publishRequest=msgs.PublishRequest(messages=[message]),
            topic=util.TopicFormat(topic_name)))

    if not result.messageIds:
      # If we got a result with empty messageIds, then we've got a problem.
      raise sdk_ex.HttpException('Publish operation failed with Unknown error.')

    # We only allow to publish one message at a time, so do not return a
    # list of messageId.
    resource = resource_projector.MakeSerializable(result)
    resource['messageIds'] = result.messageIds[0]
    return resource
