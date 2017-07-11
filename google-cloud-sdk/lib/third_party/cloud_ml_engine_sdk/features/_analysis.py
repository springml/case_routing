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
"""Feature analysis functionality.
"""

import logging
from math import log
import numbers
import random

import _registries
import _tokenizer
import _transforms
import apache_beam as beam
from apache_beam.typehints import Dict
from apache_beam.typehints import Tuple
from apache_beam.typehints import Union
from apache_beam.typehints import with_input_types
from apache_beam.typehints import with_output_types
import numpy as np

from google.cloud.ml.util import _dataflow as dfutil


class _ExtractValues(beam.DoFn):
  """Extract values from all feature columns."""

  def __init__(self, sorted_feature_columns):
    self._sorted_feature_columns = sorted_feature_columns

  # TODO(user): Remove the context param and try catch after sdk update
  def start_bundle(self, context=None):
    self._extractors = [
        _registries.analyzer_registry.get_analyzer(column).extract_value
        for column in self._sorted_feature_columns
    ]

  def process(self, element):
    try:
      element = element.element
    except AttributeError:
      pass
    try:
      instance = element
      yield [
          extract_value(instance, column_index)
          for column_index, extract_value in enumerate(self._extractors)
      ]
    except Exception as ex:  # pylint: disable=broad-except
      try:
        yield beam.pvalue.TaggedOutput('errors', (ex, element))
      except AttributeError:
        yield beam.pvalue.SideOutputValue('errors', (ex, element))


class AnalyzeData(beam.PTransform):
  """A PTransform to analyze feature data to create metadata for preprocessing.

  The input to this PTransform is a PCollection representing the source dataset,
  with each element of the collection being a dictionary. The keys of which
  correspond to the columns referenced in the feature spec provided when
  constructing this transform.
  """

  def __init__(self,
               features,
               input_format=None,
               format_metadata=None,
               error_threshold=0,
               return_bad_elements=False):
    """Construct an AnalyzeData PTransform.

    Args:
      features: A list of Features for the data.
      input_format: Optional, whether the input was csv or json.
      format_metadata: Optional, arguments to store in the metadata for the
        input_format.
      error_threshold: How many errors are allowed before the job fails.
      return_bad_elements: Should elements with errors be returned as a side
        output.  Defaults to False.
    """
    super(AnalyzeData, self).__init__('Analyze Data')
    self._features = features
    self._format = input_format
    self._format_metadata = format_metadata
    self._error_threshold = error_threshold
    self._return_bad_elements = return_bad_elements
    self._sorted_feature_columns = _transforms.sorted_columns_from_features(
        self._features)

  # TODO(b/33677990): Remove apply method.
  def apply(self, data):
    return self.expand(data)

  def expand(self, data):
    """Analyzes each of the columns in the feature spec to generate metadata.

    Args:
      data: The input PCollection.

    Returns:
      Just the metadata if return_bad_elements is False, otherwise a tuple of
      the metadata and the bad elements side output.
    """
    rows, errors = data | 'Extract Columns' >> beam.ParDo(
        _ExtractValues(self._sorted_feature_columns)).with_outputs(
            'errors', main='rows')
    _ = data | dfutil.CountPCollection('ml-analyze-input')
    _ = errors | dfutil.CountPCollection('ml-analyze-errors')
    _ = (errors, data) | dfutil.CheckErrorThreshold(self._error_threshold)

    analysis_list = []
    combine_fn_analyzers = {}
    for ix, column in enumerate(self._sorted_feature_columns):
      analyzer = _registries.analyzer_registry.get_analyzer(column)
      if isinstance(analyzer, CombineFnColumnAnalyzer):
        combine_fn_analyzers[ix] = analyzer
      else:
        values = rows | 'extract_%s' % column.name >> beam.Map(
            lambda row, ix=ix: row[ix])
        analysis_list.append(values | analyzer)
    if combine_fn_analyzers:
      analysis_list.append(rows | 'Analyze CombineFn Features' >>
                           _MultiColumnAnalyzer(combine_fn_analyzers))

    columns = analysis_list | beam.Flatten() | beam.combiners.ToDict()
    metadata = columns | 'Generate Metadata' >> beam.Map(self._create_metadata)

    if self._return_bad_elements:
      return metadata, errors
    else:
      return metadata

  def _get_version(self):
    # Version numbers are stored in the top level package.
    # Which we can't import at the top as it would be a circular reference.
    import google.cloud.ml as ml  # pylint: disable=g-import-not-at-top
    return ml.__version__

  def _create_metadata(self, columns):
    features = {}
    stats = {}
    metadata = {
        'sdk_version': self._get_version(),
        'columns': columns,
        'features': features,
        'stats': stats,
    }
    if self._format:
      metadata['format'] = self._format
      if self._format_metadata:
        metadata[self._format] = self._format_metadata

    for feature in self._features:
      feature_size = 0
      feature_type = 'dense'
      feature_dtype = 'int64'
      feature_cols = []

      for feature_column in feature.columns:
        column_name = feature_column.name
        column = columns.get(column_name, None)
        if not column:
          logging.warning('%s not processed because it has no metadata',
                          column_name)
          continue
        value_type = column['type']
        if value_type == 'target' and hasattr(feature_column, 'scenario'):
          column['scenario'] = feature_column.scenario

        transformer = _registries.transformation_registry.get_transformer(
            column)
        if transformer.dtype != 'int64':
          # If we're combining an int with anything else, the "other" dtype
          # takes precedence. For numeric columns, this will be 'float' and for
          # anything else, this will likely be 'bytes'
          # TODO(user). Some unexpected behaviour could result from the
          # assignment of dtypes here (i.e. in the loop) with respect to
          # incompatible types getting combined mistakenly. At the time of
          # b/32318252 has been opened to track refactoring this logic so that
          # it is clearer to the reader.
          feature_dtype = transformer.dtype
        if transformer.feature_type == 'sparse':
          # If we're combining dense transforms with sparse transforms, the
          # resulting feature will be sparse.
          # TODO(user): Consider having an enum for 'sparse' and 'dense'
          feature_type = 'sparse'
        feature_size += transformer.feature_size

        if value_type == 'key':
          stats['instances'] = column['count']
        elif value_type == 'target':
          if 'vocab' in column:
            stats['labels'] = len(column['vocab'])
          if 'mean' in column:
            stats['mean'] = column['mean']

        feature_cols.append(column_name)

      features[feature.name] = {
          'name': feature.name,
          'size': feature_size,
          'type': feature_type,
          'dtype': feature_dtype,
          'columns': feature_cols
      }

    return metadata


