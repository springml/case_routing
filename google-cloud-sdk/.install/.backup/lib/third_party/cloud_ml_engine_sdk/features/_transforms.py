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
"""Feature transformation functionality.
"""

import hashlib
import logging
import math
import os
import re

import _features
import _registries
import _tokenizer
from apache_beam import coders
from apache_beam.io import gcsio
import numpy as np
from PIL import Image
from six.moves import cStringIO

from google.cloud.ml.io import coders as ml_coders


# TODO(user): Use this or introduce a TensorProtoFormatter (whichever is
# faster) for batch and online predictions.
#
# TODO(b/30748966): Possibly remove FeatureDictFormatter.
#
# This code is performance critical so make sure to run the corresponding
# benchmark when updating it.
class FeatureDictFormatter(object):
  """Standalone class to format processed feature data to tensor-values.

  The tensor-values are not tf.tensors, just arrays. There is no distinction
  between scalar or tensor values.

  If the values are sparse representation pairs (index, value) then the dtype
  refers to the value, while the index is always considered to be an int64.

  Example:
    input: {'foods': ('bytes', ['pizza', 'ice cream']),
            'drinks': ('bytes', ['water']),
            'cost': ('float', [(0, 10.0), (1, 3.0), (2, 0.5)])}
    output: the python dict
      {'foods': ['pizza', 'ice cream'],
       'drinks': ['water'],
       'cost@0': [0, 1, 2],
       'cost@1': [10.0, 3.0, 0.5]}
  """

  def format(self, feature_vectors):
    """Formats given dictionary of feature_vectors.

    Args:
      feature_vectors: Feature vectors to be formatted.
    Returns:
      Dictionary that maps feature names to a feature value list after
      conversion from sparse to dense features where relevant.
    """

    entries = {}
    # dtype is not needed for this formatter.
    for feature_name, (_, feature_vector) in feature_vectors.iteritems():
      if feature_vector and isinstance(feature_vector[0], tuple):
        entries.update(
            FeatureDictFormatter._make_dense_features(feature_name,
                                                      feature_vector))
      else:
        entries[feature_name] = feature_vector

    return entries

  @staticmethod
  def _make_dense_features(feature_name, feature_vector):
    """Decodes the given string.

    Example:
      input: 'cost', [(0, 10.0), (1, 3.0), (2, 0.5)]
      output: the python dict
        {'cost@0': [0, 1, 2],
         'cost@1': [10.0, 3.0, 0.5]}

    Args:
      feature_name: Name of feature.
      feature_vector: Vector to be densified, index and value pairs.

    Returns:
      Dense version of feature_vector.
    """
    # feature_vector is in the form [(k1, k2, ..., v), (k1, k2, ..., v), ...]
    # Split this into parallel features, one for each tuple index.

    features = dict()
    # create lists with one value from each tuple.
    values = zip(*feature_vector)
    # Create a feature for each item in the tuple
    for index, _ in enumerate(feature_vector[0]):
      features[feature_name + '@' + str(index)] = list(values[index])

    return features


# This code is performance critical so make sure to run the corresponding
# benchmark when updating it.
class ExampleProtoFormatter(FeatureDictFormatter):
  """Class for formating processed feature data to tf.Example protos.

  Returns the tf.Example version of FeatureDictFormatter.

  If the values are sparse representation pairs (index, value) then the dtype
  refers to the value, while the index is always considered to be an int64.

  Example:
    input: {'foods': ('bytes', ['pizza', 'ice cream']),
            'drinks': ('bytes', ['water']),
            'cost': ('float', [(0, 10.0'), (1, 3.0), (2, 0.5)])}
    output: The tf.Example containing
        features {
          feature {
            key: 'foods'
            value { bytes_list {
              value: 'pizza'
              value: 'ice cream'
            }}
          }
          feature {
            key: 'drinks'
            value { bytes_list {
              value: 'water'
            }}
          }
          feature {
            key: 'cost@0'
            value { int64_list {
              value: 0
              value: 1
              value: 2
             }}
          }
          feature {
            key: 'cost@1'
            value { float_list {
              value: 10.0
              value: 3.0
              value: 0.5
            }}
          }
        }
  """

  def __init__(self):
    import tensorflow as tf  # pylint: disable=g-import-not-at-top
    self._tf_train = tf.train

  def format(self, feature_vectors):
    """Formats given dictionary of feature_vectors.

    Args:
      feature_vectors: Feature vectors to be formatted.
    Returns:
      Formatted example_proto version of feature vectors
    """

    example = self._tf_train.Example()
    feature_map = example.features.feature
    for feature_name, (dtype, feature_vector) in feature_vectors.iteritems():
      if isinstance(feature_vector[0], tuple):
        for key, values in FeatureDictFormatter._make_dense_features(
            feature_name, feature_vector).iteritems():
          # This is a sparse representation index if the key ends with @0.
          self._update_tf_feature(feature_map[key], values, 'int64' if
                                  key.endswith('@0') else dtype)
      else:
        self._update_tf_feature(feature_map[feature_name], feature_vector,
                                dtype)
    return example

  def _update_tf_feature(self, tf_feature, feature_vector, dtype):
    if dtype == 'int64':
      tf_feature.int64_list.value.extend(feature_vector)
    elif dtype == 'float':
      tf_feature.float_list.value.extend(feature_vector)
    else:
      tf_feature.bytes_list.value.extend(feature_vector)


class FeatureVectorFormatter(FeatureDictFormatter):
  """Class for formating processed feature data to FeatureVectors objects.

  These can be lazily viewed as serialized or deserialized example protos.
  """

  def format(self, feature_vectors):
    return FeatureVector(feature_vectors)


