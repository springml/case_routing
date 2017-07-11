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
"""Implements Feature modeling functionality.
"""

import re

from PIL import Image

from google.cloud.ml.io.coders import MetadataCoder


class Scenario(object):

  DISCRETE = 'discrete'
  CONTINUOUS = 'continuous'


class FeatureFormat(object):
  """Supported feature formats for raw/input datasets (before preprocessing).
  """
  CSV = 'csv'
  JSON = 'json'


class FeatureTypes(object):
  """The supported set of feature types.
  """
  KEY = 'key'
  TARGET = 'target'
  NUMERIC = 'numeric'
  CATEGORICAL = 'categorical'
  TEXT = 'text'
  IMAGE = 'image'


class FeatureTransforms(object):
  """The list of supported transformations that can be applied to values.
  """
  IDENTITY = 'identity'
  SCALE = 'scale'
  BAG_OF_WORDS = 'bag_of_words'
  LOOKUP = 'lookup'
  KEY = 'key'
  DISCRETIZE = 'discretize'
  BINARIZE = 'binarize'
  IMAGE = 'image'
  WORD2VEC = 'word2vec'


class BagOfWordsEncodings(object):
  """List of output encodings that can be applied to a BOW transform.
  """
  SPARSE = 'sparse'
  ONE_HOT = 'one_hot'
  # TODO(b/31396263) eventually word2vec should be a BOW encoding.


class Feature(object):
  """Corresponds to a feature vector comprised of one or more values.
  """

  def __init__(self, name, columns):
    self._name = name
    self._columns = columns

  @property
  def name(self):
    return self._name

  @property
  def columns(self):
    return self._columns


class FeatureColumn(object):
  """Base class for different column values making up a Feature.
  """

  def __init__(self, name, value_type, sampling_percentage=100, default=None):
    self._name = name
    self._type = value_type
    self._sampling_percentage = sampling_percentage
    self._transform = None
    self._transform_args = None
    self._default = default

  @property
  def name(self):
    """Retrieves the name of the column.

    Returns:
      The name of the column.
    """
    return self._name

  @property
  def value_type(self):
    """Retrieves the type of value contained in the column.

    Returns:
      The data type of the values in this column.
    """
    return self._type

  @property
  def transform(self):
    """Retrieves the transformation to be applied.

    Returns:
      The type of the transform to perform.
    """
    return self._transform

  @property
  def transform_args(self):
    """Retrieves the transformation arguments.

    Returns:
      A dictionary containing args for this transform.
    """
    return self._transform_args

  @property
  def is_numeric(self):
    """Returns whether a column is numeric.

    Returns:
      True if the feature is numeric.  Defaults to False.
    """
    return False

  @property
  def exclusive(self):
    """Returns whether the column must be within a feature by itself.

    Features such as ids, target, and sparse values must be within a feature by
    themselves.

    Returns:
      True if the feature is exclusive.  Defaults to False.
    """
    return False

  @property
  def default(self):
    """Returns the default value for this column.

    This is required during feature extraction when this feature-column is being
    transformed into a feature vector. If the value is missing from a row, then
    this default value is used instead. If this default is None however, then
    the transform should throw an error.

    Returns:
      The specified default value associated with the column.
    """
    return self._default

  @property
  def sampling_percentage(self):
    return self._sampling_percentage

  def identity(self):
    """Clears out the default transformation, so the actual value is used.

    Returns:
      This FeatureColumn.
    """
    self._set_transformation(FeatureTransforms.IDENTITY, {'dtype': 'float'})
    return self

  def _set_transformation(self, transform, transform_args):
    self._transform = transform
    self._transform_args = transform_args


class KeyFeatureColumn(FeatureColumn):
  """Represents a value that identifies the instance.
  """

  def __init__(self, name):
    super(KeyFeatureColumn, self).__init__(name, FeatureTypes.KEY)
    self._set_transformation(FeatureTransforms.KEY, None)

  @property
  def exclusive(self):
    return True