class _MultiColumnAnalyzer(beam.PTransform):

  def __init__(self, analyzers):
    self._analyzers = analyzers

  # TODO(b/33677990): Remove apply method.
  def apply(self, rows):
    return self.expand(rows)

  def expand(self, rows):
    value_indices, value_analyzers = zip(*self._analyzers.items())
    assert all(
        isinstance(analyzer, CombineFnColumnAnalyzer)
        for analyzer in value_analyzers)
    return (
        rows
        | 'Extract' >> beam.Map(lambda row: [row[ix] for ix in value_indices])
        | 'Combine' >> beam.CombineGlobally(beam.combiners.TupleCombineFn(
            *[a.combine_fn for a in value_analyzers])).without_defaults()
        | 'PairWithName' >> beam.FlatMap(lambda combined_values: [  # pylint: disable=g-long-lambda
            (a.column_name, a.combined_value_to_dict(c))
            for a, c in zip(value_analyzers, combined_values)]))


class ColumnAnalyzer(beam.PTransform):
  """Base class for column analyzers.
  """

  def __init__(self, column):
    super(ColumnAnalyzer, self).__init__('Analyze ' + column.name)
    self._column = column

  def extract_value(self, instance, index):
    """Extracts the column value from an element (represented as a dict).

    By default, extracts the value by column name, returning None if it does
    not exist.

    May be overridden to compute this value and/or throw an error if the
    column value is not valid.

    Args:
      instance: The input instance to extract from.
      index: The index for the feature column being analyzed.

    Returns:
      The column from this instance.
    """
    return instance[index]

  def _get_column_metadata(self):
    """Returns a dictionary of the needed metadata.

    Sets name, type and transforms args if there are any.

    Returns:
      A dictionary of the needed metadata.
    """
    column_metadata = {'name': self._column.name}
    if self._column.default is not None:
      column_metadata['default'] = self._column.default
    if self._column.value_type:
      column_metadata['type'] = self._column.value_type

    transform_name = self._column._transform  # pylint: disable=protected-access
    if transform_name:
      column_metadata['transform'] = transform_name
    if transform_name and self._column.transform_args:
      column_metadata[transform_name] = self._column.transform_args
    return column_metadata