class ColumnTransform(object):
  """Base class for transforms to convert input columns to output features.
  """

  @property
  def dtype(self):
    """Retrieves the data type produced by this transform.

    Returns:
      The tensorflow variable type of the feature. 'float' by default.
    """
    return 'float'

  @property
  def feature_size(self):
    """Retrieves the length of the feature array produced by this transform.

    Returns:
      The size of the feature, 1 by default.
    """
    return 1

  @property
  def feature_type(self):
    """Retrieves whether this transform returns a dense or sparse feature.

    Returns:
      'dense' for dense features, 'sparse' for sparse features.
    """
    return 'dense'

  def _get_dtype_from_value(self, value):
    if isinstance(value, (int, long)):
      return 'int64'
    elif isinstance(value, float):
      return 'float'
    return 'bytes'

  def _value_is_tuple(self):
    """Whether the transformer returns a single element or a tuple.

    Returns:
      Boolean indicating whether the transform generates an array of tuples,
      instead of an array of values. The default implementation returns False.
    """
    return False


@_registries.register_transformer('categorical', 'lookup')
class ValueToIndexTransform(ColumnTransform):
  """Column Transform Class to look up a value in a list and return the index.

  This is the default transform used for Categorical Target columns.
  """

  @staticmethod
  def from_metadata(column):
    return ValueToIndexTransform(column['vocab'],
                                 default=column.get('default', None))

  def _to_column_metadata(self):
    """Constructs a metadata object for this transform, for testing only."""
    return {
        'vocab': self._item_list,
        'default': self._default,
        'transform': 'lookup',
    }

  def __init__(self, item_list, default=None):
    self._item_list = item_list
    self._default = default

  def transform(self, value):
    if not value or value not in self._item_list:
      return [self._default]
    return [self._item_list[value]]

  @property
  def dtype(self):
    """Retrieves the data type produced by this transform.

    Returns:
      The type of the first value in the item list, or int64 if it is empty.
    """
    if not self._item_list or not self._item_list[self._item_list.keys()[0]]:
      return 'int64'
    return self._get_dtype_from_value(self._item_list[self._item_list.keys()[
        0]])


class IdentityTransform(ColumnTransform):
  """Column Transform Class which returns the passed value.

  Just returns the value passed in, with optional default for missing values.
  """

  @staticmethod
  def from_metadata(column):
    # If transform is missing (old behavior, assume identity with dtype float)
    transform_metadata = column.get('identity', {})
    dtype = transform_metadata.get('dtype', 'float')
    return IdentityTransform(dtype)

  def _to_column_metadata(self):
    """Constructs a metadata object for this transform, for testing only."""
    return {'identity': {'dtype': self._dtype,}}

  def __init__(self, dtype='float'):
    self._dtype = dtype

  def transform(self, value):
    if self._dtype == 'int64':
      return [long(value)]
    return [value]

  @property
  def dtype(self):
    return self._dtype


@_registries.register_transformer('numeric', 'discretize')
class DiscretizeTransform(ColumnTransform):
  """Column Transform Class for discretizing a numeric value.
  """

  @staticmethod
  def from_metadata(column):
    return DiscretizeTransform(column['min'], column['max'],
                               column['discretize']['buckets'],
                               column['discretize']['sparse'])

  def __init__(self, range_min, range_max, buckets, sparse):
    self._min = float(range_min)
    self._max = float(range_max)
    if range_max <= range_min:
      raise ValueError('range max is not greater than range min')
    self._buckets = buckets
    self._buckets_are_lists = isinstance(buckets, list)
    if self._buckets_are_lists:
      if not buckets:
        raise ValueError('buckets needs to have atleast one value')
    elif isinstance(buckets, int):
      if buckets <= 1:
        raise ValueError('buckets needs to be 2 or greater')
    else:
      raise ValueError('buckets needs to be either a list or an int')
    self._sparse = sparse

  def transform(self, value):
    """Discretizes a numeric value.

    Args:
      value: Either a list of thresholds, or a scalar representing the number of
      buckets.

    Returns:
      A one-hot vector with the bucket's index set. When given a list of
      N thresholds, the number of buckets is N + 1. When given a scalar for the
      number of buckets (N), the range of the data is divided into N equal
      buckets (i.e. with N-1 equally spaced thresholds).
    """
    if self._buckets_are_lists:
      return DiscretizeTransform._discretize_with_user_defined_buckets(
          value, self._buckets, self._sparse)
    return self._discretize_with_fixed_buckets(value)

  def _discretize_with_fixed_buckets(self, value):
    thresholds = []
    data_range = self._max - self._min
    bucket_size = data_range / self._buckets
    for i in range(1, self._buckets):
      thresholds.append(self._min + (i * bucket_size))
    return DiscretizeTransform._discretize_with_user_defined_buckets(
        value, thresholds, self._sparse)

  @staticmethod
  def _discretize_with_user_defined_buckets(value, thresholds, sparse):
    """Discretizes a numeric value with a given list of thresholds.

    Args:
      value: The value to be discretized.
      thresholds: The list of thresholds that bookend the buckets.
      sparse: Boolean to control return-type. If true, this is a list with
        the bucket-index. If false, this is one-hot-encoded.

    Returns:
      A one-hot vector with the bucket's index set. When given a list of
      N thresholds, the number of buckets is N + 1 (there are N - 1 buckets
      between the first and last thresholds, and there are 2 buckets on the
      left and right of the first and last thresholds).
    """
    thresholds = sorted(thresholds)
    bucket = 0
    while bucket < len(thresholds) and value >= thresholds[bucket]:
      bucket += 1

    # We one-off this case because this value is technically in the range.
    if value == thresholds[len(thresholds) - 1]:
      bucket = len(thresholds) - 1

    if sparse:
      return [bucket]

    vector = [0] * (len(thresholds) + 1)
    vector[bucket] = 1
    return vector

  @property
  def feature_type(self):
    if self._sparse:
      return 'sparse'
    return super(DiscretizeTransform, self).feature_type

  @property
  def feature_size(self):
    if self._sparse:
      return super(DiscretizeTransform, self).feature_size
    if self._buckets_are_lists:
      return len(self._buckets) + 1
    return self._buckets


