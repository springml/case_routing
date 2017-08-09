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
"""Cloud Pub/Sub snapshots create command."""

from apitools.base.py import exceptions as api_ex

from googlecloudsdk.api_lib.util import exceptions
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.projects import util as projects_util
from googlecloudsdk.command_lib.pubsub import util
from googlecloudsdk.core import log


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class Create(base.CreateCommand):
  """This feature is part of an invite-only release of the Cloud Pub/Sub API.

  Creates one or more Cloud Pub/Sub snapshots.
  This feature is part of an invitation-only release of the underlying
  Cloud Pub/Sub API. The command will generate errors unless you have access to
  this API. This restriction should be relaxed in the near future. Please
  contact cloud-pubsub@google.com with any questions in the meantime.
  """

  @staticmethod
  def Args(parser):
    """Registers flags for this command."""

    parser.add_argument('snapshot', nargs='+',
                        help='One or more snapshot names to create.')

    parser.add_argument(
        '--subscription', required=True,
        help=('The subscription whose backlog the snapshot retains. '
              ' Specifically, the created snapshot is guaranteed to retain a)'
              ' The existing backlog on the subscription, i.e., the set of'
              ' messages in the subscription that are unacknowledged upon the'
              ' successful completion of the create snapshot request, b) Any'
              ' messages published to the subscription\'s topic following the'
              ' successful creation of the snapshot.'))

    parser.add_argument(
        '--subscription-project', default='',
        help=('The name of the project the provided subscription belongs to.'
              ' If not set, it defaults to the currently selected'
              ' cloud project.'))

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Yields:
      A serialized object (dict) describing the results of the operation.
      This description fits the Resource described in the ResourceRegistry under
      'pubsub.projects.snapshots'.
    """
    msgs = self.context['pubsub_msgs']
    pubsub = self.context['pubsub']

    subscription_project = ''
    if args.subscription_project:
      subscription_project = projects_util.ParseProject(
          args.subscription_project).Name()
    subscription_name = args.subscription

    for snapshot_name in args.snapshot:
      snapshot_path = util.SnapshotFormat(snapshot_name)
      create_req = msgs.PubsubProjectsSnapshotsCreateRequest(
          createSnapshotRequest=msgs.CreateSnapshotRequest(
              subscription=util.SubscriptionFormat(
                  subscription_name, subscription_project)),
          name=snapshot_path)

      # TODO(b/32275310): Conform to gcloud error handling guidelines.
      try:
        result = pubsub.projects_snapshots.Create(create_req)
        failed = None
      except api_ex.HttpError as error:
        result = msgs.Snapshot(name=snapshot_path)
        exc = exceptions.HttpException(error)
        failed = exc.payload.status_message

      result = util.SnapshotDisplayDict(result, failed)
      log.CreatedResource(snapshot_path, kind='snapshot', failed=failed)
      yield result