class IdentityColumnAnalyzer(ColumnAnalyzer):
  """This is the default analyzer, and only generates simple metatada.

    Disregards the values and returns a PCollection with a single entry. A tuple
    in the same format as all the other metadata.
  """

  # TODO(b/33677990): Remove apply method.
  def apply(self, values):
    return self.expand(values)

  def expand(self, values):
    return ['empty'] | 'Identity Metadata' >> beam.Map(
        self._ret_val)  # run once

  def _ret_val(self, _):
    return (self._column.name, self._get_column_metadata())


class CombineFnColumnAnalyzer(ColumnAnalyzer):
  """Analyzes columns using a CombineFn.

  Subclasses MUST NOT override the apply method, as an alternative
  (cross-feature) PTransform may be used instead.
  """

  def __init__(self, column, combine_fn, output_name='combined_value'):
    assert self.apply.im_func is CombineFnColumnAnalyzer.apply.im_func, (
        'Subclass %s of CombineFnColumnAnalyzer must not overload apply.' %
        type(self))
    super(CombineFnColumnAnalyzer, self).__init__(column)
    self._combine_fn = combine_fn
    self._output_name = output_name

  @property
  def combine_fn(self):
    return self._combine_fn

  @property
  def column_name(self):
    return self._column.name

  # TODO(b/33677990): Remove apply method.
  def apply(self, values):
    return self.expand(values)

  def expand(self, values):
    return (
        values
        | beam.CombineGlobally(self._combine_fn).without_defaults()
        |
        beam.Map(lambda c: (self.column_name, self.combined_value_to_dict(c))))

  def combined_value_to_dict(self, aggregate):
    return dict(self._get_column_metadata(), **{self._output_name: aggregate})


@_registries.register_analyzer('key')
class IdColumnAnalyzer(CombineFnColumnAnalyzer):
  """Analyzes id columns to produce a count of instances.
  """

  def __init__(self, column):
    super(IdColumnAnalyzer, self).__init__(column,
                                           beam.combiners.CountCombineFn(),
                                           'count')

  def combined_value_to_dict(self, count):
    return {'name': self._column.name, 'type': 'key', 'count': count}


@_registries.register_analyzer('numeric')
@with_input_types(Union[int, long, float])
@with_output_types(Tuple[str, Dict[Union[str, unicode], float]])
class NumericColumnAnalyzer(CombineFnColumnAnalyzer):
  """Analyzes numeric columns to produce a min/max/mean statistics.
  """

  def __init__(self, column):
    super(NumericColumnAnalyzer, self).__init__(
        column, self.MinMeanMax(getattr(column, 'log_base', None)))

  def extract_value(self, instance, index):
    value = instance[index]
    if value is not None and not isinstance(value, numbers.Number):
      return float(value)
    else:
      return value

  def combined_value_to_dict(self, combined_value):
    return dict(self._get_column_metadata(), **combined_value)

  class MinMeanMax(beam.core.CombineFn):
    """Aggregator to combine values within a numeric column.
    """

    def __init__(self, log_base=None):
      self._log_base = log_base

    def create_accumulator(self):
      return (float('+inf'), float('-inf'), 0, 0)

    def add_input(self, stats, element):
      if element is None:
        return stats
      (min_value, max_value, total, count) = stats
      if self._log_base:
        element = log(element, self._log_base)
      return (min(min_value, element), max(max_value, element), total + element,
              count + 1)

    def merge_accumulators(self, accumulators):
      min_values, max_values, totals, counts = zip(*accumulators)
      return (min(min_values), max(max_values), sum(totals), sum(counts))

    def extract_output(self, stats):
      (min_value, max_value, total, count) = stats
      return {
          'min': min_value,
          'max': max_value,
          'mean': 0 if count == 0 else total / float(count),
      }


