# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Dataflow-related utilities.
"""

import apache_beam as beam
from apache_beam.metrics import Metrics


class CheckErrorThreshold(beam.PTransform):

  def __init__(self, error_threshold, **kwargs):
    super(CheckErrorThreshold, self).__init__(**kwargs)
    self._error_threshold = error_threshold

  # TODO(b/33677990): Remove apply method.
  def apply(self, (errors, data)):
    return self.expand((errors, data))

  def expand(self, (errors, data)):
    if 0 < self._error_threshold < 1:

      # pylint: disable=unused-argument
      def check_threshold(unused, bad, total, threshold):
        if bad > total * threshold:
          raise RuntimeError(
              'Number of bad records (%s/%s) exceeded threshold of %s' %
              (bad, total, threshold))

      _ = (
          data.pipeline
          | beam.Create([None])
          | 'Compare'
          >> beam.Map(
              check_threshold,
              beam.pvalue.AsSingleton(
                  errors | 'ErrorCount' >> beam.combiners.Count.Globally()),
              beam.pvalue.AsSingleton(
                  data | 'DataCount' >> beam.combiners.Count.Globally()),
              self._error_threshold))


class CountPCollection(beam.PTransform):
  """Counts the number of items in a PCollection."""

  class CountDoFn(beam.DoFn):

    def __init__(self, aggregate_name):
      self.counter = Metrics.counter(self.__class__, aggregate_name)

    def process(self, element):
      self.counter.inc()

  def __init__(self, aggregate_name):
    super(CountPCollection, self).__init__(label=aggregate_name)
    self.aggregate_name = aggregate_name

  # TODO(b/33677990): Remove apply method.
  def apply(self, pc):
    return self.expand(pc)

  def expand(self, pc):
    return pc | beam.ParDo(CountPCollection.CountDoFn(self.aggregate_name))
