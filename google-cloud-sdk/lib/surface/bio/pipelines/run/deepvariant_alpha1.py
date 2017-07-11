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
"""Command to run DeepVariant."""

from googlecloudsdk.api_lib.bio import bio
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.bio import flags
from googlecloudsdk.command_lib.util import labels_util
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class DeepVariantAlpha1(base.Command):
  """Runs DeepVariant Alpha1.

  See https://cloud.google.com/genomics/v1alpha2/deepvariant for more
  information.
  """

  @staticmethod
  def Args(parser):
    flags.GetPipelineInputPairFlag().AddToParser(parser)
    flags.GetPipelineOutputPathFlag().AddToParser(parser)
    flags.GetPipelineSampleNameFlag().AddToParser(parser)

    labels_util.AddCreateLabelsFlags(parser)

    flags.GetPipelineLoggingFlag().AddToParser(parser)
    flags.GetPipelineZonesFlag().AddToParser(parser)

  def Run(self, args):
    pipelines = bio.Pipelines(properties.VALUES.core.project.Get())
    op = pipelines.RunDeepVariant(
        compute_zones=args.zones,
        input_fastq1=[args.input_pair[0]],
        input_fastq2=[args.input_pair[1]],
        labels=labels_util.UpdateLabels(
            None,
            pipelines.GetMessages().PipelineOptions.LabelsValue,
            labels_util.GetUpdateLabelsDictFromArgs(args), None),
        output_path=args.output_path,
        sample_name=args.sample_name)

    log.status.Print('Running [{0}].'.format(op.name))
    return op