@_registries.register_analyzer('categorical')
@with_input_types(Union[str, unicode])
@with_output_types(Tuple[str, Dict[Union[str, unicode], float]])
class CategoricalColumnAnalyzer(ColumnAnalyzer):
  """Analyzes categorical columns to produce a dictionary of discrete values.

    Returns a tuple (column_name, metadata_dictionary).
    (This will return an empty list, if no values appear more than
    frequency threshold times. b/30843722)
  """

  def __init__(self, column):
    super(CategoricalColumnAnalyzer, self).__init__(column)

    # Need to make these checks because all columns will not have these
    # attributes. This is true for TargetFeatureColumns which get this analyzer
    # by default if we're in a classification problem.
    if hasattr(column, 'frequency_threshold'):
      self._frequency_threshold = column.frequency_threshold
    else:
      self._frequency_threshold = 0
    if hasattr(column, 'tokenizer_args'):
      tokenizer_args = column.tokenizer_args
      # Although create_flat_tokenizer also deals with empty split_regex, it is
      # useful to skip the tokenization step since it ammounts to a noop.
      if tokenizer_args and tokenizer_args['split_regex']:
        # Create a tokenizer that matches the one used by the categorical column
        # transform.
        self._tokenizer_fn = _tokenizer.create_flat_tokenizer(
            split_regex=tokenizer_args['split_regex'],
            stop_words=tokenizer_args['stop_words'],
            use_stemmer=tokenizer_args['use_stemmer'],
            ngrams=tokenizer_args['ngrams'],
            strip_html=tokenizer_args['strip_html'],
            removable_tags=tokenizer_args['removable_tags'])
      else:
        self._tokenizer_fn = None
    else:
      self._tokenizer_fn = None
    self._aggregator = CategoricalColumnAnalyzer.Aggregator(
        self._get_column_metadata())

  # TODO(b/33677990): Remove apply method.
  def apply(self, values):
    return self.expand(values)

  def expand(self, values):
    if self._tokenizer_fn:
      values |= 'Tokenize Categorical' >> beam.FlatMap(self._tokenizer_fn)
    values |= 'count' >> beam.combiners.Count.PerElement()
    if self._frequency_threshold > 1:
      values |= 'filter by threshold' >> beam.Filter(
          lambda x: x[1] >= self._frequency_threshold)
    return (values
            | 'Analysis'
            >> beam.core.CombineGlobally(self._aggregator).without_defaults())

  class Aggregator(beam.core.CombineFn):
    """Aggregator to combine values within a categorical column.
    """

    def __init__(self, column):
      self._column = column

    def create_accumulator(self):
      return set()

    def add_input(self, accumulator, element):
      if element[0] is not None:
        accumulator.add(element[0])
      return accumulator

    def merge_accumulators(self, accumulators):
      return set.union(*accumulators)

    def extract_output(self, accumulator):
      items = dict(zip(sorted(accumulator), xrange(len(accumulator))))
      column = self._column
      column['vocab'] = items
      column['idf'] = {}
      return (self._column['name'], column)


