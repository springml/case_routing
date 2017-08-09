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

"""Implementation of gcloud dataflow jobs list command.
"""

from googlecloudsdk.api_lib.dataflow import apis
from googlecloudsdk.api_lib.dataflow import job_display
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.dataflow import dataflow_util
from googlecloudsdk.command_lib.dataflow import time_util
from googlecloudsdk.core import properties


@base.ReleaseTracks(base.ReleaseTrack.BETA, base.ReleaseTrack.GA)
class List(base.ListCommand):
  """Lists all jobs in a particular project.

  By default, 100 jobs in the current project are listed; this can be overridden
  with the gcloud --project flag, and the --limit flag.

  ## EXAMPLES

  Filter jobs with the given name:

    $ {command} --filter="name=my-wordcount"

  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""

    base.ASYNC_FLAG.RemoveFromParser(parser)
    # Set manageable limits on number of jobs that are listed.
    base.LIMIT_FLAG.SetDefault(parser, 100)
    base.PAGE_SIZE_FLAG.SetDefault(parser, 20)

    # Flags for filtering jobs.
    parser.add_argument(
        '--status',
        choices={
            'all': (
                'Returns running jobs first, ordered on creation timestamp, '
                'then, returns all terminated jobs ordered on the termination '
                'timestamp.'),
            'terminated': (
                'Filters the jobs that have a terminated state, ordered on '
                'the termination timestamp. Example terminated states: Done, '
                'Updated, Cancelled, etc.'),
            'active': (
                'Filters the jobs that are running ordered on the creation '
                'timestamp.'),
        },
        help='Filter the jobs to those with the selected status.')
    parser.add_argument(
        '--created-after', type=time_util.ParseTimeArg,
        help='Filter the jobs to those created after the given time')
    parser.add_argument(
        '--created-before', type=time_util.ParseTimeArg,
        help='Filter the jobs to those created before the given time')
    parser.display_info.AddFormat("""
          table(
            id:label=JOB_ID,
            name:label=NAME,
            type:label=TYPE,
            creationTime.yesno(no="-"),
            state
          )
     """)
    parser.display_info.AddUriFunc(dataflow_util.JobsUriFunc)

  def Run(self, args):
    """Runs the command.

    Args:
      args: All the arguments that were provided to this command invocation.

    Returns:
      An iterator over Job messages.
    """
    filter_pred = _JobFilter(args)
    project_id = properties.VALUES.core.project.Get(required=True)
    jobs = self._JobSummariesForProject(project_id, args, filter_pred)

    return [job_display.DisplayInfo(job) for job in jobs]

  def _JobSummariesForProject(self, project_id, args, filter_predicate):
    """Get the list of job summaries that match the predicate.

    Args:
      project_id: The project ID to retrieve
      args: parsed command line arguments
      filter_predicate: The filter predicate to apply

    Returns:
      An iterator over all the matching jobs.
    """
    request = apis.Jobs.LIST_REQUEST(
        projectId=project_id, filter=self._StatusArgToFilter(args.status))

    return dataflow_util.YieldFromList(
        project_id=project_id,
        service=apis.Jobs.GetService(),
        request=request,
        limit=args.limit,
        batch_size=args.page_size,
        field='jobs',
        batch_size_attribute='pageSize',
        predicate=filter_predicate)

  def _StatusArgToFilter(self, status):
    """Return a string describing the job status.

    Args:
      status: The job status enum
    Returns:
      string describing the job status
    """
    filter_value_enum = (
        apis.GetMessagesModule().DataflowProjectsJobsListRequest
        .FilterValueValuesEnum)
    value_map = {
        'all': filter_value_enum.ALL,
        'terminated': filter_value_enum.TERMINATED,
        'active': filter_value_enum.ACTIVE,
    }
    return value_map.get(status, filter_value_enum.ALL)


class _JobFilter(object):
  """Predicate for filtering jobs.
  """

  def __init__(self, args):
    """Create a _JobFilter from the given args.

    Args:
      args: The argparse.Namespace containing the parsed arguments.
    """
    self.preds = []
    if args.created_after or args.created_before:
      self._ParseTimePredicate(args.created_after, args.created_before)

  def __call__(self, job):
    return all([pred(job) for pred in self.preds])

  def _ParseTimePredicate(self, after, before):
    """Return a predicate for filtering jobs by their creation time.

    Args:
      after: Only return true if the job was created after this time.
      before: Only return true if the job was created before this time.

    """
    if after and (not before):
      self.preds.append(lambda x: time_util.Strptime(x.createTime) > after)
    elif (not after) and before:
      self.preds.append(lambda x: time_util.Strptime(x.createTime) <= before)
    elif after and before:
      def _Predicate(x):
        create_time = time_util.Strptime(x.createTime)
        return after < create_time and create_time <= before
      self.preds.append(_Predicate)