class TargetFeatureColumn(FeatureColumn):
  """Represents a value that is the target value associated with the instance.
  """

  def __init__(self, name):
    super(TargetFeatureColumn, self).__init__(name, FeatureTypes.TARGET)
    self._scenario = None

  def discrete(self):
    """Indicates this is a target column for a classification-like scenario.

    Returns:
      This FeatureColumn.
    """
    self._scenario = Scenario.DISCRETE
    self._set_transformation(FeatureTransforms.LOOKUP, None)
    return self

  def continuous(self):
    """Indicates this is a target column for a regression-like scenario.

    Returns:
      This FeatureColumn.
    """
    self._scenario = Scenario.CONTINUOUS
    self._set_transformation(FeatureTransforms.IDENTITY, {'default': 0.0})
    return self

  @property
  def exclusive(self):
    return True

  @property
  def scenario(self):
    return self._scenario

  @property
  def is_numeric(self):
    return self._scenario == Scenario.CONTINUOUS


class NumericFeatureColumn(FeatureColumn):
  """Represents a numeric value.
  """

  def __init__(self, name, default=None, log_base=0):
    if default is not None:
      if not isinstance(default, (float, int, type(None))):
        raise ValueError(
            'Default value for NumericFeatureColumn must be float or int.'
            ' Instead got %s (type:%s)' % (default, type(default)))

    super(NumericFeatureColumn, self).__init__(name, FeatureTypes.NUMERIC,
                                               default=default)
    self._log_base = log_base
    self.identity()

  def max_abs_scale(self, value):
    """Indicates value should be scaled to the range [-value, value].

    Args:
      value: The maximum absolute value of this feature.

    Returns:
      This FeatureColumn.
    """
    self._set_transformation(FeatureTransforms.SCALE,
                             {'min': -value,
                              'max': value,
                              'log_base': self._log_base})
    return self

  def discretize(self, buckets, sparse=True):
    """Zero-based index of bucket for the given value in the range [min, max].

    Args:
      buckets: The number of buckets.
      sparse: Whether the output is sparse, or one-hot vector representation.

    Returns:
      This FeatureColumn.
    """
    self._set_transformation(FeatureTransforms.DISCRETIZE, {'buckets': buckets,
                                                            'sparse': sparse})
    return self

  def binarize(self, threshold):
    """Zero if value is strictly less than the threshold; one otherwise.

    Args:
      threshold: Threshold for binarizing

    Returns:
      This FeatureColumn.
    """
    self._set_transformation(FeatureTransforms.BINARIZE,
                             {'threshold': threshold})
    return self

  def scale(self):
    return self.max_abs_scale(1)

  def identity(self, dtype='float'):
    self._set_transformation(FeatureTransforms.IDENTITY, {'dtype': dtype})
    return self

  @property
  def is_numeric(self):
    return True

  @property
  def log_base(self):
    return self._log_base


