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
"""Implementation of gcloud dataflow jobs run command.
"""

from googlecloudsdk.api_lib.dataflow import apis
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import properties


@base.ReleaseTracks(base.ReleaseTrack.BETA, base.ReleaseTrack.GA)
class Run(base.Command):
  """Runs a job from the specified path.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command.

    Args:
      parser: argparse.ArgumentParser to register arguments with.
    """
    parser.add_argument(
        'job_name',
        metavar='JOB_NAME',
        help='The unique name to assign to the job.')

    parser.add_argument(
        '--gcs-location',
        help='The location of the job template to run.',
        required=True)

    parser.add_argument(
        '--zone',
        type=arg_parsers.RegexpValidator(
            r'\w+-\w+\d-\w', 'must provide a valid zone'),
        help='The zone to run the workers in.')

    parser.add_argument(
        '--service-account-email',
        type=arg_parsers.RegexpValidator(
            r'.*@.*\..*', 'must provide a valid email address'),
        help='The service account to run the workers as.')

    parser.add_argument(
        '--max-workers',
        type=int,
        help='The maximum number of workers to run.')

    parser.add_argument(
        '--parameters',
        metavar='PARAMETERS',
        type=arg_parsers.ArgDict(),
        action=arg_parsers.UpdateAction,
        help='The parameters to pass to the job.')

  def Run(self, args):
    """Runs the command.

    Args:
      args: The arguments that were provided to this command invocation.

    Returns:
      A Job message.
    """
    if not args.gcs_location.startswith('gs://'):
      raise exceptions.ToolException("""\
--gcs-location must begin with 'gs://'.  Provided value was '{value}'.
""".format(value=args.gcs_location))
    job = apis.Templates.Create(
        project_id=properties.VALUES.core.project.Get(required=True),
        gcs_location=args.gcs_location,
        job_name=args.job_name,
        parameters=args.parameters,
        service_account_email=args.service_account_email,
        zone=args.zone,
        max_workers=args.max_workers)

    return job