@_registries.register_transformer('numeric', 'binarize')
class BinarizeTransform(ColumnTransform):
  """Column Transform to transform a value as a 0 or 1 depending on a threshold.

  This transform is suitable for numeric columns.
  """

  @staticmethod
  def from_metadata(column):
    return BinarizeTransform(column['binarize']['threshold'])

  def __init__(self, threshold=0.0):
    self._threshold = threshold

  def transform(self, value):
    return [self.binarize(value, self._threshold)]

  def binarize(self, value, threshold):
    if value > threshold:
      return 1.0
    return 0.0


@_registries.register_transformer('key', 'key')
class IdTransform(ColumnTransform):
  """Column Transform Class to encode a key value.

  This transform is suitable for KEY columns.
  """

  @staticmethod
  def from_metadata(_):
    return IdTransform()

  def transform(self, value):
    # KEY values are represented as a bytes list.
    return [str(value)]

  @property
  def dtype(self):
    return 'bytes'


@_registries.register_transformer('numeric', 'scale')
class NumericScaleTransform(ColumnTransform):
  """Column Transform Class which scales numeric values to the set range.

     formula: v' = (v - min) * (scale_max - scale_min) / (max - min) + scale_min
  """

  @staticmethod
  def from_metadata(column):
    return NumericScaleTransform(column['min'],
                                 column['max'],
                                 column['scale']['min'],
                                 column['scale']['max'],
                                 column['scale']['log_base'])

  def __init__(self, range_min, range_max, scale_min=0.0, scale_max=1.0,
               log_base=0):
    self._min = float(range_min)
    self._max = float(range_max)
    self._scale_min = float(scale_min)
    self._scale_max = float(scale_max)
    self._log_base = log_base

  def transform(self, value):
    if self._log_base > 0:
      value = math.log(value, self._log_base)
    return [self._scale(value)]

  def _scale(self, value):
    if value is None:
      return ((self._scale_max - self._scale_min) / 2.0) + self._scale_min
    if self._max == self._min:
      return self._scale_max

    value = float(value)
    return (((value -  self._min) * (self._scale_max - self._scale_min)) /
            (self._max - self._min)) + self._scale_min