class CategoricalFeatureColumn(FeatureColumn):
  """Represents a discrete value.

  By default, categorical values are encoded into a sparse encoding.
  """

  _TOKENIZER_ARGS = {
      'buckets': 1,
      'normalize': False,
      'stop_words': None,
      'use_stemmer': False,
      'ngrams': 1,
      'strip_html': False,
      'removable_tags': None}

  # TODO(user) remove the default values from the no-public classes
  # since all the values are being set by the calling sites.
  def __init__(self, name, default=None, frequency_threshold=5,
               split_regex=None):
    if default is not None and not isinstance(default, (basestring)):
      raise ValueError(
          'Default value for CategoricalFeatureColumn must be string.'
          ' Instead got %s (type:%s)' % (default, type(default)))

    super(CategoricalFeatureColumn, self).__init__(name,
                                                   FeatureTypes.CATEGORICAL,
                                                   default=default)
    self._frequency_threshold = frequency_threshold
    # Validate early that the split_regex is valid when not None.
    if split_regex is not None:
      re.compile(split_regex)
    self._split_regex = split_regex
    self.sparse()

  def one_of_k(self, use_counts=False):
    """Indicates a one-of-k represenation should be used.

    Values will be encoded as an array with every value set to zero except one.
    Not recommended for categories with a large number of possible values.

    Args:
      use_counts: whether to use counts as weights
    Returns:
      This FeatureColumn.
    """
    # TODO(user): Consider adding vocab_size
    self._tokenizer_args = dict(
        self._TOKENIZER_ARGS, **{
            'counts': use_counts,
            'split_regex': self._split_regex,
            'output_encoding': BagOfWordsEncodings.ONE_HOT})
    self._set_transformation(FeatureTransforms.BAG_OF_WORDS,
                             self._tokenizer_args)
    return self

  def sparse(self, use_counts=True):  # pylint: disable=unused-argument
    """Indicates a sparse bag of words representation should be used.

    Args:
      use_counts: whether to use counts as weights. This is unused because this
      was implemented incorrectly, without taking the consequences in
      FeaturesMetadata.parse_features into account. This has been set to True
      as default as a quick fix to b/34245622.
    Returns:
      This FeatureColumn.
    """
    # TODO(user): Consider adding vocab_size
    self._tokenizer_args = dict(
        self._TOKENIZER_ARGS, **{
            'counts': True,
            'split_regex': self._split_regex,
            'output_encoding': BagOfWordsEncodings.SPARSE})
    self._set_transformation(FeatureTransforms.BAG_OF_WORDS,
                             self._tokenizer_args)
    return self

  def identity(self):
    self._set_transformation(FeatureTransforms.IDENTITY, {'dtype': 'bytes'})
    self._tokenizer_args = None
    return self

  @property
  def tokenizer_args(self):
    return self._tokenizer_args

  @property
  def exclusive(self):
    return self.transform == FeatureTransforms.IDENTITY

  @property
  def frequency_threshold(self):
    return self._frequency_threshold

  @property
  def split_regex(self):
    return self._split_regex


