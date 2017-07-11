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
"""Prediction related classes and functions.
"""

import _transforms

from google.cloud.ml.io.coders import MetadataCoder
from google.cloud.ml.util import _decoders as decoders


class FeatureProducer(object):
  """Implements methods for doing preprocessing on single examples.

  Takes a single raw example in the input format, and perform the
  transformations learned during preprocessing, and outputs the new example in
  the feature format.

  The input format is given by the 'format' key in the metadata.
  """

  def __init__(self, metadata_or_path,
               formatter=_transforms.FeatureVectorFormatter()):
    assert isinstance(metadata_or_path, (str, dict))
    if isinstance(metadata_or_path, str):
      # It should be a metadata path.
      metadata = MetadataCoder.load_from(metadata_or_path)
    else:
      # It should be the metadata.
      metadata = metadata_or_path

    self._decoder, self._internal_transformer = self._get_decoder(metadata)
    self._predict_transformer = _transforms.FeatureTransformer(metadata)
    self._formatter = formatter

  def _get_decoder(self, metadata):
    """Create a decoder class to be used during file reads.

    Args:
      metadata: The metadata object created during analysis.

    Returns:
      A decoder class along with the corresponding internal transform.
    """
    if 'format' not in metadata:
      decoder = decoders.PassthroughDecoder()
      feature_to_tuple_transform = (
          _transforms.DictionaryToTupleFromMetadata(
              metadata))
    elif metadata['format'] == 'json':
      decoder = decoders.JsonDecoder()
      feature_to_tuple_transform = (
          _transforms.DictionaryToTupleFromMetadata(
              metadata))
    else:
      assert metadata['format'] == 'csv'
      # Create a list instance to drop the local column_names.
      column_names = list(metadata['csv']['headers'])
      numeric_column_names = set()
      for name, column in metadata['columns'].iteritems():
        if column['type'] == 'target':
          # We remove all target columns, as this Transformer only works on
          # prediction data, which does not have labels.
          column_names.remove(name)
        elif column['type'] == 'numeric':
          numeric_column_names.add(name)
      decoder = decoders.CsvDecoder(
          column_names, numeric_column_names,
          # TODO(b/32726166) don't use a default value for the delimiter.
          delimiter=metadata['csv'].get('delimiter', ','),
          decode_to_dict=False,
          fail_on_error=True,
          skip_initial_space=False)
      feature_to_tuple_transform = (
          _transforms.SequenceToTupleFromMetadata(metadata))
    return decoder, feature_to_tuple_transform

  def preprocess(self, instance):
    """Preprocess individual instances for prediction.

    Args:
      instance: A string containing an unpreprocessed example.

    Returns:
      Features using the specified formatter.
    """
    record = self._decoder.decode(instance)
    record_tuple = self._internal_transformer.columns_to_tuple(record)
    return self._formatter.format(
        self._predict_transformer.transform(record_tuple))