@_registries.register_transformer('categorical', 'bag_of_words')
@_registries.register_transformer('categorical', 'one_of_k')
@_registries.register_transformer('text', 'bag_of_words')
class BagOfWordsTransform(ColumnTransform):
  """Column Transform class to convert a text into a bag of words.

  The encoding of the bag of words can be sparse, that is a list (ngram, score)
  tuples, or a one hot vector dense vector of scores.

  Score can be binary (word exists in document or not), term_frequency,
  or tf_idf. Empty idf dictionary implies that tf*idf should not be used.
  """

  @staticmethod
  def from_metadata(column):
    if column.get('bag_of_words', None) is None:
      # If we are reading from old metadata neither 'one hot' or 'word2vec'
      # will have the bag_of_words property. We create a BOW transform
      # based on the additional information we can retrieve.
      logging.warning('Current implementation of one_of_k is being deprecated '
                      'make sure all the models are retrained with a new SDK.')
      return BagOfWordsTransform(
          column['vocab'],
          output_encoding=_features.BagOfWordsEncodings.ONE_HOT)
    else:
      if column['bag_of_words'].get('output_encoding', None) is None:
        # If we are reading from old metadata bag_of_words will not have
        # output_encoding data. Set output_encoding = SPARSE.
        logging.warning('Using an old version of the metadata please make sure '
                        'all the models are retrained with a new SDK.')
        output_encoding = _features.BagOfWordsEncodings.SPARSE
      else:
        # Else read output_encoding from the metadata.
        output_encoding = column['bag_of_words']['output_encoding']

      return BagOfWordsTransform(
          column['vocab'],
          column['bag_of_words']['buckets'],
          column['bag_of_words']['counts'],
          column['bag_of_words']['split_regex'],
          column['bag_of_words']['stop_words'],
          column['bag_of_words']['use_stemmer'],
          column['bag_of_words']['ngrams'],
          column['idf'],
          column['bag_of_words']['normalize'],
          column['bag_of_words']['strip_html'],
          column['bag_of_words']['removable_tags'],
          output_encoding=output_encoding)

  def _to_column_metadata(self):
    """Constructs a metadata object for this transform, for testing only."""
    transform = ('one_of_k' if
                 self._output_encoding == _features.BagOfWordsEncodings.ONE_HOT
                 else 'bag_of_words')
    return {
        'vocab': self._vocab,
        'transform': transform,
        'idf': self._idf,
        transform: {
            'buckets': self._additional_buckets,
            'counts': self._use_counts,
            'split_regex': self._split_regex,
            'stop_words': self._stop_words,
            'use_stemmer': self._use_stemmer,
            'ngrams': self._ngrams,
            'normalize': self._normalize,
            'strip_html': self._strip_html,
            'removable_tags': self._removable_tags,
        }
    }

  def __init__(self,
               vocab,
               additional_buckets=1,
               use_counts=True,
               split_regex=r'\w{1,}',
               stop_words=None,
               use_stemmer=False,
               ngrams=1,
               idf=None,
               normalize=False,
               strip_html=False,
               removable_tags=None,
               output_encoding=_features.BagOfWordsEncodings.SPARSE):
    if additional_buckets < 1:
      raise ValueError(
          'Invalid number of additional buckets %d. Should be one or greater.'
          % additional_buckets)
    self._vocab = vocab
    self._vocab_size = len(self._vocab)
    self._additional_buckets = additional_buckets
    self._use_counts = use_counts
    self._idf = idf
    self._idf_size = len(idf) if idf else 0
    self._normalize = normalize
    # Validate early that the split_regex is valid when not None.
    if split_regex is not None:
      re.compile(split_regex)
    self._split_regex = split_regex
    self._stop_words = stop_words
    self._use_stemmer = use_stemmer
    self._ngrams = ngrams
    self._strip_html = strip_html
    self._removable_tags = removable_tags
    self._output_encoding = output_encoding
    self._tokenize_fn = None

  def _tokenize(self, text):
    """Tokenize text.

    Tokenize will always return empty array if the input string is '' or None.

    Args:
      text: string to be tokenized.
    Returns:
      An sequence representing the tokenized string.
    """
    # Functions cannot be serialized, lazy initialize here.
    if not self._tokenize_fn:
      self._tokenize_fn = _tokenizer.create_flat_tokenizer(
          split_regex=self._split_regex,
          stop_words=self._stop_words,
          use_stemmer=self._use_stemmer,
          ngrams=self._ngrams,
          strip_html=self._strip_html,
          removable_tags=self._removable_tags)
    return self._tokenize_fn(text)

  def transform(self, text):
    """Convert the text into a bag of words array.

    Args:
      text: The text string to convert.

    Returns:
      When use_count is specified return a list of (word index, count) tuples
      sorted by word index. Else a list of word index. If the input text is
      empty return the size of the vocabulary.
    """
    # Tokenize will return an empty array if the string was empty. The code
    # below understands this and will handle it appropriately.
    tokens = self._do_transform(text)
    if self._output_encoding == _features.BagOfWordsEncodings.ONE_HOT:
      return self._one_hot_encode(tokens, len(self._vocab))
    else:
      return tokens

  def _do_transform(self, text):
    """Convert the text into a bag of words array.

    Args:
      text: The text string to convert.

    Returns:
      A list of (word index, count) tuples sorted by word index. If use counts,
      else a list of word index.
    """
    gram_list = self._tokenize(text)

    # tf-idf overrides use-counts
    if not self._use_counts and not self._idf:
      repeated_indices_list = []
      for gram in gram_list:
        index = self._get_index(gram)
        if index != -1:
          repeated_indices_list.append(index)
      if not repeated_indices_list:
        return [self._vocab_size]
      return repeated_indices_list

    bag = {}
    for gram in gram_list:
      index = self._get_index(gram)
      if index != -1:
        bag[index] = bag.get(index, 0) + 1

    norm = 0.0
    if self._idf:
      for word_index in bag:
        idf_score = 0  # if word not in idf dict, no weight
        if word_index < self._idf_size:
          idf_score = self._idf[word_index]

        bag[word_index] *= idf_score
        norm += bag[word_index]**2  # calculates sum of squares on the fly

    if self._normalize:
      if not self._idf:
        norm = np.sum(np.array(bag.values())**2)  # calculate sum of squares
      if norm > 0:
        norm = math.sqrt(norm)
        for word_index in bag:  # divide everything by norm
          bag[word_index] /= norm

    # If there was no text (more specifically no words), the map will be empty.
    # If there is at least one out of value bucket, then record a
    # "pseduo-unknown" value. This will ensure that the resulting sparse feature
    # is never empty, which is required of some TensorFlow ops.
    #
    # Note that the index len(vocab) is the first bucket after all the indices
    # representing the actual vocabulary.
    if not bag:
      bag[self._vocab_size] = 1

    # Sort based on the indices as Tensorflow will expect them sorted.
    return sorted(bag.items())

  def _one_hot_encode(self, word_indexes, vocab_size):
    """Encode the word indexes on a dense vector.

    Args:
      word_indexes: a sparse vector of indexes or tuples (index, score),
      vocab_size: size of the vocabulary
    Returns:
      A dense vector of size vocab_size, if the inputs are tuples the dense
      vector will use the socre as the indicator else 1s will be used.
    """

    def get_index(index_or_tuple):
      if not self._use_counts and not self._idf:
        # The value is an index.
        return index_or_tuple
      else:
        # The value is a tuple (index, score).
        return index_or_tuple[0]

    def get_score(index_or_tuple):
      if not self._use_counts and not self._idf:
        # The value is an index.
        return 1
      else:
        # The value is a tuple (index, score).
        return index_or_tuple[1]

    vector = [0] * vocab_size
    if not word_indexes:
      return vector

    # TODO(user): do we want to add a bucket for unknown category labels?
    if len(word_indexes) == 1:
      # OOV words are not added to the one hot vector.
      index_or_tuple = word_indexes[0]
      index = get_index(index_or_tuple)
      if index != vocab_size:
        vector[index] = get_score(index_or_tuple)
    else:
      for index_or_tuple in word_indexes:
        vector[get_index(index_or_tuple)] = get_score(index_or_tuple)
    return vector

  @property
  def feature_size(self):
    if self._output_encoding == _features.BagOfWordsEncodings.ONE_HOT:
      # One hot encoding doesn't have OOV buckets.
      return self._vocab_size
    else:
      return self._vocab_size + self._additional_buckets

  @property
  def feature_type(self):
    if self._output_encoding == _features.BagOfWordsEncodings.ONE_HOT:
      return 'dense'
    else:
      return 'sparse'

  def _value_is_tuple(self):
    """Whether the transformer returns a single element or a tuple."""
    return self._use_counts

  def _get_index(self, gram):
    index = self._vocab.get(gram, -1)
    if index == -1:
      # The additional buckets are implemented as indices following the indices
      # reserved for the vocabulary.
      index = int(
          int(hashlib.md5(gram).hexdigest(), 16) %
          self._additional_buckets) + max(self._vocab_size, self._idf_size)
    return index

  @property
  def dtype(self):
    """Retrieves the data type produced by this transform.

    Returns:
      'float' if tf-idf or if normalize is true; int otherwise.
    """
    if self._idf or self._normalize:
      return 'float'
    return 'int64'


