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
"""Metric library for Cloud ML batch prediction dataflow transforms.
"""

# TODO(user): Get rid of this file and instead just use counters and other
# metrics directly in the body of the pertinent DoFns.

from apache_beam.metrics import Metrics


class AggregatorName(object):
  """Names of the metrics."""
  ML_PREDICTIONS = "ml-predictions"


# The aggregator config.
CONFIG_ = [
    (AggregatorName.ML_PREDICTIONS),
]


def CreateAggregatorsDict(namespace="main"):
  """Creates metrics dict."""
  return {name: Metrics.counter(namespace, name) for name in CONFIG_}
