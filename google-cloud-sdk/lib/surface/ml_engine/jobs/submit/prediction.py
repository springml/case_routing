# Copyright 2016 Google Inc. All Rights Reserved.
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
"""ml-engine jobs submit batch prediction command."""
from googlecloudsdk.api_lib.ml_engine import jobs
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.ml_engine import flags
from googlecloudsdk.command_lib.ml_engine import jobs_util

_TF_RECORD_URL = ('https://www.tensorflow.org/versions/r0.12/how_tos/'
                  'reading_data/index.html#file-formats')


def _AddSubmitPredictionArgs(parser):
  """Add arguments for `jobs submit prediction` command."""
  parser.add_argument('job', help='Name of the batch prediction job.')
  model_group = parser.add_mutually_exclusive_group(required=True)
  model_group.add_argument(
      '--model-dir',
      help=('Google Cloud Storage location where '
            'the model files are located.'))
  model_group.add_argument(
      '--model', help='Name of the model to use for prediction.')
  parser.add_argument(
      '--version',
      help="""\
Model version to be used.

This flag may only be given if --model is specified. If unspecified, the default
version of the model will be used. To list versions for a model, run

    $ gcloud ml-engine versions list
""")
  # input location is a repeated field.
  parser.add_argument(
      '--input-paths',
      type=arg_parsers.ArgList(min_length=1),
      required=True,
      metavar='INPUT_PATH',
      help="""\
Google Cloud Storage paths to the instances to run prediction on.

Wildcards (```*```) accepted at the *end* of a path. More than one path can be
specified if multiple file patterns are needed. For example,

  gs://my-bucket/instances*,gs://my-bucket/other-instances1

will match any objects whose names start with `instances` in `my-bucket` as well
as the `other-instances1` bucket, while

  gs://my-bucket/instance-dir/*

will match any objects in the `instance-dir` "directory" (since directories
aren't a first-class Cloud Storage concept) of `my-bucket`.
""")
  parser.add_argument(
      '--data-format',
      required=True,
      choices={
          'TEXT': ('Text files with instances separated by the new-line '
                   'character.'),
          'TF_RECORD': 'TFRecord files; see {}'.format(_TF_RECORD_URL),
          'TF_RECORD_GZIP': 'GZIP-compressed TFRecord files.'
      },
      help='Data format of the input files.')
  parser.add_argument(
      '--output-path', required=True,
      help='Google Cloud Storage path to which to save the output. '
      'Example: gs://my-bucket/output.')
  parser.add_argument(
      '--region',
      required=True,
      help='The Google Compute Engine region to run the job in.')
  parser.add_argument(
      '--max-worker-count',
      required=False,
      type=int,
      help=('The maximum number of workers to be used for parallel processing. '
            'Defaults to 10 if not specified.'))
  flags.RUNTIME_VERSION.AddToParser(parser)


class Prediction(base.Command):
  """Start a Cloud ML Engine batch prediction job."""

  @staticmethod
  def Args(parser):
    _AddSubmitPredictionArgs(parser)
    parser.display_info.AddFormat(jobs_util.JOB_FORMAT)

  def Run(self, args):
    return jobs_util.SubmitPrediction(
        jobs.JobsClient(), args.job,
        model_dir=args.model_dir,
        model=args.model,
        version=args.version,
        input_paths=args.input_paths,
        data_format=args.data_format,
        output_path=args.output_path,
        region=args.region,
        runtime_version=args.runtime_version,
        max_worker_count=args.max_worker_count)