# TODO(b/31396263) Word2vec should probably also use BagOfWordsTransform
# and only use word2vec as the encoding option.
@_registries.register_transformer('word2vec', 'word2vec')
class Word2VecTransform(ColumnTransform):
  """Word To Vector Transform."""

  @staticmethod
  def from_metadata(column):
    return Word2VecTransform(column['word2vec']['word2vec_dict'],
                             column['word2vec']['split_regex'],
                             column['word2vec']['stop_words'],
                             column['word2vec']['use_stemmer'],
                             column['word2vec']['max_doc_size'],
                             column['word2vec']['ngrams'],
                             column['word2vec']['strip_html'],
                             column['word2vec']['removable_tags'])

  def __init__(self,
               word2vec_dict,
               split_regex=r'\w{1,}',
               stop_words=None,
               use_stemmer=False,
               max_doc_size=1000,
               ngrams=1,
               strip_html=False,
               removable_tags=None):
    self._word2vec_dict = word2vec_dict
    self._split_regex = split_regex
    self._stop_words = stop_words
    self._use_stemmer = use_stemmer
    self._max_doc_size = max_doc_size
    self._ngrams = ngrams
    self._strip_html = strip_html
    self._removable_tags = removable_tags
    self._tokenize_fn = None

  def _tokenize(self, text):
    """Tokenize text.

    Tokenize will always return empty array if the input string is '' or None.

    Args:
      text: string to be tokenized.
    Returns:
      An sequence representing the tokenized string.
    """
    # Functions cannot be serialized, lazy initialize here.
    if not self._tokenize_fn:
      self._tokenize_fn = _tokenizer.create_flat_tokenizer(
          split_regex=self._split_regex,
          stop_words=self._stop_words,
          use_stemmer=self._use_stemmer,
          ngrams=self._ngrams,
          strip_html=self._strip_html,
          removable_tags=self._removable_tags)
    return self._tokenize_fn(text)

  def transform(self, text):
    """Convert text into a matrix of vectors according to the dictionary."""
    tokenized = self._tokenize(text)
    vector_size = len(self._word2vec_dict[self._word2vec_dict.keys()[0]])
    array = np.zeros((self._max_doc_size, vector_size))
    i = 0

    for word in tokenized:
      vector = self._word2vec_dict.get(word, False)
      if vector:
        array[i] = vector
        i += 1
        if i == self._max_doc_size:
          logging.warning('Document was cropped to %d words.',
                          self._max_doc_size)
          return array

    return array

  @property
  def feature_type(self):
    return 'dense'

  @property
  def feature_size(self):
    embedding_size = len(self._word2vec_dict[self._word2vec_dict.keys()[0]])
    return self._max_doc_size * embedding_size


@_registries.register_transformer('image', 'image')
class ImageTransform(ColumnTransform):
  """Column Transform Class to process images. Options to Resize and Grayscale.
  """

  @staticmethod
  def from_metadata(column):
    return ImageTransform(column['image']['target_size'],
                          column['image']['resize_method'],
                          column['image']['grayscale'],
                          column['image']['keep_aspect_ratio'],
                          column['image']['is_base64_str'],
                          column['image']['save_dir'],
                          column['image']['save_format'])

  def __init__(self,
               target_size=(256, 256),
               resize_method=Image.ANTIALIAS,
               grayscale=False,
               keep_aspect_ratio=False,
               is_base64_str=False,
               save_dir=None,
               save_format='JPEG'):
    """Initializes the Image Transform class. Returns numpy array of image.

    Args:
      target_size: tuple (int, int) width x length in pixels. All images
        should be the same size, so this has to be defined.
      resize_method: Defines resampling method. eg Image.NEAREST
                    http://pillow.readthedocs.io/en/3.1.x/reference/Image.html
      grayscale: boolean - weather the returned images should be in grayscale,
                and therefore be 2 dimensional arrays
      keep_aspect_ratio: Boolean, if True, target size will be adjusted to
        maintain aspect ratio of image.
      is_base64_str: Boolean, if provided data is not a uri to image, but
        the base64 string of the image instead.
      save_dir: uri of directory images should be saved. If None, it indicates
        that images will not be saved as images anywhere (only tfrecord)
      save_format: if save dir is a uri, define what format images should be
        saved as. eg 'JPEG' or 'PNG'
    Raises:
      ValueError: If self._target_size is not a tuple or list of size 2.
    """
    # target size is a tuple of width x length
    self._target_size = target_size
    if not (isinstance(self._target_size, (tuple, list)) and
            len(self._target_size) == 2):
      raise ValueError(
          'Invalid image size %s. Needs to be tuple or list.' %
          str(self._target_size))
    self._resize_method = resize_method
    self._grayscale = grayscale
    self._keep_aspect_ratio = keep_aspect_ratio
    self._is_base64_str = is_base64_str
    self._save_dir = save_dir
    self._save_format = save_format

  def transform(self, image):
    """Transforms image and returns bytes. If needed saves file as well.

    Args:
      image: can be a uri to local or cloud location or the base64 string of an
      image.
    Returns:
      image as numpy array.
    """
    if self._is_base64_str:
      image_bytes = image.decode('base64')
      image_name = hashlib.md5(image).hexdigest()
    else:
      image_name = image
      image_bytes = self._open(image)

    try:
      im = Image.open(cStringIO(image_bytes))
    except IOError:
      log_str = 'with md5 ' if self._is_base64_str else ''
      logging.exception('Error processing image %s%s', log_str, image_name)

    if self._grayscale:  # make grayscale
      im = im.convert('L')
    else:
      im = im.convert('RGB')

    if self._keep_aspect_ratio:  # resize
      target_size = self._get_target_size(im.size[0], im.size[1])
    else:
      target_size = self._target_size
    im = im.resize(target_size, self._resize_method)

    output = cStringIO()
    _ = im.save(output, 'JPEG')

    if self._save_dir:
      new_image_uri = self._get_new_uri(image_name)
      self._save_image(im, new_image_uri, output)

    return [output.getvalue()]

  def _open(self, uri, mode='rb'):
    try:
      if uri.startswith('gs://'):
        return gcsio.GcsIO().open(uri, mode).read()
      else:
        return open(uri, mode).read()
    except IOError:
      logging.exception('Error processing image %s', uri)

  def _get_target_size(self, width, height):
    max_width = float(self._target_size[0])
    max_height = float(self._target_size[1])
    ratio = min(max_width / width, max_height / height)
    return (int(ratio * width), int(ratio * height))

  def _save_image(self, im, uri, jpeg_output, mode='wb'):
    if self._save_format != 'JPEG':
      output = cStringIO()
      im.save(output, self._save_format)
    else:
      output = jpeg_output
    image_bytes = output.getvalue()
    try:
      if uri.startswith('gs://'):
        fw = gcsio.GcsIO().open(uri, mode)
      else:
        fw = open(uri, mode)
      fw.write(image_bytes)
      fw.close()
    except IOError:
      logging.exception('Error saving image %s', uri)

  def _get_new_uri(self, old_image_name):
    """Creates the new image name. 'preprocessed_'+old_image_name+ extension.

    If Image was a string of base64, then old_image_name is a random string
    of numbers.
    Args:
      old_image_name: original image file or random string.
    Returns:
      String: New image name
    """
    image_name = os.path.basename(old_image_name)  # remove directory info
    image_name = os.path.splitext(image_name)[0]  # remove extension info

    image_name = 'preprocessed_%s.%s' % (image_name, self._save_format.lower())
    image_name = os.path.join(self._save_dir, image_name)
    return image_name

  @property
  def feature_type(self):
    return 'dense'

  @property
  def feature_size(self):
    # TODO(user) This is an under-estimation of the size of bytes
    # an image with JPEG format has.
    return self._target_size[0] * self._target_size[1] * 8

  @property
  def dtype(self):
    return 'bytes'


