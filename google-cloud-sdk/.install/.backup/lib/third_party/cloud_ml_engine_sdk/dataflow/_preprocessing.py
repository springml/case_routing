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
"""Dataflow transforms for running preprocessing.
"""

import collections
import logging
import random


import apache_beam as beam

from google.cloud.ml.features import _transforms
from google.cloud.ml.features._analysis import AnalyzeData
from google.cloud.ml.features._features import Feature
from google.cloud.ml.features._features import FeatureColumn
from google.cloud.ml.features._features import FeatureTypes
from google.cloud.ml.features._pipeline import TransformData as ExtractFeatures


def _validate_features(features):
  """Performs internal validation of the defined set of features.

  Args:
    features: The metadata features.

  Raises:
    ValueError: An invalid feature set has been specified.
  """
  key_column = None
  target_column = None

  column_names = set()
  for feature in features:
    for column in feature.columns:
      if column.name in column_names:
        raise ValueError(
            'Column names should be unique, "%s" is already defined.' %
            column.name)
      else:
        column_names.add(column.name)
      if column.exclusive and len(feature.columns) > 1:
        raise ValueError(
            'The column "%s" cannot be combined with other columns.' %
            column.name)

      if column.value_type == FeatureTypes.KEY:
        if key_column is not None:
          raise ValueError(
              'Id feature "%s" conflicts with existing id feature "%s".',
              (column.name, key_column.name))
        else:
          key_column = column

      if column.value_type == FeatureTypes.TARGET:
        if target_column is not None:
          raise ValueError(
              'Target feature "%s" conflicts with existing target "%s".',
              (column.name, target_column.name))
        else:
          if column.scenario is None:
            raise ValueError(
                'Target column does not specify scenario. '
                'discrete() or continuous() needs to be called.')
          target_column = column


def _validate_csv_metadata(format_metadata):
  """Performs internal validation on the format metadata.

  Args:
    format_metadata: Dictionary of format metadata.

  Raises:
    ValueError: If the format metadata is invalid.
  """
  if not format_metadata or 'headers' not in format_metadata:
    raise ValueError(
        'Headers should always be specified when the format is "csv".')

  header_names = set()
  for header in format_metadata['headers']:
    if header in header_names:
      raise ValueError(
          'Headers should be unique, "%s" is already defined.' % header)
    else:
      header_names.add(header)


def _get_target_column(features):
  """Retrieve the target feature column if any."""
  target_column = None
  for feature in features:
    for column in feature.columns:
      if column.value_type == FeatureTypes.TARGET:
        target_column = column.name
        break
  return target_column


def get_features(feature_set):
  """Get Features from a feature set.

  Args:
    feature_set: The set of features.

  Returns:
    The list of feature values.
  """
  if isinstance(feature_set, dict):
    feature_dict = feature_set
  else:
    feature_dict = type(feature_set).__dict__
  features = {}
  for name, value in feature_dict.iteritems():
    if not isinstance(value, list) and not isinstance(value, tuple):
      value = [value]
    _get_features_for_list(name, value, features)
  feature_values = features.values()
  _validate_features(feature_values)
  return feature_values


def _get_features_for_list(name, column_values, features_dict):
  columns = []
  for column in column_values:
    if issubclass(type(column), FeatureColumn):
      columns.append(column)
  if columns:
    features_dict[name] = Feature(name, columns)


class DictionaryToTuple(_transforms.DictionaryToTupleBase, beam.DoFn):
  """Extract values from all feature columns."""

  def __init__(self, features):
    sorted_columns = _transforms.sorted_columns_from_features(features)
    column_ordering = [column.name for column in sorted_columns]
    super(DictionaryToTuple, self).__init__(column_ordering)

  # TODO(user): Remove the try catch after sdk update
  def process(self, element):
    try:
      yield self.columns_to_tuple(element.element)
    except AttributeError:
      yield self.columns_to_tuple(element)


class SequenceToTuple(_transforms.SequenceToTupleBase, beam.DoFn):
  """Extract values from all feature columns."""

  def __init__(self, features, source_column_headers, target_column):
    """Generate column indices for the feature columns.

    Args:
      features: Features as defined on Preprocess.
      source_column_headers: List of headers as they appear on the original csv.
      target_column: String to indicate the name of the target column if any.
    """
    sorted_columns = _transforms.sorted_columns_from_features(features)
    sorted_feature_column_names = [column.name for column in sorted_columns]
    super(SequenceToTuple, self).__init__(
        source_column_headers, sorted_feature_column_names, target_column)

  # TODO(user): Remove the try catch after sdk update
  def process(self, element):
    try:
      yield self.columns_to_tuple(element.element)
    except AttributeError:
      yield self.columns_to_tuple(element)


