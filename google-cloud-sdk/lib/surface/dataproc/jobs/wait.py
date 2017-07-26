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

"""Wait for a job to complete."""

from googlecloudsdk.api_lib.dataproc import dataproc as dp
from googlecloudsdk.api_lib.dataproc import util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log


class Wait(base.Command):
  """View the output of a job as it runs or after it completes.

  View the output of a job as it runs or after it completes.

  ## EXAMPLES

  To view the output of a job as it runs, run:

    $ {command} job_id
  """

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'id',
        metavar='JOB_ID',
        help='The ID of the job to wait.')

  def Run(self, args):
    dataproc = dp.Dataproc(self.ReleaseTrack())

    job_ref = util.ParseJob(args.id, dataproc)

    job = dataproc.client.projects_regions_jobs.Get(
        dataproc.messages.DataprocProjectsRegionsJobsGetRequest(
            projectId=job_ref.projectId,
            region=job_ref.region,
            jobId=job_ref.jobId))

    # TODO(b/36050945) Check if Job is still running and fail or handle 401.

    job = util.WaitForJobTermination(
        dataproc,
        job,
        message='Waiting for job completion',
        goal_state=dataproc.messages.JobStatus.StateValueValuesEnum.DONE,
        stream_driver_log=True)

    log.status.Print('Job [{0}] finished successfully.'.format(args.id))

    return job