@_registries.register_analyzer('text')
@with_input_types(Union[str, unicode])
@with_output_types(Tuple[str, Dict[Union[str, unicode], float]])
class TextColumnAnalyzer(ColumnAnalyzer):
  """Analyzes text columns to produce a dict and mapping of words to indices.

  """

  def __init__(self, column):
    super(TextColumnAnalyzer, self).__init__(column)
    self._tokenizer_fn = _tokenizer.create_flat_tokenizer(
        split_regex=column.split_regex,
        stop_words=column.stop_words,
        use_stemmer=column.use_stemmer,
        ngrams=column.ngrams,
        strip_html=column.strip_html,
        removable_tags=column.removable_tags)
    self._aggregator = TextColumnAnalyzer.Aggregator(self._get_column_metadata(
    ))
    self._word2vec_dict = column.word2vec_dict
    if not self._word2vec_dict:
      self._n = column.transform_args['vocab_size']
    self._sampling_percentage = column.sampling_percentage
    self._ngrams = column.ngrams
    self._use_tf_idf = column.use_tf_idf
    self._frequency_threshold = column.frequency_threshold

  # TODO(b/33677990): Remove apply method.
  def apply(self, values):
    return self.expand(values)

  def expand(self, values):
    if self._sampling_percentage < 100.0:
      values |= 'Sampling %s/100' % self._sampling_percentage >> beam.ParDo(
          SamplingFn(self._sampling_percentage))

    ngram_list_list = values | 'Tokenize index' >> beam.Map(self._tokenizer_fn)

    if self._word2vec_dict:
      max_doc_size = beam.pvalue.AsSingleton(
          self._get_max_tokens_in_doc(ngram_list_list))
      metadata_column = (self._column.name, self._get_column_metadata())
      return [metadata_column] | 'create metadata' >> beam.Map(
          self._add_doc_size, max_doc_size)

    ngram_counts = (ngram_list_list
                    | 'FlatMap' >> beam.FlatMap(lambda x: x)
                    | 'Count' >> beam.combiners.Count.PerElement())

    if self._frequency_threshold > 1:
      ngram_counts |= ('Filter categories' >>
                       beam.Filter(lambda a: a[1] >= self._frequency_threshold))

    top_n_grams = (ngram_counts | 'TopNCount' >> beam.combiners.Top.Of(
        self._n, compare=lambda a, b: (a[1], a[0]) < (b[1], b[0])))

    vocab_grams = top_n_grams
    vocab_column = vocab_grams | 'Analysis' >> beam.core.CombineGlobally(
        self._aggregator).without_defaults()

    if self._use_tf_idf:
      docs_count = beam.pvalue.AsSingleton(values | 'Count Documents' >>
                                           beam.combiners.Count.Globally())
      vocab_set = vocab_column | 'Get Vocab Set' >> beam.Map(
          lambda x: set(x[1]['vocab'].keys()))
      idf_dict = self._get_idf_dict(ngram_list_list, vocab_set, docs_count)
      return (idf_dict | beam.Map(self.convert_idf_dict,
                                  beam.pvalue.AsSingleton(vocab_column)))
    else:
      return vocab_column

  def _add_doc_size(self, column, max_doc_size):
    (name, column_dict) = column
    column_dict['word2vec']['max_doc_size'] = max_doc_size
    return (name, column_dict)

  def _get_idf_dict(self, ngram_list_list, vocab_set, docs_count):
    return (ngram_list_list
            # flatten ngrams lol, take set
            | 'Unique Ngrams per doc' >> beam.FlatMap(set)
            | beam.combiners.Count.PerElement()
            | 'Vocab Filter' >> beam.FlatMap(self.vocab_filter,
                                             beam.pvalue.AsSingleton(vocab_set))
            | 'compute idf' >> beam.ParDo(self.idf, docs_count)
            | beam.combiners.ToDict())

  def _get_max_tokens_in_doc(self, ngram_list_list):
    return (ngram_list_list
            | 'Count of words doc' >> beam.FlatMap(lambda x: [len(x)])
            | beam.CombineGlobally(self.MaxFn()))

  # TODO(user): Investigate doing this Max with native dataflow transforms.

  def vocab_filter(self, kv, vocab):
    (k, v) = kv
    if k in vocab:
      yield (k, v)

  def convert_idf_dict(self, word_to_idf, column):
    """Convert idf dict from word-> idf score, to word_vocab_index-> idf score.

    Args:
      word_to_idf: Dictionary with word to idf mapping.
      column: The metadata column.

    Returns:
      The column name and column dictionary.
    """
    (column_name, column_dict) = column
    id_to_idf = np.zeros(len(word_to_idf))
    for word in word_to_idf.keys():
      word_idx = column_dict['vocab'].get(word, -1)
      if word_idx >= 0:  # if word in final vocab
        id_to_idf[word_idx] = word_to_idf[word]
    column_dict['idf'] = id_to_idf.tolist()
    return (column_name, column_dict)

  def idf(self, kv, docs_count):
    """Calculate inverse document frequency for a word.

    Args:
      kv: key-value of (word, number of documents it appears in).
      docs_count: number of total documents

    Raises:
      ValueError: If the number of documents is negative.

    Yields:
      A tuple of key and idf.
    """
    (key, v) = kv
    if v <= 0:
      raise ValueError('Number of documents word %s appeared is %d' % (key, v))
    idf = log(docs_count / float(v)) + 1  # +1 for smoothing - to avoid 0's
    yield (key, idf)

  class MaxFn(beam.CombineFn):
    """A CombineFn to find the max of the input PCollection.
    """

    def create_accumulator(self):
      return -1

    def add_input(self, current_min, x):
      return max(current_min, x)

    def merge_accumulators(self, accumulators):
      return max(accumulators)

    def extract_output(self, x):
      return x

  class Aggregator(beam.core.CombineFn):
    """Aggregator to combine values within a text column.
    """

    def __init__(self, column):
      self._column = column

    def create_accumulator(self):
      return set()

    def add_input(self, accumulator, element):
      for (word, _) in element:
        if word is not None:
          accumulator.add(word)
      return accumulator

    def merge_accumulators(self, accumulators):
      return set.union(*accumulators)

    def extract_output(self, accumulator):
      vocab = dict(zip(sorted(accumulator), xrange(len(accumulator))))
      column = self._column
      column['vocab'] = vocab
      column['idf'] = None
      return (self._column['name'], column)


class SamplingFn(beam.DoFn):

  def __init__(self, sampling_percentage):
    super(SamplingFn, self).__init__('Sampling')
    self._sampling_percentage = sampling_percentage

  # TODO(user): Remove the try catch after sdk update
  def process(self, element):
    try:
      element = element.element
    except AttributeError:
      pass
    random_sample = random.uniform(0.0, 100.0)
    if random_sample <= self._sampling_percentage:
      yield element
