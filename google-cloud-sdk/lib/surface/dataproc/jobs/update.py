# Copyright 2017 Google Inc. All Rights Reserved.
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

"""Update job command."""

from googlecloudsdk.api_lib.dataproc import dataproc as dp
from googlecloudsdk.api_lib.dataproc import exceptions
from googlecloudsdk.api_lib.dataproc import util
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.util import labels_util
from googlecloudsdk.core import log


class Update(base.UpdateCommand):
  """Update the labels for a job.

  Update the labels for a job.

  ## EXAMPLES

  To add the label 'customer=acme' to a job , run:

    $ {command} job_id --update-labels=customer=acme

  To update the label 'customer=ackme' to 'customer=acme', run:

    $ {command} job_id --update-labels=customer=acme

  To remove the label whose key is 'customer', run:

    $ {command} job_id --remove-labels=customer
  """

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'id',
        metavar='JOB_ID',
        help='The ID of the job to describe.')
    # Allow the user to specify new labels as well as update/remove existing
    labels_util.AddUpdateLabelsFlags(parser)

  def Run(self, args):
    dataproc = dp.Dataproc(self.ReleaseTrack())

    job_ref = util.ParseJob(args.id, dataproc)

    changed_fields = []

    has_changes = False

    # Update labels if the user requested it
    labels = None
    if args.update_labels or args.remove_labels:
      has_changes = True
      changed_fields.append('labels')

      # We need to fetch the job first so we know what the labels look like. The
      # labels_util.UpdateLabels will fill out the proto for us with all the
      # updates and removals, but first we need to provide the current state
      # of the labels
      orig_job = dataproc.client.projects_regions_jobs.Get(
          dataproc.messages.DataprocProjectsRegionsJobsGetRequest(
              projectId=job_ref.projectId,
              region=job_ref.region,
              jobId=job_ref.jobId))

      labels = labels_util.UpdateLabels(
          orig_job.labels,
          dataproc.messages.Job.LabelsValue,
          args.update_labels,
          args.remove_labels)

    if not has_changes:
      raise exceptions.ArgumentError(
          'Must specify at least one job parameter to update.')

    updated_job = orig_job
    updated_job.labels = labels
    request = dataproc.messages.DataprocProjectsRegionsJobsPatchRequest(
        projectId=job_ref.projectId,
        region=job_ref.region,
        jobId=job_ref.jobId,
        job=updated_job,
        updateMask=','.join(changed_fields))

    returned_job = dataproc.client.projects_regions_jobs.Patch(request)

    log.UpdatedResource(returned_job)
    return returned_job
