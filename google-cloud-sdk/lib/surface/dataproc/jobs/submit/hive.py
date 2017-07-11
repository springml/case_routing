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

"""Submit a Hive job to a cluster."""

from apitools.base.py import encoding

from googlecloudsdk.api_lib.dataproc import base_classes
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base


@base.ReleaseTracks(base.ReleaseTrack.GA)
class Hive(base_classes.JobSubmitter):
  """Submit a Hive job to a cluster.

  Submit a Hive job to a cluster.

  ## EXAMPLES

  To submit a Hive job with a local script, run:

    $ {command} --cluster my_cluster --file my_queries.q

  To submit a Hive job with inline queries, run:

    $ {command} --cluster my_cluster -e "CREATE EXTERNAL TABLE foo(bar int) LOCATION 'gs://my_bucket/'" -e "SELECT * FROM foo WHERE bar > 2"
  """

  @staticmethod
  def Args(parser):
    super(Hive, Hive).Args(parser)
    HiveBase.Args(parser)

  def ConfigureJob(self, messages, job, args):
    HiveBase.ConfigureJob(
        messages,
        job,
        self.files_by_type,
        args)
    super(Hive, self).ConfigureJob(messages, job, args)

  def PopulateFilesByType(self, args):
    self.files_by_type.update(HiveBase.GetFilesByType(args))


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class HiveBeta(base_classes.JobSubmitterBeta):
  """Submit a Hive job to a cluster.

  Submit a Hive job to a cluster.

  ## EXAMPLES

  To submit a Hive job with a local script, run:

    $ {command} --cluster my_cluster --file my_queries.q

  To submit a Hive job with inline queries, run:

    $ {command} --cluster my_cluster -e "CREATE EXTERNAL TABLE foo(bar int) LOCATION 'gs://my_bucket/'" -e "SELECT * FROM foo WHERE bar > 2"
  """

  @staticmethod
  def Args(parser):
    """Parses commannd-line arguments specific to the beta release."""
    super(HiveBeta, HiveBeta).Args(parser)
    HiveBase.Args(parser)

  def ConfigureJob(self, messages, job, args):
    HiveBase.ConfigureJob(
        messages,
        job,
        self.files_by_type,
        args)
    super(HiveBeta, self).ConfigureJob(messages, job, args)

  def PopulateFilesByType(self, args):
    self.files_by_type.update(HiveBase.GetFilesByType(args))


class HiveBase(object):
  """Common functionality between release tracks."""

  @staticmethod
  def Args(parser):
    """Performs command line parsing specific to Hive."""
    driver = parser.add_mutually_exclusive_group(required=True)
    driver.add_argument(
        '--execute', '-e',
        metavar='QUERY',
        dest='queries',
        action='append',
        default=[],
        help='A Hive query to execute as part of the job.')
    driver.add_argument(
        '--file', '-f',
        help='HCFS URI of file containing Hive script to execute as the job.')
    parser.add_argument(
        '--jars',
        type=arg_parsers.ArgList(),
        metavar='JAR',
        default=[],
        help=('Comma separated list of jar files to be provided to the '
              'Hive and MR. May contain UDFs.'))
    parser.add_argument(
        '--params',
        type=arg_parsers.ArgDict(),
        metavar='PARAM=VALUE',
        help='A list of key value pairs to set variables in the Hive queries.')
    parser.add_argument(
        '--properties',
        type=arg_parsers.ArgDict(),
        metavar='PROPERTY=VALUE',
        help='A list of key value pairs to configure Hive.')
    parser.add_argument(
        '--continue-on-failure',
        action='store_true',
        help='Whether to continue if a single query fails.')

  @staticmethod
  def GetFilesByType(args):
    return {
        'jars': args.jars,
        'file': args.file}

  @staticmethod
  def ConfigureJob(messages, job, files_by_type, args):
    """Populates the hiveJob member of the given job."""

    hive_job = messages.HiveJob(
        continueOnFailure=args.continue_on_failure,
        jarFileUris=files_by_type['jars'],
        queryFileUri=files_by_type['file'])

    if args.queries:
      hive_job.queryList = messages.QueryList(queries=args.queries)
    if args.params:
      hive_job.scriptVariables = encoding.DictToMessage(
          args.params, messages.HiveJob.ScriptVariablesValue)
    if args.properties:
      hive_job.properties = encoding.DictToMessage(
          args.properties, messages.HiveJob.PropertiesValue)

    job.hiveJob = hive_job
