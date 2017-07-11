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
"""Analyzer for evaluation analysis.
"""

from __future__ import absolute_import

import apache_beam as beam
from apache_beam.typehints import Tuple
import numpy as np


class ConfusionMatrix(beam.PTransform):
  """A PTransform for computing the confusion-matrix from the evaluation data.
  """

  def __init__(self, indices_to_labels):
    super(ConfusionMatrix, self).__init__('Confusion Matrix')
    self._indices_to_labels = indices_to_labels

  # TODO(b/33677990): Remove apply method.
  def apply(self, values):
    return self.expand(values)

  def expand(self, values):
    # Count the occurrences of each pair of (target,predicted) and
    # return (target,predicted, count)
    return (values
            | 'get_values' >> beam.Map(lambda x:  # pylint: disable=g-long-lambda
                                       (int(x['target']), int(x['predicted'])))
            .with_output_types(Tuple[int, int])
            | beam.combiners.Count.PerElement('count_target_predicted_pairs')
            .with_output_types(Tuple[Tuple[int, int], int])
            # pylint: disable=g-long-lambda
            | 'format' >> beam.Map(lambda (pair, c), indices_to_labels:
                                   {'target': indices_to_labels[pair[0]],
                                    'predicted': indices_to_labels[pair[1]],
                                    'count': c},
                                   indices_to_labels=self._indices_to_labels))


class PrecisionRecall(beam.PTransform):

  def __init__(self, indices_to_labels):
    super(PrecisionRecall, self).__init__('Precision Recall')
    self._indices_to_labels = indices_to_labels

  # TODO(b/33677990): Remove apply method.
  def apply(self, values):
    return self.expand(values)

  def expand(self, values):

    # This global combine will eventually pull everything down onto a single
    # machine. So if the number of Thresholds*Labels is really large this will
    # hit memory limitations. That point is likely only with several million
    # labels, however.
    combined = values | beam.CombineGlobally(LabelThresholdAggregator())

    pr_raw = combined | 'Precision Recall Computation' >> beam.ParDo(
        PrecisionRecallComputeDoFn())
    pr_with_labels = (pr_raw | 'Replace indices with labels' >> beam.Map(
        # pylint: disable=g-long-lambda
        lambda x, indices_to_labels:
        {'label': indices_to_labels[x[0]], 'threshold': x[1], 'precision': x[2],
         'recall': x[3], 'f1score': x[4]},
        indices_to_labels=self._indices_to_labels))
    return pr_with_labels


class LabelThresholdAggregator(beam.core.CombineFn):
  """Aggregator to combine label thresholds.
  """

  def __init__(self):
    self._num_thresholds = 100

  def create_accumulator(self):
    return dict()

  def _add_input(self, accumulator, label, (thresholds, t1, t2, t3)):
    if label not in accumulator:
      accumulator[label] = (thresholds, t1, t2, t3)
    else:
      (thresholds, c1, c2, c3) = accumulator[label]
      accumulator[label] = (thresholds, c1 + t1, c2 + t2, c3 + t3)
    return accumulator

  def add_input(self, accumulator, element):
    predicted = int(element['predicted'])
    target = int(element['target'])
    score = element.get('score', None)

    if score is None:
      raise ValueError('score is not present for precision-recall calculation')

    thresholds = np.arange(0.0, 1.0, 1.0 / self._num_thresholds)
    zeros = np.zeros(self._num_thresholds, dtype=np.int32)
    counts = np.ones(self._num_thresholds, dtype=np.int32)
    prediction = np.zeros(self._num_thresholds, dtype=np.int32)
    prediction[thresholds < score] = 1
    accurate = np.zeros(self._num_thresholds, dtype=np.int32)
    if predicted == target:
      accurate[thresholds < score] = 1
    self._add_input(accumulator, target, (thresholds, counts, zeros, zeros))
    self._add_input(accumulator, predicted,
                    (thresholds, zeros, prediction, accurate))
    return accumulator

  def merge_accumulators(self, accumulators):
    merged = dict()
    for accumulator in accumulators:
      for key, value in accumulator.iteritems():
        self._add_input(merged, key, value)
    return merged

  def extract_output(self, accumulator):
    return [(k, float(v1[i]), v2[i], v3[i], v4[i])
            for k, (v1, v2, v3, v4) in accumulator.iteritems()
            for i in range(self._num_thresholds)]


