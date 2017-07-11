# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Cloud Pub/Sub subscriptions seek command."""

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.projects import util as projects_util
from googlecloudsdk.command_lib.pubsub import util


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class SeekAlpha(base.Command):
  """This feature is part of an invite-only release of the Cloud Pub/Sub API.

  Resets a subscription's backlog to a point in time or to a given snapshot.
  This feature is part of an invitation-only release of the underlying
  Cloud Pub/Sub API. The command will generate errors unless you have access to
  this API. This restriction should be relaxed in the near future. Please
  contact cloud-pubsub@google.com with any questions in the meantime.
  """

  @staticmethod
  def Args(parser):
    """Registers flags for this command."""

    parser.add_argument('subscription',
                        help='Name of the subscription to affect.')

    seek_to_parser = parser.add_mutually_exclusive_group(required=True)
    seek_to_parser.add_argument(
        '--time', type=arg_parsers.Datetime.Parse,
        help=('The time to seek to. Messages in the subscription that '
              'were published before this time are marked as acknowledged, and '
              'messages retained in the subscription that were published after '
              'this time are marked as unacknowledged. See `gcloud topic '
              'datetimes` for information on time formats.'))
    seek_to_parser.add_argument(
        '--snapshot',
        help=('The name of the snapshot. The snapshot\'s topic must be the same'
              ' as that of the subscription.'))
    parser.add_argument(
        '--snapshot-project', default='',
        help=('The name of the project the snapshot belongs to (if seeking to '
              'a snapshot). If not set, it defaults to the currently selected '
              'cloud project.'))

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      A serialized object (dict) describing the results of the operation.  This
      description fits the Resource described in the ResourceRegistry under
      'pubsub.subscriptions.seek'.
    """
    msgs = self.context['pubsub_msgs']
    pubsub = self.context['pubsub']

    subscription_path = util.SubscriptionFormat(args.subscription)
    result = {'subscriptionId': subscription_path}

    seek_req = msgs.SeekRequest()
    if args.snapshot:
      if args.snapshot_project:
        snapshot_project = (
            projects_util.ParseProject(args.snapshot_project).Name())
      else:
        snapshot_project = ''
      seek_req.snapshot = util.SnapshotFormat(args.snapshot, snapshot_project)
      result['snapshotId'] = seek_req.snapshot
    else:
      seek_req.time = args.time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
      result['time'] = seek_req.time

    pubsub.projects_subscriptions.Seek(
        msgs.PubsubProjectsSubscriptionsSeekRequest(
            seekRequest=seek_req, subscription=subscription_path))

    return result
