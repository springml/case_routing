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

"""The main command group for Cloud Pub/Sub.

Everything under here will be the commands in your group.  Each file results in
a command with that name.

This module contains a single class that extends base.Group.  Calliope will
dynamically search for the implementing class and use that as the command group
for this command tree.  You can implement methods in this class to override some
of the default behavior.
"""

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base


@base.ReleaseTracks(base.ReleaseTrack.ALPHA, base.ReleaseTrack.BETA)
class Pubsub(base.Group):
  """Manage Cloud Pub/Sub topics and subscriptions."""

  def Filter(self, context, args):
    """Modify the context that will be given to this group's commands when run.

    The context is a dictionary into which you can insert whatever you like.
    The context is given to each command under this group.  You can do common
    initialization here and insert it into the context for later use.  Of course
    you can also do common initialization as a function that can be called in a
    library.

    Args:
      context: {str:object}, A set of key-value pairs that can be used for
          common initialization among commands.
      args: argparse.Namespace: The same namespace given to the corresponding
          .Run() invocation.
    """
    context['pubsub_msgs'] = apis.GetMessagesModule('pubsub', 'v1')
    context['pubsub'] = apis.GetClientInstance('pubsub', 'v1')