def _metadata_column_transforms(metadata):
  """Generates transformation classes for every column listed in the metadata.

  Creates a dictionary of column_name -> transform function mappings from
  metadata.

  Args:
    metadata: the metadata generated during analysis that drive the
      transformation logic.

  Returns:
    A dictionary of column names to transformer classes.
  """
  sorted_metadata_columns = _sorted_columns_from_metadata(metadata)
  transforms = {}
  for index, column in enumerate(sorted_metadata_columns):
    column_name = column['name']
    transforms[column_name] = (
        index, _registries.transformation_registry.get_transformer(column))
  return transforms


def sorted_columns_from_features(features):
  """Sort feature columns by name to ensure the order is consistent."""
  feature_columns = []
  for feature in features:
    feature_columns.extend(feature.columns)
  return sorted(feature_columns, key=lambda column: column.name)


def _sorted_columns_from_metadata(metadata):
  """Sort metadata columns by name to ensure the order is consistent."""
  columns = metadata.get('columns', {})
  return sorted(columns.itervalues(), key=lambda value: value['name'])


class DictionaryToTupleBase(object):
  """Base class to extract an instance tuple form an instance dictionary."""

  def __init__(self, column_ordering):
    """Initialize with the correct expected feature column ordering.

    Args:
      column_ordering: The expected feature column ordering.
    """
    self._column_ordering = column_ordering

  def columns_to_tuple(self, record):
    """Transforms and filters the input record dictionary into a dense tuple.

    Features coming from JSON can still have absent values which we replace
    with None.

    Args:
      record: Dictionary of column names to values.
    Returns:
      A tuple containing the feature columns values for each record, None is
      used when no value is found for that feature column.
    """
    return tuple(record.get(column_name, None)
                 for column_name in self._column_ordering)


class DictionaryToTupleFromMetadata(DictionaryToTupleBase):
  """Extract values from all feature columns."""

  def __init__(self, metadata):
    sorted_columns = _sorted_columns_from_metadata(metadata)
    column_ordering = [column['name'] for column in sorted_columns]
    super(DictionaryToTupleFromMetadata, self).__init__(column_ordering)


class SequenceToTupleBase(object):
  """Base class to extract a feature tuple form a feature sequence."""

  def __init__(self, source_column_headers, sorted_feature_column_names,
               target_column):
    """Initialize with the correct expected feature column ordering.

    Args:
      source_column_headers: List of headers as they appear on the original csv.
      sorted_feature_column_names: The expected feature column ordering.
      target_column: String to indicate the name of the target column if any.
    """
    self._headers_length = len(source_column_headers)
    column_indexes = {
        header: index
        for index, header in enumerate(source_column_headers)}
    self._feature_column_mapping = [
        column_indexes[column_name]
        for column_name in sorted_feature_column_names]

    # TODO(b/32802556) update this code once we have a consistent treatment of
    # the target columns.
    headers_without_target = [
        header
        for header in source_column_headers
        if header != target_column]
    column_indexes_without_target = {
        header: index
        for index, header in enumerate(headers_without_target)}
    self._feature_column_mapping_without_target = [
        column_indexes_without_target[column_name]
        if column_name != target_column
        else None
        for column_name in sorted_feature_column_names]

  def columns_to_tuple(self, record):
    """Transforms and filters the input record sequence into a tuple.

    Args:
      record: A sequence containing the input values.
    Returns:
      A tuple containing the feature columns values for each record, None is
      used when no value is found for that feature column.
    """
    # Use the size of the record to determine if the dataset contains the target
    # column.
    if len(record) < self._headers_length:
      sorted_feature_column_indexes = (
          self._feature_column_mapping_without_target)
    else:
      sorted_feature_column_indexes = self._feature_column_mapping
    return tuple(
        record[column_index] if column_index is not None else None
        for column_index in sorted_feature_column_indexes)


class SequenceToTupleFromMetadata(SequenceToTupleBase):
  """Extract values from all feature columns."""

  def __init__(self, metadata):
    sorted_columns = _sorted_columns_from_metadata(metadata)
    sorted_feature_column_names = [column['name'] for column in sorted_columns]
    source_column_headers = metadata['csv']['headers']
    target_column = None
    for column in metadata['columns'].values():
      if column['type'] == 'target':
        target_column = column['name']
        break
    super(SequenceToTupleFromMetadata, self).__init__(
        source_column_headers, sorted_feature_column_names, target_column)