class Preprocess(beam.PTransform):
  """A transform to analyze and transform a training and test datasets.

  The training dataset is analyzed first in order to compute the statistics
  needed to transform the evaluation dataset(s).
  """

  def __init__(self,
               feature_set,
               error_threshold=0,
               return_bad_elements=False,
               input_format=None,
               format_metadata=None,
               shuffle_data=True):
    """Construct the transform.

    Args:
      feature_set: the feature set describing the features in the data.
      error_threshold: maximum number of malformed elements (as a ratio of
        total elements) to filter without aborting the entire pipeline
      return_bad_elements: whether to also return the PCollection of malformed
        elements for each input PCollection
      input_format: required format of the input (i.e. un-preprocessed) dataset.
        Possible values are in the features.FeatureFormat class
        (eg. 'csv', 'json').
      format_metadata: metadata about input dataset. For 'csv' for example,
        this would be an ordered list of the csv-headers.
      shuffle_data: whether to randomly shuffle the data (which is often
        required for stochastic and mini-batch learning).

    Raises:
      ValueError: If the headers are not specified when the input format is csv.
    """
    super(Preprocess, self).__init__()
    self._features = get_features(feature_set)
    self._error_threshold = error_threshold
    self._return_bad_elements = return_bad_elements
    self._input_format = input_format
    # TODO(b/32726166) Make sure input format and metadata are required.
    if self._input_format is None or format_metadata is None:
      logging.warning('input_format is None; input_format and format_metadata '
                      'will become required after the next release.')
    self._format_metadata = format_metadata
    if self._input_format == 'csv':
      _validate_csv_metadata(self._format_metadata)
    self._shuffle_data = shuffle_data

  @staticmethod
  @beam.ptransform_fn
  def _Shuffle(pcoll):
    # TODO(user): Express this in a more canonical way if/when Dataflow
    # supports it.
    return (pcoll | 'PairWithRandom'
            >> beam.Map(lambda x: (random.random(), x))
            | 'GroupByRandom' >> beam.GroupByKey()
            | 'DropRandom' >> beam.FlatMap(lambda (k, vs): vs))

  @staticmethod
  def _discard_invalid_records(record):
    """Discard invalid records as found by the coders."""
    # TODO(b/32791683) for now only yield records deemed as valid records
    # (not-None, non-Empty). We should add a feature to raise an error
    # when there are more than self._error_threshold errors. Keep track of the
    # number of invalid records.
    if record:
      yield record

  # TODO(b/33677990): Remove apply method.
  def apply(self, datasets):
    return self.expand(datasets)

  def expand(self, datasets):
    """Apply the transform.

    Args:
      datasets: A PCollection or a tuple of PCollections. The
        first dataset will be used to compute statistics used to parameterize
        the preprocessing. Features will be extracted from all datasets.

    Returns:
      A tuple (metadata, extracted_dataset_0, extracted_dataset_1, ....)
      metadata: A PCollection containing a single record containing the results
         of the analyze phase.
      extracted_dataset_i: A PCollection containing the results of transforming
        datasets[i].

    If return_bad_elements is set, each dataset is followed by a PCollection of
    all malformed elements for that dataset's input.

    Raises:
      ValueError: If the input isn't a valid tuple of pcollections.
    """
    if not isinstance(datasets, collections.Iterable):
      # It's not an iterable so make it one.
      datasets = [datasets]

    if len(datasets) < 1:
      raise ValueError(
          'The input should be a tuple of at least 1 PCollection: (training).')

    if self._input_format == 'csv':
      # Read the tuple directly when the source format is csv.
      target_column = _get_target_column(self._features)
      internal_format_fn = SequenceToTuple(
          self._features,
          self._format_metadata['headers'],
          target_column)
    else:
      # Extract the fields from the dictionary otherwise.
      internal_format_fn = DictionaryToTuple(
          self._features)

    internal_datasets = []
    for i, d in enumerate(datasets):
      internal_datasets.append(
          d
          | 'DiscardInvalidRows_{0}'.format(i) >> beam.FlatMap(
              self._discard_invalid_records)
          | 'ToInternalTuple_{0}'.format(i) >> beam.ParDo(internal_format_fn))

    metadata, errors = (
        internal_datasets[0]
        | 'AnalyzeData' >> AnalyzeData(
            self._features,
            error_threshold=self._error_threshold,
            return_bad_elements=True,
            input_format=self._input_format,
            format_metadata=self._format_metadata))

    results = [metadata]
    if self._return_bad_elements:
      # TODO(user): Implement error handling for analysis phase.
      results.append(errors)

    for i, d in enumerate(internal_datasets):
      if self._shuffle_data:
        d |= 'Shuffle_{0}'.format(i) >> self._Shuffle
      data, errors = (
          d
          | 'ExtractFeatures_{0}'.format(i) >> ExtractFeatures(
              metadata,
              error_threshold=self._error_threshold,
              return_bad_elements=True))
      results.append(data)
      if self._return_bad_elements:
        results.append(errors)

    return tuple(results)
