# Copyright 2014 Google Inc. All Rights Reserved.
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

"""gcloud dns record-sets command group."""

from googlecloudsdk.calliope import base


class RecordSets(base.Group):
  """Manage the record-sets within your managed-zones.

  Manage the record-sets within your managed-zones.

  ## EXAMPLES

  To import record-sets from a BIND zone file, run:

    $ {command} import --zone MANAGED_ZONE --zone-file-format ZONE_FILE

  To export record-sets in yaml format, run:

    $ {command} export --zone MANAGED_ZONE

  To see how to make scriptable changes to your record-sets through
  transactions, run:

    $ {command} transaction --zone MANAGED_ZONE

  To see change details or list of all changes, run:

    $ {command} changes --zone MANAGED_ZONE

  To see the list of all record-sets, run:

    $ {command} list --zone MANAGED_ZONE
  """
  pass