def _get_value_from_instance(instance, transformer_index, column_metadata):
  """Get column_name value from instance."""
  # The dictionary to tuple transformation on preprocessing guarantees that an
  # (possibly None) entry will exist on the instance vector for each
  # feature column.
  value = instance[transformer_index]
  if value is not None:
    return value

  default_value = column_metadata.default
  if default_value is not None:
    return default_value

  column_metadata_type = column_metadata.type
  if column_metadata_type == _features.FeatureTypes.CATEGORICAL:
    # '' replaces missing values for categorical features
    return ''

  if column_metadata_type == _features.FeatureTypes.NUMERIC:
    # For numeric columns, default to the mean if the value is missing
    # and a default wasn't specified
    return column_metadata.mean

  # Check if the column is target at the end, since there would likely be less
  # target columns than feature columns.
  if column_metadata_type == _features.FeatureTypes.TARGET:
    # OK for target to be missing (eg. prediction data)
    return None

  raise ValueError(
      'Missing value encountered, and default for %s is None' %
      column_metadata.name)


class _TransformerWithMetadata(object):
  """A transformer object with column metadata."""

  def __init__(self, transformer_index, transformer, column_metadata):
    self._transformer = transformer
    self.transformer_index = transformer_index
    self.column_metadata = column_metadata

    # While we are here cache the following transformer properties:
    self.transformed_value_is_tuple = transformer._value_is_tuple()  # pylint: disable=protected-access
    self.feature_type = transformer.feature_type
    self.feature_size = transformer.feature_size

  def get_value_and_transform(self, instance):
    """Retrieve the value from the instance and transform it into a vector."""
    value = _get_value_from_instance(
        instance, self.transformer_index, self.column_metadata)
    return self._transformer.transform(value)


class _OptimizedColumnMetadata(object):
  """Optimized (cached) column metadata."""

  def __init__(self, column_name, column_metadata):
    self.name = column_name
    self.default = column_metadata.get('default', None)
    self.type = column_metadata['type']
    self.mean = column_metadata.get('mean', None)
    if self.type == _features.FeatureTypes.NUMERIC and self.default is None:
      assert self.mean is not None, (
          'Column %s is of type Numeric and does not have a '
          'mean value.' % column_name)


class _OptimizedMetadata(object):
  """Optimized metadata."""

  def __init__(self, feature_name, dtype, to_feature_vector_fn,
               is_target_feature, transformers):
    self.feature_name = feature_name
    self.dtype = dtype
    self.to_feature_vector_fn = to_feature_vector_fn
    self.transformers = transformers
    self.is_target_feature = is_target_feature


def _assert_transform_types_are_compatible(feature_metadata_type,
                                           transformer_feature_type):
  """Assert that the transformer is dense if the feature is dense."""
  assert transformer_feature_type in ('dense', 'sparse')
  if feature_metadata_type == 'dense':
    assert transformer_feature_type == 'dense', (
        'Transformer type should be dense when the feature is dense.')


def _is_target_feature(column_names, column_mapping):
  """Assert that a feature only contains target columns if it contains any."""
  column_names_set = set(column_names)
  column_types = set(column['type']
                     for column_name, column in column_mapping.iteritems()
                     if column_name in column_names_set)
  if 'target' in column_types:
    assert len(column_types) == 1, (
        'Features with target columns can only contain target columns.'
        'Found column_types: %s for columns %s' % (column_types,
                                                   column_names))
    return True
  else:
    return False


def _make_dense_feature_vector(instance, transformers):
  """Make dense feature vector with value as elements."""
  if len(transformers) == 1:
    # The feature has only one source column.
    transformer = transformers[0]
    return transformer.get_value_and_transform(instance)
  else:
    feature_vector = []
    for transformer in transformers:
      feature_vector.extend(transformer.get_value_and_transform(instance))
    return feature_vector


def _make_sparse_feature_vector(instance, transformers):
  """Make sparse feature vector with tuple(value, weight) as elements."""

  if len(transformers) == 1:
    # The feature has only one source column.
    transformer = transformers[0]
    transformed_value = transformer.get_value_and_transform(instance)
    if transformer.feature_type == 'dense':
      return enumerate(transformed_value)
    else:
      # If this column is not getting combined with any other column (as
      # is usually the case for 'target' features), we just return the
      # transformed_value directly since it's of the form
      # [idx1, idx2, ...]
      return transformed_value
  else:
    feature_vector = []
    total_feature_size = 0
    for transformer in transformers:
      transformed_value = transformer.get_value_and_transform(instance)
      # Transformed value is always a sequence either dense or sparse.
      # So checking for 'if transformed_value' is a valid check.
      if transformed_value:
        if transformer.feature_type == 'dense':
          tuple_list = enumerate(transformed_value, start=total_feature_size)
        else:
          # Categorical features can be represented as either [(idx1, count),
          # (idx2, count), ...] or as just [idx1, idx2]
          if transformer.transformed_value_is_tuple:
            tuple_list = [(idx + total_feature_size, value)
                          for (idx, value) in transformed_value]
          else:
            tuple_list = [(idx + total_feature_size, 1)
                          for idx in transformed_value]
      else:
        tuple_list = []

      total_feature_size += transformer.feature_size
      feature_vector.extend(tuple_list)

    return feature_vector