class TextFeatureColumn(FeatureColumn):
  """Represents free-form text value.

  By default, text values are represented as a sparse bag of words
  representation.

  Attributes:
    stop_words: Either list or set, specifying the stop words to be ignored or a
      string representing the language of stopwords to be requested from nltk.
      Use [] for no stopwords. For more info nltk.corpus.stopwords.readme()
    split_regex: Regex rule to split text
    use_stemmer: Boolean on whether text should be stemmed
    ngrams: number of ngrams the tokenizer should generate (2 for bigrams etc)
    use_tf_idf: Boolean on whether the BOW representation should be tf*idf
    normalize: Boolean on whether sparse vector (BOW or tf*idf) should be
      normalize (used with L2 norm)
    strip_html: Boolean on whether html_markup should be removed before
      processing
    removable_tags: list of html tags whose text should be ignored
    word2vec_dict: Dictionary of word -> word_vectors. If it is not empty, then
      the words will be replaced with a matrix, one row for each word
  """

  # TODO(user): Consider support for All, and make it the default
  # TODO(user): Add hashing
  # TODO(user): Add support for min size
  def __init__(self,
               name,
               default=None,
               sampling_percentage=100,
               split_regex=r'\w{3,}',
               stop_words='english',
               use_stemmer=False,
               ngrams=1,
               use_tf_idf=False,
               normalize=False,
               strip_html=False,
               removable_tags=None,
               word2vec_dict=None,
               frequency_threshold=0):
    if not isinstance(default, (basestring, type(None))):
      raise ValueError('Default value for TextFeatureColumn must be a string.'
                       ' Instead got %s (type:%s)' % (default, type(default)))
    super(TextFeatureColumn, self).__init__(
        name, FeatureTypes.TEXT, default=default,
        sampling_percentage=sampling_percentage)
    self._stop_words = stop_words
    self._split_regex = split_regex
    self._use_stemmer = use_stemmer
    self._ngrams = ngrams
    self._use_tf_idf = use_tf_idf
    self._normalize = normalize
    self._strip_html = strip_html
    self._removable_tags = [] if removable_tags is None else removable_tags
    self._word2vec_dict = {} if word2vec_dict is None else word2vec_dict
    self._frequency_threshold = frequency_threshold
    self.bag_of_words()

  @property
  def stop_words(self):
    return self._stop_words

  @property
  def split_regex(self):
    return self._split_regex

  @property
  def use_stemmer(self):
    return self._use_stemmer

  @property
  def ngrams(self):
    return self._ngrams

  @property
  def use_tf_idf(self):
    return self._use_tf_idf

  @property
  def strip_html(self):
    return self._strip_html

  @property
  def removable_tags(self):
    return self._removable_tags

  @property
  def word2vec_dict(self):
    return self._word2vec_dict

  @property
  def frequency_threshold(self):
    return self._frequency_threshold

  def bag_of_words(self,
                   vocab_size=10000,
                   additional_buckets=1,
                   use_counts=False):
    """Indicates a sparse bag of words representation should be used.

    Args:
      vocab_size: How big should the column's vocabulary be.  Defaults to 10000.
      additional_buckets: How many buckets should be used for words that do not
        fit inside the column's vocabulary. Defaults to 1.
      use_counts: Should multiple instances of a word be included in the feature
        as a count.  Defaults to false.

    Returns:
      This FeatureColumn.
    """
    args = {'vocab_size': vocab_size,
            'buckets': additional_buckets,
            'counts': use_counts,
            'normalize': self._normalize,
            'split_regex': self._split_regex,
            'stop_words': self._stop_words,
            'use_stemmer': self._use_stemmer,
            'ngrams': self._ngrams,
            'strip_html': self._strip_html,
            'removable_tags': self._removable_tags}
    self._set_transformation(FeatureTransforms.BAG_OF_WORDS, args)
    return self

  def identity(self):
    self._set_transformation(FeatureTransforms.IDENTITY, {'dtype': 'bytes'})
    return self

  @property
  def exclusive(self):
    return self.transform == FeatureTransforms.IDENTITY

  def word2vec(self, word2vec_dict, split_regex=r'\w{3,}', use_stemmer=False):
    """Indicates a word2vec dictionary should be used, to convert to matrix.

    Args:
      word2vec_dict: Dictionary of word -> word_vectors. to be used
      split_regex: Regex to use to split the string
      use_stemmer: Wether to use the stemmer.
    Returns:
      This FeatureColumn.
    """
    self._word2vec_dict = word2vec_dict
    args = {'word2vec_dict': word2vec_dict,
            'split_regex': split_regex,
            'stop_words': self._stop_words,
            'use_stemmer': use_stemmer}
    self._set_transformation(FeatureTransforms.WORD2VEC, args)
    return self


class ImageFeatureColumn(FeatureColumn):
  """Represents an image value, with the value being a path to the image file.
  """

  def __init__(self, name, default=None):
    """Creates an image column within a feature.

    Args:
      name: name of image feature
      default: default value to use in case value is missing.

    Returns:
      An instance of ImageFeatureColumn.
    """
    super(ImageFeatureColumn, self).__init__(name, FeatureTypes.IMAGE,
                                             default=default)

    self.image()

  def identity(self):
    self._set_transformation(FeatureTransforms.IDENTITY, {'dtype': 'bytes'})
    return self

  @property
  def exclusive(self):
    return self.transform == FeatureTransforms.IDENTITY

  def image(self,
            target_size=None,
            resize_method=Image.ANTIALIAS,
            grayscale=False,
            keep_aspect_ratio=False,
            is_base64_str=False,
            save_dir=None,
            save_format='JPEG'):
    """Image transform.

    Args:
      target_size: tuple (int, int) width x length in pixels. None value
                  implies  no resizing will take place
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
    Returns:
      initialized transform.
    """
    args = {'target_size': target_size,
            'grayscale': grayscale,
            'resize_method': resize_method,
            'keep_aspect_ratio': keep_aspect_ratio,
            'is_base64_str': is_base64_str,
            'save_dir': save_dir,
            'save_format': save_format}
    self._set_transformation(FeatureTransforms.IMAGE, args)
    return self


