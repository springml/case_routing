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
"""Classes for dealing with I/O from ML pipelines.
"""

import os

# pylint: disable=g-import-not-at-top
import apache_beam as beam
from apache_beam.coders.coders import Base64PickleCoder
try:
  from apache_beam.io.filebasedsink import DEFAULT_SHARD_NAME_TEMPLATE
except ImportError:
  from apache_beam.io import fileio
  DEFAULT_SHARD_NAME_TEMPLATE = fileio.DEFAULT_SHARD_NAME_TEMPLATE

from google.cloud.ml.dataflow.io import tfrecordio
from google.cloud.ml.io import coders as mlcoders

try:
  # TODO(user): Remove this after updating to latest Beam.
  from apache_beam.io.filesystem import CompressionTypes
except ImportError:
  from apache_beam.io.fileio import CompressionTypes


# TODO(user) rename these classes depending on what is said in
# b/31405800
class LoadMetadata(beam.PTransform):
  """A PTransform for loading feature metadata during preprocessing.
  """

  def __init__(self, path):
    """Initializes an instance of a LoadMetadata PTransform.

    Args:
      path: the local or GCS path to load metadata from.
    """
    super(LoadMetadata, self).__init__('Load Metadata')
    self._path = path

  def expand(self, pvalue):
    paths = pvalue.pipeline | beam.Create([self._path])
    return paths | 'Read' >> beam.Map(mlcoders.MetadataCoder.load_from)


class SaveMetadata(beam.PTransform):
  """A PTransform for loading feature metadata during preprocessing.
  """

  def __init__(self, path):
    """Initializes an instance of a SaveMetadata PTransform.

    Args:
      path: the local or GCS path to save metadata to.
    """
    super(SaveMetadata, self).__init__('Save Metadata')
    self._path = path

  def expand(self, metadata):
    # TODO(user): Switch to Map so its symmetric with LoadMetadata
    return metadata | 'Write' >> beam.io.textio.WriteToText(
        self._path, shard_name_template='', coder=mlcoders.MetadataCoder())


class SaveFeatures(beam.PTransform):
  """Save Features in a TFRecordIO format.
  """

  def __init__(self,
               file_path_prefix,
               file_name_suffix='.tfrecord.gz',
               shard_name_template=DEFAULT_SHARD_NAME_TEMPLATE,
               compression_type=CompressionTypes.AUTO):
    """Initialize SaveFeatures.

    SaveFeatures is a wrapper for WriteToTFRecord with defaults useful for the
    machine learning SDK.

    Args:

      file_path_prefix: The file path to write to. The files written will begin
        with this prefix, followed by a shard identifier
        (see shard_name_template), and end in a common extension, if given by
        file_name_suffix. In most cases, only this argument is specified.
      file_name_suffix: Suffix for the files written.
      shard_name_template: A template string containing placeholders for
        the shard number and shard count. Currently only '' and
        '-SSSSS-of-NNNNN' are patterns accepted by the service. Use '' for no
        sharding.
      compression_type: Used to handle compressed output files. Typical value
          is CompressionTypes.AUTO, in which case the file_path's extension will
          be used to detect the compression.
    """
    super(SaveFeatures, self).__init__('SaveFeatures')

    self._file_path_prefix = file_path_prefix
    self._file_name_suffix = file_name_suffix
    self._shard_name_template = shard_name_template
    self._compression_type = compression_type

  def expand(self, features):
    return (features
            | 'Write to %s' % self._file_path_prefix.replace('/', '_')
            >> tfrecordio.WriteToTFRecord(
                file_path_prefix=self._file_path_prefix,
                file_name_suffix=self._file_name_suffix,
                shard_name_template=self._shard_name_template,
                coder=mlcoders.FeatureVectorOrExampleCoder(),
                compression_type=self._compression_type))


class LoadFeatures(beam.PTransform):
  """Loads Features as written by SaveFeatures.
  """

  def __init__(
      self,
      file_pattern,
      compression_type=CompressionTypes.AUTO):
    """Initialize LoadFeatures.

    LoadFeatures is a wrapper for ReadFromTFRecord with defaults useful for the
    machine learning SDK.

    Args:
      file_pattern: The file pattern to read from as a local file path or a GCS
        gs:// path. The pattern can contain glob characters (*, ?, and [...]).
      compression_type: Used to handle compressed input files. Typical value
          is CompressionTypes.AUTO, in which case the file_path's extension will
          be used to detect the compression.
    """
    super(LoadFeatures, self).__init__('LoadFeatures')
    self._file_pattern = file_pattern
    self._compression_type = compression_type

  def expand(self, pvalue):

    return (pvalue.pipeline
            | tfrecordio.ReadFromTFRecord(
                file_pattern=self._file_pattern,
                coder=mlcoders.FeatureVectorOrExampleCoder(),
                compression_type=self._compression_type))


