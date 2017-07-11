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
"""Classes for defining the analyzer and transformer registries.
"""
import _features


class AnalyzerRegistry(object):

  def __init__(self):
    self._column_type_to_analyzer = {}

  def register_analyzer(self, column_type, analyzer_cls):
    self._column_type_to_analyzer[column_type] = analyzer_cls

  def get_analyzer(self, column):
    """Gets the analyzer associated with the column.

    Args:
      column: The column's metadata

    Returns:
      A ColumnAnalyzer object
    """
    # importing here to avoid a circular dependency.
    # TODO(user): Move this import back out once the circle is resolved.
    import _analysis  # pylint: disable=g-import-not-at-top
    # One-off treatment for FeatureTypes.TARGET
    if column.value_type == _features.FeatureTypes.TARGET:
      if column.scenario == _features.Scenario.CONTINUOUS:
        return _analysis.NumericColumnAnalyzer(column)
      return _analysis.CategoricalColumnAnalyzer(column)

    analyzer_cls = self._column_type_to_analyzer.get(column.value_type, None)
    if analyzer_cls is None:
      return _analysis.IdentityColumnAnalyzer(column)
    return analyzer_cls(column)


class TransformerRegistry(object):
  """Registry of preprocessing column transformers.
  """

  def __init__(self):
    self._column_type_to_transformer = {}

  def register_transformer(self, column_type, transformer_type, tranformer_cls):
    if self._column_type_to_transformer.get(column_type, None) is None:
      self._column_type_to_transformer[column_type] = {}
    self._column_type_to_transformer[column_type][transformer_type] = (
        tranformer_cls)

  def get_transformer(self, column):
    """Gets the transformer associated with the column.

    Args:
      column: The column's metadata

    Returns:
      A ColumnTransform object
    """
    # importing here to avoid a circular dependency.
    # TODO(user): Move this import back out once the circle is resolved.
    import _transforms  # pylint: disable=g-import-not-at-top
    # One-off treatment for FeatureTypes.TARGET
    column_type = column['type']
    if (column_type == _features.FeatureTypes.TARGET and
        column.get('scenario') == _features.Scenario.DISCRETE):
      return _transforms.ValueToIndexTransform.from_metadata(column)

    # One-off treatment for KEY
    transformer_type = column.get('transform')
    if (column_type == _features.FeatureTypes.KEY or
        transformer_type == _features.FeatureTransforms.KEY):
      return _transforms.IdTransform.from_metadata(column)

    transformer_cls = self._column_type_to_transformer.get(
        column_type, {}).get(transformer_type, None)
    if transformer_cls is None:
      return _transforms.IdentityTransform.from_metadata(column)
    return transformer_cls.from_metadata(column)


analyzer_registry = AnalyzerRegistry()


def register_analyzer(column_type):
  def func(analyzer_cls):
    analyzer_registry.register_analyzer(column_type, analyzer_cls)
    return analyzer_cls
  return func


transformation_registry = TransformerRegistry()


def register_transformer(column_type, tranformer_type):
  def func(tranformer_cls):
    transformation_registry.register_transformer(column_type, tranformer_type,
                                                 tranformer_cls)
    return tranformer_cls
  return func
