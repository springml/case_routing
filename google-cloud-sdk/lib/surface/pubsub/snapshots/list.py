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
"""Cloud Pub/Sub snapshots list command."""
import re
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as sdk_ex
from googlecloudsdk.command_lib.pubsub import util
from googlecloudsdk.core.resource import resource_printer_base
from googlecloudsdk.core.resource import resource_projector


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class List(base.ListCommand):
  """This feature is part of an invite-only release of the Cloud Pub/Sub API.

  Lists all the snapshots in a given project.
  This feature is part of an invitation-only release of the underlying
  Cloud Pub/Sub API. The command will generate errors unless you have access to
  this API. This restriction should be relaxed in the near future. Please
  contact cloud-pubsub@google.com with any questions in the meantime.
  """

  @staticmethod
  def Args(parser):
    parser.display_info.AddFormat("""
          table[box](
            projectId:label=PROJECT,
            snapshotId:label=SNAPSHOT,
            topicId:label=TOPIC,
            expireTime:label=EXPIRE_TIME
            )
        """)

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Yields:
      Snapshot paths that match the regular expression in args.name_filter.

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
        list_snapshots_req = msgs.PubsubProjectsSnapshotsListRequest(
            project=util.ProjectFormat(),
            pageToken=page_token,
            pageSize=page_size)

        list_snapshots_response = pubsub.projects_snapshots.List(
            list_snapshots_req)

        for snapshot in list_snapshots_response.snapshots:
          yield SnapshotDict(snapshot)

        page_token = list_snapshots_response.nextPageToken
        if not page_token:
          break
        yield resource_printer_base.PageMarker()

    except re.error as e:
      raise sdk_ex.HttpException(str(e))


def SnapshotDict(snapshot):
  """Returns a snapshot dict with additional fields."""
  result = resource_projector.MakeSerializable(snapshot)
  snapshot_info = util.SnapshotIdentifier(snapshot.name)
  result['projectId'] = snapshot_info.project.project_name
  result['snapshotId'] = snapshot_info.resource_name
  topic_info = util.TopicIdentifier(snapshot.topic)
  result['topicId'] = topic_info.resource_name
  result['expireTime'] = snapshot.expireTime
  return result