# This class runs in a tight loop, please run the following if you change it.
# //third_party/py/google/cloud/ml:benchmark_feature_transformer_test
class FeatureTransformer(object):
  """Standalone functionality to transform features into processed feature data.

  This provides functionality to transform instances in both training and
  prediction phases, so it is consistent, and usable from a variety of
  environments (in applications and data processing pipelines).
  """

  def __init__(self, metadata):
    """Initializes an instance of a FeatureTransformer.

    Args:
      metadata: the metadata object generated by the analysis phase.
    """
    # These optimizations allow us to do fewer lookups on the tight loop.
    self._optimized_metadata = []

    column_mapping = metadata.get('columns', {})
    transformers = _metadata_column_transforms(metadata)
    for feature_name, feature_metadata in metadata.get('features',
                                                       {}).iteritems():
      feature_metadata_type = feature_metadata['type']
      is_target_feature = _is_target_feature(
          feature_metadata['columns'], column_mapping)
      assert feature_metadata_type in ('dense', 'sparse')
      transformers_with_metadata = []
      for column_name in feature_metadata['columns']:
        transformer_index, transformer = transformers[column_name]
        _assert_transform_types_are_compatible(
            feature_metadata_type, transformer.feature_type)

        column_metadata = _OptimizedColumnMetadata(
            column_name, column_mapping[column_name])
        transformer_with_metadata = _TransformerWithMetadata(
            transformer_index,
            transformer,
            column_metadata)
        transformers_with_metadata.append(transformer_with_metadata)

      if feature_metadata_type == 'dense':
        to_feature_vector_fn = _make_dense_feature_vector
      else:
        to_feature_vector_fn = _make_sparse_feature_vector

      self._optimized_metadata.append(
          _OptimizedMetadata(feature_name, feature_metadata['dtype'],
                             to_feature_vector_fn, is_target_feature,
                             transformers_with_metadata))

  def transform(self, instance):
    """Make feature vectors from instance."""
    feature_vectors = {}

    for optimized_metadata in self._optimized_metadata:
      feature_vector = optimized_metadata.to_feature_vector_fn(
          instance, optimized_metadata.transformers)

      if not feature_vector:
        # Skip this feature column if there are no transformed features.
        continue
      # TODO(b/32802556) For now this can only happen on the target column.
      # Revisit when we handle target columns correctly. Note that something
      # on this lines might be needed as we preserve None values for the
      # features (b/31770163).
      if (optimized_metadata.is_target_feature and
          all(v is None for v in feature_vector)):
        # Target features can be all Nones if absent, skip the feature.
        continue
      feature_vectors[optimized_metadata.feature_name] = (
          optimized_metadata.dtype, feature_vector)

    return feature_vectors


def cached_property(f):
  """Like Python's @property, but memoized."""
  cached_name = '_' + f.__name__
  uncomputed = object()
  def getter(self):
    value = self.__dict__.get(cached_name, uncomputed)
    if value is uncomputed:
      self.__dict__[cached_name] = value = f(self)
    return value
  return property(getter, doc=f.__doc__)


class FeatureVector(object):
  """Represents a preprocessed feature vector, for training or prediction."""

  _proto_formatter = ExampleProtoFormatter()

  def __init__(self, data):
    """Polymorphic constructor of a FeatureVector.

    Args:
      data: One of
        - str: A serialized representation of an ExampleProto.
        - dict: A dictionary representation compatible (as input) to an
          ExampleProtoFormatter, or produced by TfTransform.
        - FeatureVector: Another FeatureVector.
        - tf.ExampleProto: An ExampleProto.
    """
    if isinstance(data, str):
      self._serialized_example_proto = data
    elif isinstance(data, FeatureVector):
      self._serialized_example_proto = data.serialized_example_proto
    elif isinstance(data, dict):
      if data and isinstance(next(data.itervalues()), tuple):
        # The dictionary is one created by the current SDK.
        self._feature_dict = data
      else:
        # The dictionary is one created by TfTransform, so we need to translate
        # it. The most natural mapping is to an Example proto.
        #
        # TODO(user): Update this to properly handle SparseFeature once the
        # representation of those is finalized (b/33692353).
        self._example_proto = self._make_example_proto(data)
    else:
      import tensorflow as tf  # pylint: disable=g-import-not-at-top
      if isinstance(data, tf.train.Example):
        self._example_proto = data
      else:
        raise TypeError(type(data))

  # TODO(user) eventually move to a schema based encoding.
  def _make_example_proto(self, tf_transform_dict):
    """Construct a tf.learn.Example that corresponds to a TfTransform dict."""
    import tensorflow as tf  # pylint: disable=g-import-not-at-top
    result = tf.train.Example()
    feature_map = result.features.feature
    for column, values in tf_transform_dict.iteritems():
      if not isinstance(values, (list, np.ndarray)):
        # Create an array from the scalar value.
        values = [values]
      first_value = values[0]
      feature = feature_map[column]
      if isinstance(first_value, (np.integer, int, long)):
        feature.int64_list.value.extend(values)
      elif isinstance(first_value, (np.floating, float)):
        # TODO(b/33432974, b/32200112): Remove the "map" part of this once
        # protobuf 3.2.0 is savailable in Dataflow and CloudML containers.
        feature.float_list.value.extend(map(float, values))
      else:
        feature.bytes_list.value.extend(values)
    return result

  @cached_property
  def serialized_example_proto(self):
    return self.example_proto.SerializeToString()

  @cached_property
  def example_proto(self):
    serialized_str = getattr(self, '_serialized_example_proto', None)
    if serialized_str is not None:
      import tensorflow as tf  # pylint: disable=g-import-not-at-top
      example = tf.train.Example()
      example.ParseFromString(serialized_str)
      return example
    else:
      return self._proto_formatter.format(self.feature_dict)

  def SerializeToString(self):  # pylint: disable=invalid-name
    return self.serialized_example_proto

  @cached_property
  def feature_dict(self):
    # TODO(user): Allow conversion back to feature dicts.
    return self._feature_dict

  def __eq__(self, other):
    # TODO(user): Try comparing against commonly set attributes, if any.
    if isinstance(other, FeatureVector):
      # Compare the parsed, not the serialized versions of the example protos
      # since the order of the serialized proto map fields is non-deterministic.
      return self.example_proto == other.example_proto
    else:
      # Allow comparison against ExampleProtos directly.
      return self.example_proto == other

  def __ne__(self, other):
    return not self == other

  # TODO(user): Is this still required now that we have registered a coder?
  def __reduce__(self):
    """Pickle helper.

    Pickle self by just storing the serialized representation.

    Returns:
         pickle data
    """
    return FeatureVector, (self.serialized_example_proto,)

  def __repr__(self):
    return unicode(self.example_proto)


# Register coder for this class.
coders.registry.register_coder(FeatureVector,
                               ml_coders.FeatureVectorOrExampleCoder)
