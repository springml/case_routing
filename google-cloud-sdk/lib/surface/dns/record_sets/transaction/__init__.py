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

"""gcloud dns record-sets transaction command group."""

from googlecloudsdk.api_lib.dns import transaction_util
from googlecloudsdk.calliope import base


class Transaction(base.Group):
  """Make scriptable and transactional changes to your record-sets.

  Make scriptable and transactional changes to your record-sets.

  ## EXAMPLES

  To start a transaction, run:

    $ {command} start

  To append a record-set addition to the transaction, run:

    $ {command} add --name RECORD_SET_NAME --ttl TTL --type TYPE DATA

  To append a record-set removal to the transaction, run:

    $ {command} remove --name RECORD_SET_NAME --ttl TTL --type TYPE DATA

  To look at the details of the transaction, run:

    $ {command} describe

  To delete the transaction, run:

    $ {command} abort

  To execute the transaction, run:

    $ {command} execute
  """

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--transaction-file',
        default=transaction_util.DEFAULT_PATH,
        help='Path of the file which contains the transaction.')
