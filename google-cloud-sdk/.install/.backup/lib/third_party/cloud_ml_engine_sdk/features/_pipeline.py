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
"""Transforms building up the pipeline.
"""

import traceback

import _transforms

import apache_beam as beam
from apache_beam.metrics import Metrics
from google.cloud.ml.util import _dataflow as dfutil


class TransformData(beam.PTransform):
  """A PTransform for transforming feature data during preprocessing.

  The input to this PTransform is a PCollection representing the source dataset,
  with each element of the collection being a dictionary. The keys of correspond
  to the columns referenced in the feature spec provided when constructing this
  transform.

  This PTransform also requires a singleton PCollection containing the metadata
  that was produced during analysis.
  """

  def __init__(self, metadata, error_threshold=0, return_bad_elements=False):
    """Initializes a TransformData instance.

    Args:
      metadata: The metadata generated during analysis within a PCollection
        instance.
      error_threshold: maximum number of malformed elements (as a ratio of
        total elements) to filter without aborting the entire pipeline
      return_bad_elements: whether to also return the PCollection of malformed
        elements for each input PCollection
    """
    super(TransformData, self).__init__()
    self._metadata = metadata
    self._error_threshold = error_threshold
    self._return_bad_elements = return_bad_elements

  # TODO(b/33677990): Remove apply method.
  def apply(self, data):
    return self.expand(data)

  def expand(self, data):

    features, errors = data | 'Transform' >> TransformDataFeatures(
        self._metadata,
        error_threshold=self._error_threshold,
        return_bad_elements=True)

    # format the features
    formatted_features = (features
                          | 'FormatDataFeaturesFn'
                          >> beam.ParDo(FormatDataFeaturesFn()))

    if self._return_bad_elements:
      return formatted_features, errors
    else:
      return formatted_features


class FormatDataFeaturesFn(beam.DoFn):
  """Format preprocessed featuress into FeatureVector objects."""

  def __init__(self):
    super(FormatDataFeaturesFn, self).__init__()
    self._formatter = _transforms.FeatureVectorFormatter()

  # TODO(user): Remove the try catch after sdk update
  def process(self, element):
    """Format features into FeatureVector objects.

    Args:
      element: Features as produced by TransformDataFeatures.

    Yields:
      The FeatureVector encoding of element.
    """
    try:
      element = element.element
    except AttributeError:
      pass
    yield self._formatter.format(element)


class TransformDataFeatures(beam.PTransform):
  """A PTransform for transforming feature data during preprocessing.

  The input to this PTransform is a PCollection representing the source dataset,
  with each element of the collection being a dictionary. The keys of correspond
  to the columns referenced in the feature spec provided when constructing this
  transform.

  This PTransform also requires two singleton PCollections.
  feature_metadata_map: Feature-name to feature-metadata mapping.
  column_transforms: The column transform functions to apply to each named
  column.
  """

  def __init__(self, metadata, error_threshold, return_bad_elements):
    """Initializes a TransformData instance.

    Args:
      metadata: The metadata generated during analysis within a PCollection
        instance.
      error_threshold: maximum number of malformed elements (as a ratio of
        total elements) to filter without aborting the entire pipeline
      return_bad_elements: whether to also return the PCollection of malformed
        elements for each input PCollection
    """
    super(TransformDataFeatures, self).__init__()
    self._metadata = metadata
    self._error_threshold = error_threshold
    self._return_bad_elements = return_bad_elements

  # TODO(b/33677990): Remove apply method.
  def apply(self, data):
    return self.expand(data)

  def expand(self, data):
    features, errors = data | 'Transform' >> beam.ParDo(
        TransformDataFn(self._error_threshold > 0),
        beam.pvalue.AsSingleton(self._metadata)).with_outputs(
            'errors', main='features')

    _ = (errors, data) | dfutil.CheckErrorThreshold(self._error_threshold)

    if self._return_bad_elements:
      return features, errors
    else:
      return features


class TransformDataFn(beam.DoFn):
  """The transformation function to input data and produce processed data.
  """

  def __init__(self, allow_errors):
    self._allow_errors = allow_errors
    self._counter = Metrics.counter(self.__class__, 'ml-extract-features')
    self._error_counter = Metrics.counter(self.__class__,
                                          'ml-extract-features-errors')

  # TODO(user): Remove the context param and try catch after sdk update
  def start_bundle(self, context=None):
    self._transformer = None

  def process(self, element, metadata):
    try:
      element = element.element
    except AttributeError:
      pass
    if self._transformer is None:
      # We would like to do this as part of start_bundle instead of lazy loading
      # but for now it doesn't support side inputs.
      # https://issues.apache.org/jira/browse/BEAM-1003
      self._transformer = _transforms.FeatureTransformer(metadata)

    self._counter.inc()
    try:
      yield self._transformer.transform(element)
    except Exception, exn:  # pylint: disable=broad-except
      self._error_counter.inc()
      if self._allow_errors:
        traceback.print_exc()
        try:
          yield beam.pvalue.TaggedOutput('errors', (exn, element))
        except AttributeError:
          yield beam.pvalue.SideOutputValue('errors', (exn, element))
      else:
        raise
