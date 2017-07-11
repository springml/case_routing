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
"""Classes for defining the data used to train machine learning models.

Data to be used in training, prediction and evaluation is described in terms of
features. This module provides functionality to define those features, and data
transformations to apply to produce those features.
"""

from _features import CategoricalFeatureColumn
from _features import Feature
from _features import FeatureColumn
from _features import FeatureFormat
from _features import FeatureMetadata
from _features import ImageFeatureColumn
from _features import KeyFeatureColumn
from _features import NumericFeatureColumn
from _features import TargetFeatureColumn
from _features import TextFeatureColumn
from _predict import FeatureProducer
from _registries import register_analyzer
from _registries import register_transformer
from _transforms import ExampleProtoFormatter
from _transforms import FeatureVector


def key(name):
  """Creates a feature representing the key of the instance.

  Args:
    name: Name of feature column.

  Returns:
    An instance of KeyFeatureColumn.
  """
  return KeyFeatureColumn(name)


def target(name='target'):
  """Creates a feature representing the target label or value of the instance.

  Args:
    name: Name of feature column.

  Returns:
    An instance of TargetFeatureColumn.
  """
  return TargetFeatureColumn(name)


def numeric(name, default=None, log_base=0):
  """Creates a numeric column within a feature.

  Args:
    name: Name of feature column.
    default: Default value for the column.
    log_base: Base of logarithm to be applied.

  Returns:
    An instance of NumericFeatureColumn.
  """
  return NumericFeatureColumn(name, default=default, log_base=log_base)


def categorical(name, default=None, frequency_threshold=5,
                split_regex=None):
  r"""Creates a categorical or discrete value column within a feature.

  Args:
    name: Name of feature column.
    default: Default value for the column.
    frequency_threshold: Frequency threshold below which words are not added to
      the vocab.
    split_regex: Regex rule to extract the column value. Defaults to None,
      which means no splitting.
      Examples:
      - Use r'\w{1,}' to group alphanumerical characters of len 1.
      - Use r'\w{3,}' to group alphanumerical characters of len 3.
      - Use r'\S+' to group on non-whitespace.

  Returns:
    An instance of CategoricalFeatureColumn.
  """
  return CategoricalFeatureColumn(name, default=default,
                                  frequency_threshold=frequency_threshold,
                                  split_regex=split_regex)


def text(name,
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
  """Creates a free-form text value column within a feature.

  Args:
    name: Name of feature column.
    default: Default value for the column.
    sampling_percentage: Percentage value (0-100) for the number of rows that
      should be sampled for constructing the vocabulary/ngrams.
    split_regex: Regex rule to split text
    stop_words: Either list or set, specifying the stop words to be ignored or a
      string representing the language of stopwords to be requested from nltk.
      Use [] for no stopwords. For more info nltk.corpus.stopwords.readme()
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
    frequency_threshold: Frequency threshold below which words/ngrams
      are not added to the vocab.

  Returns:
    An instance of TextFeatureColumn.
  """
  return TextFeatureColumn(
      name,
      default=default,
      sampling_percentage=sampling_percentage,
      split_regex=split_regex,
      stop_words=stop_words,
      use_stemmer=use_stemmer,
      ngrams=ngrams,
      use_tf_idf=use_tf_idf,
      normalize=normalize,
      strip_html=strip_html,
      removable_tags=removable_tags,
      word2vec_dict=word2vec_dict,
      frequency_threshold=frequency_threshold)


def image(name, default=None):
  """Creates an image column within a feature..

  Args:
    name: name of image feature
    default: Default value for the column.

  Returns:
    An instance of ImageFeatureColumn.
  """
  return ImageFeatureColumn(name, default=default)