class PrecisionRecallComputeDoFn(beam.DoFn):
  """DoFn for calculating the precision and recall figures.
  """

  # TODO(user): Remove the try catch after sdk update
  def process(self, elements):
    try:
      elements = elements.element
    except AttributeError:
      pass
    for element in elements:
      label = element[0]
      threshold = element[1]

      accurate_predicted_label_count = element[4] if element[4] else 0
      target_label_count = element[2] if element[2] else 1
      predicted_label_count = element[3] if element[3] else 1

      precision = accurate_predicted_label_count / float(predicted_label_count)
      recall = accurate_predicted_label_count / float(target_label_count)

      pr_sum = precision + recall
      f1score = 0 if pr_sum == 0 else (2 * precision * recall / pr_sum)

      yield (label, threshold, precision, recall, f1score)


class LogLoss(beam.PTransform):
  """A PTransform for determining the LogLoss curve.
  """

  def __init__(self):
    super(LogLoss, self).__init__('Log Loss')

  # TODO(b/33677990): Remove apply method.
  def apply(self, values):
    return self.expand(values)

  def expand(self, values):
    return (values
            | 'Log Loss value' >> beam.Map(self._log_loss)
            | beam.combiners.Mean.Globally()
            | beam.Map(lambda x: -1.0 * x))

  @staticmethod
  def _log_loss(values):
    """Calculate the log loss of a binary classification.

    Takes a target value, a predicted value, and a score for that prediction.
    Assumes that the score is the probability of the predicted value.

    Args:
      values: a dictionary with target, predicted, and score.

    Returns:
      The log loss values.
    """
    epsilon = 1e-15
    probability = float(values['score'])
    probability = np.maximum(epsilon, probability)
    probability = np.minimum(1 - epsilon, probability)

    actual = 1 if int(values['target']) == int(values['predicted']) else 0
    log_loss = (actual * np.log(probability) + np.subtract(1, actual) *
                np.log(np.subtract(1, probability)))
    return log_loss


class MetadataIndicesToLabelsFn(beam.DoFn):
  """The function to get column transforms from a metadata file.
  """

  # TODO(user): Remove the try catch after sdk update
  def process(self, metadata):
    try:
      metadata = metadata.element
    except AttributeError:
      pass
    indices_to_labels = dict()
    # pylint: disable=unused-variable
    for column, column_data in metadata['columns'].iteritems():
      if column_data['type'] == 'target':
        for label, index in column_data['vocab'].iteritems():
          indices_to_labels[index] = label
    yield indices_to_labels


class GetTargetIndiciesToLabels(beam.PTransform):
  """A PTransform for loading index to label mappings from metadata.
  """

  def __init__(self):
    super(GetTargetIndiciesToLabels, self).__init__('GetTargetIndiciesToLabels')

  # TODO(b/33677990): Remove apply method.
  def apply(self, metadata):
    return self.expand(metadata)

  def expand(self, metadata):
    return metadata | 'GetLabels' >> beam.ParDo(MetadataIndicesToLabelsFn())


class AnalyzeModel(beam.PTransform):
  """A PTransform for analyzing a model.

  Takes evaluation data with the schema "target, predicted, score[optional]".
  """

  def __init__(self, metadata, calculate_pr=True, calculate_log_loss=True):
    """Initializes a AnalyzeModel instance.

    Args:
      metadata: The metadata generated during analysis within a PCollection
        instance.
      calculate_pr: Whether or not precision-recall figures should be
        calculated. This should be false when scores aren't available, i.e. when
        input is in the form (tareget, predicted) instead of (target,
        predicted, score).
      calculate_log_loss: Whether or not log-loss figures should be calculated.
        Should be True only for binary classification models.
    """
    super(AnalyzeModel, self).__init__('AnalyzeModel')
    self._metadata = metadata
    self._calc_log_loss = calculate_log_loss
    self._calc_pr = calculate_pr

  # TODO(b/33677990): Remove apply method.
  def apply(self, evaluation_data):
    return self.expand(evaluation_data)

  def expand(self, evaluation_data):
    indices_to_labels = (self._metadata
                         | 'GetLabels' >> GetTargetIndiciesToLabels())
    confusion_matrix = evaluation_data | ConfusionMatrix(
        beam.pvalue.AsSingleton(indices_to_labels))
    if self._calc_pr:
      precision_recall = evaluation_data | PrecisionRecall(
          beam.pvalue.AsSingleton(indices_to_labels))
      if self._calc_log_loss:
        logloss = evaluation_data | LogLoss()
        return confusion_matrix, precision_recall, logloss
      return confusion_matrix, precision_recall
    return confusion_matrix