class GraphOptions(object):
  """Internal helper to provide key.value syntax for user-specified dicts.
  """

  def __init__(self, *dicts):
    target = self.__dict__
    for d in dicts:
      if d:
        target.update(d)


class FeatureMetadata(object):
  """Provides functionality for loading and saving feature metadata.

  Feature metadata is produced by analyzing the training data along with a
  feature set definition, and then consumed during feature transformation.
  """

  # TODO(user): remove this method once we update the samples.
  @staticmethod
  def load_from(path):
    """Reads the metadata from the specified file path.

    Args:
      path: either a local path or a path to a GCS object.

    Returns:
      The metadata object to be used to perform transformation.
    """
    return MetadataCoder.load_from(path)

  @staticmethod
  def get_metadata(path):
    """Reads the metadata from the specified file path.

    Args:
      path: either a local path or a path to a GCS object.

    Returns:
      The metadata object as a GraphOptions.
    """
    metadata = MetadataCoder.load_from(path)
    # Include the stats at the top level, for backwards compatibility with
    # the previous GraphBuilder interface.
    metadata.update(metadata['stats'])
    return GraphOptions(metadata)

  @staticmethod
  def parse_features(metadata, examples, keep_target=True):
    """Parses examples into features based on this feature set.

    Args:
      metadata: The metadata dictionary. Uses both columns and features.
      examples: The tensor of serialized examples.
      keep_target: If true, the target feature is included. This is useful when
          training but should be set to False when evaluating a tensorflow
          model.
    Returns:
      A dictionary where each key is the feature name, and values are either a
      tensor for dense features, or a nested dictionary (with keys 'key' and
      'values') for sparse features. When a sparse feature named 'x' is used,
      the example is expected to have two feature elements: one named 'x@0' of
      type int64 and another named 'x@1' of type given by the feature x. That
      is, sparse features with more than 1 index are not supported.
    """
    # Importing tf locally so that we avoid conflicts with Dataflow.
    # TODO(user): Refactor this out to it's own file.
    import tensorflow as tf  # pylint: disable=g-import-not-at-top

    # TODO(user): Replace dictionary for sparse features with a single
    # SparseTensor
    dtype_mapping = {
        'bytes': tf.string,
        'float': tf.float32,
        'int64': tf.int64
    }

    def _is_target(feature_name):
      """Determines if a feature is the target feature.

      Args:
        feature_name: A key into the features dict of metadata.

      Returns:
        True if feature_name is the target feature, and False otherwise.
      """
      column_name = metadata.features[feature_name]['columns'][0]
      return metadata.columns[column_name]['type'] == 'target'

    example_schema = {}
    for feature_name, feature in metadata.features.iteritems():
      if not keep_target and _is_target(feature_name):
        continue

      size = feature['size']
      dtype = feature['dtype']

      if feature['type'] == 'dense':
        example_schema[feature_name] = tf.FixedLenFeature(
            shape=[size], dtype=dtype_mapping[dtype])
      else:
        example_schema[feature_name + '@0'] = tf.VarLenFeature(dtype=tf.int64)
        example_schema[feature_name + '@1'] = tf.VarLenFeature(dtype_mapping[
            dtype])

    parsed_features = {}
    parsed_examples = tf.parse_example(examples, example_schema)
    for feature_name, feature in metadata.features.iteritems():
      if not keep_target and _is_target(feature_name):
        continue
      if feature['type'] == 'dense':
        parsed_features[feature_name] = parsed_examples[feature_name]
      else:
        parsed_features[feature_name] = {
            'ids': parsed_examples[feature_name + '@0'],
            'values': parsed_examples[feature_name + '@1']
        }

    return parsed_features
