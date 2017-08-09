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

"""Submit a Spark SQL job to a cluster."""

from apitools.base.py import encoding

from googlecloudsdk.api_lib.dataproc import base_classes
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base


@base.ReleaseTracks(base.ReleaseTrack.GA)
class SparkSql(base_classes.JobSubmitter):
  """Submit a Spark SQL job to a cluster.

  Submit a Spark SQL job to a cluster.

  ## EXAMPLES

  To submit a Spark SQL job with a local script, run:

    $ {command} --cluster my_cluster --file my_queries.ql

  To submit a Spark SQL job with inline queries, run:

    $ {command} --cluster my_cluster -e "CREATE EXTERNAL TABLE foo(bar int) LOCATION 'gs://my_bucket/'" -e "SELECT * FROM foo WHERE bar > 2"
  """

  @staticmethod
  def Args(parser):
    super(SparkSql, SparkSql).Args(parser)
    SparkSqlBase.Args(parser)

  def ConfigureJob(self, messages, job, args):
    SparkSqlBase.ConfigureJob(
        messages,
        job,
        self.BuildLoggingConfig(messages, args.driver_log_levels),
        self.files_by_type,
        args)
    super(SparkSql, self).ConfigureJob(messages, job, args)

  def PopulateFilesByType(self, args):
    self.files_by_type.update(SparkSqlBase.GetFilesByType(args))


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class SparkSqlBeta(base_classes.JobSubmitterBeta):
  """Submit a Spark SQL job to a cluster.

  Submit a Spark SQL job to a cluster.

  ## EXAMPLES

  To submit a Spark SQL job with a local script, run:

    $ {command} --cluster my_cluster --file my_queries.ql

  To submit a Spark SQL job with inline queries, run:

    $ {command} --cluster my_cluster -e "CREATE EXTERNAL TABLE foo(bar int) LOCATION 'gs://my_bucket/'" -e "SELECT * FROM foo WHERE bar > 2"
  """

  @staticmethod
  def Args(parser):
    super(SparkSqlBeta, SparkSqlBeta).Args(parser)
    SparkSqlBase.Args(parser)

  def ConfigureJob(self, messages, job, args):
    SparkSqlBase.ConfigureJob(
        messages,
        job,
        self.BuildLoggingConfig(messages, args.driver_log_levels),
        self.files_by_type,
        args)
    super(SparkSqlBeta, self).ConfigureJob(messages, job, args)

  def PopulateFilesByType(self, args):
    self.files_by_type.update(SparkSqlBase.GetFilesByType(args))


class SparkSqlBase(object):
  """Submit a Spark SQL job to a cluster."""

  @staticmethod
  def Args(parser):
    """Parses command-line arguments specific to submitting SparkSql jobs."""
    driver = parser.add_mutually_exclusive_group(required=True)
    driver.add_argument(
        '--execute', '-e',
        metavar='QUERY',
        dest='queries',
        action='append',
        default=[],
        help='A Spark SQL query to execute as part of the job.')
    driver.add_argument(
        '--file', '-f',
        help=('HCFS URI of file containing Spark SQL script to execute as '
              'the job.'))
    parser.add_argument(
        '--jars',
        type=arg_parsers.ArgList(),
        metavar='JAR',
        default=[],
        help=('Comma separated list of jar files to be provided to the '
              'executor and driver classpaths. May contain UDFs.'))
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
        '--driver-log-levels',
        type=arg_parsers.ArgDict(),
        metavar='PACKAGE=LEVEL',
        help=('A list of package to log4j log level pairs to configure driver '
              'logging. For example: root=FATAL,com.example=INFO'))

  @staticmethod
  def GetFilesByType(args):
    return {
        'jars': args.jars,
        'file': args.file}

  @staticmethod
  def ConfigureJob(messages, job, log_config, files_by_type, args):
    """Populates the sparkSqlJob member of the given job."""

    spark_sql_job = messages.SparkSqlJob(
        jarFileUris=files_by_type['jars'],
        queryFileUri=files_by_type['file'],
        loggingConfig=log_config)

    if args.queries:
      spark_sql_job.queryList = messages.QueryList(queries=args.queries)
    if args.params:
      spark_sql_job.scriptVariables = encoding.DictToMessage(
          args.params, messages.SparkSqlJob.ScriptVariablesValue)
    if args.properties:
      spark_sql_job.properties = encoding.DictToMessage(
          args.properties, messages.SparkSqlJob.PropertiesValue)

    job.sparkSqlJob = spark_sql_job