class SaveModel(beam.PTransform):
  """Copy a model to the given directory.

  Args:
    path: The local or GCS path to save the model to.
    extract_model_fn: A function to extract the model path from a file hierarchy
      like the one generated from tf.learn's `Estimator.export_savedmodel()`.
  Returns:
    A path to the saved model if extract_model_fn is present, otherwise a path
    to the old path + '.meta' for backwards compatibility.
  """

  def __init__(self, path, extract_model_fn=None):
    self._path = path
    self._extract_model_fn = extract_model_fn

  @staticmethod
  def from_tf_learn_hierarchy(export_name='Servo'):
    def extract_model_fn(trained_model_dir):
      """Extract Model."""
      # gcsio.glob() will return all the files under
      # <trained_model_dir>/export/<export_name>/* for this reason we search for
      # one specific file (saved_model.pb) according to the tf.learn directory
      # hierarchy. Where the * corresponds to the model timestamp.
      # TODO(user): Remove this gaurd after new Beam release
      try:
        from apache_beam.io import filesystems  # pylint: disable=g-import-not-at-top
        match_result = filesystems.FileSystems.match(
            [os.path.join(trained_model_dir, 'export', export_name,
                          '*', 'saved_model.pb')])[0]
        paths = [f.path for f in match_result.metadata_list]
      except ImportError:
        paths = fileio.ChannelFactory.glob(
            os.path.join(trained_model_dir, 'export', export_name,
                         '*', 'saved_model.pb'))
      # We still validate that there in only one model under the given path.
      if len(paths) == 1:
        return paths[0].replace('saved_model.pb', '')
      else:
        raise ValueError('The model on %s was not exported by tf.learn. '
                         'Or there is more than one matching model path: '
                         '%s'%
                         (trained_model_dir, paths))
    return extract_model_fn

  @staticmethod
  def _copy_model_dir(trained_model, dest, extract_model_fn):
    """Copy a folder.

    Args:
      trained_model: Folder containing a model.
      dest: Folder to copy trained_model to.
      extract_model_fn: A function to extract the model path from a file
        hierarchy like the one generated from tf.learn's
        `Estimator.export_savedmodel()`.

    Returns:
      dest
    Raises:
      ValueError: If the model directory doesn't match the tf.learn structure.
    """
    if extract_model_fn:
      trained_model = extract_model_fn(trained_model)
    else:
      trained_model = trained_model

    def append_trailing_slash(path):
      return path if path.endswith('/') else path + '/'

    # TODO(user): Remove this gaurd after new Beam release
    try:
      from apache_beam.io import filesystems  # pylint: disable=g-import-not-at-top
      filesystems.FileSystems.copy([append_trailing_slash(trained_model)],
                                   [append_trailing_slash(dest)])
    except ImportError:
      fileio.ChannelFactory.copytree(
          append_trailing_slash(trained_model), append_trailing_slash(dest))
    return dest

  def expand(self, model_directory):
    if self._extract_model_fn:
      return (model_directory
              | beam.Map(SaveModel._copy_model_dir, self._path,
                         self._extract_model_fn))
    else:
      return (model_directory
              | beam.Map(SaveModel._copy_model_dir, self._path,
                         self._extract_model_fn)
              | beam.io.textio.WriteToText(
                  self._path + '.meta',
                  shard_name_template='',
                  coder=Base64PickleCoder()))


class LoadModel(beam.PTransform):
  """Loads a model as written by SaveModel."""

  def __init__(self, path):
    """Initialize LoadModel.

    Args:
      path: The local or GCS path to read the model from.

    """
    super(LoadModel, self).__init__('LoadModel')
    self._path = path

  def expand(self, pvalue):
    # TODO(user): This still seems to be broken.
    # if fileio.ChannelFactory.exists(self._path + '.meta'):
    #  return pvalue.pipeline | beam.io.ReadFromText(
    #          self._path + '.meta', coder=Base64PickleCoder())
    # else:
    return pvalue.pipeline | beam.Create([self._path])


class SaveConfusionMatrixCsv(beam.PTransform):
  """A PTransform for saving confusion matrices.
  """

  def __init__(self, path):
    """Initialize SaveConfusionMatrixCsv.

    Args:
      path: The local or GCS path to save the confusion matrix to.

    """
    super(SaveConfusionMatrixCsv, self).__init__('Save Confusion Matrix')
    self._path = path

  def expand(self, confusion_matrix):
    # The confusion matrix is an output of a global aggregation and should
    # therefore be on a single shard.
    (confusion_matrix  # pylint: disable=expression-not-assigned
     | 'Write Confusion Matrix'
     >> beam.io.textio.WriteToText(
         self._path,
         shard_name_template='',
         coder=mlcoders.CsvCoder(['target', 'predicted', 'count'], ['count'])))


class SavePrecisionRecallCsv(beam.PTransform):
  """A PTransform for saving precision recall curves.
  """

  def __init__(self, path):
    """Initialize SavePrecisionRecallCsv.

    Args:
      path: The local or GCS path to save the precision recall curves to.
    """
    super(SavePrecisionRecallCsv, self).__init__('Save Precision Recall')
    self._path = path

  def expand(self, precision_recall):
    # Precision/recall is an output of a global aggregation and should
    # therefore be on a single shard.
    (precision_recall  # pylint: disable=expression-not-assigned
     | 'Write Precision Recall'
     >> beam.io.textio.WriteToText(
         self._path,
         shard_name_template='',
         coder=mlcoders.CsvCoder(
             ['label', 'threshold', 'precision', 'recall', 'f1score'],
             ['threshold', 'precision', 'recall', 'f1score'])))


class SaveTrainingJobResult(beam.PTransform):
  """A PTransform for saving a training job result."""

  def __init__(self, path):
    """Initialize SaveTrainingJobResult.

    Args:
      path: The local or GCS path to save the training job result to.
    """
    super(SaveTrainingJobResult, self).__init__()
    self._path = path

  def expand(self, result):
    return (result
            | beam.io.textio.WriteToText(
                self._path,
                shard_name_template='',
                coder=mlcoders.TrainingJobResultCoder()))


class LoadTrainingJobResult(beam.PTransform):
  """Loads a model as written by SaveTrainingJobResult."""

  def __init__(self, path):
    """Initialize LoadTrainingJobResult.

    Args:
      path: The local or GCS path to load the training job result from.
    """
    super(LoadTrainingJobResult, self).__init__()
    self._path = path

  def expand(self, pvalue):
    return pvalue.pipeline | beam.io.ReadFromText(
        self._path, coder=mlcoders.TrainingJobResultCoder())
