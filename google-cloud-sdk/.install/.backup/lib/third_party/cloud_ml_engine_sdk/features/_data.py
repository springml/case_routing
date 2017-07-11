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
"""DataSet represention.
"""

# TODO(user): Support for BQ datasets


class DataSetUsage(object):
  """The usage mode associated with a particular dataset.
  """
  TRAINING = 'training'
  PREDICTION = 'prediction'
  EVALUATION = 'evaluation'


class DataSet(object):
  """Defines a dataset containing feature data to use.

  Defines a dataset containing feature data to use for training, prediction,
  or evaluation.
  """

  def __init__(self, filespec, usage):
    """Initialize an instance of a DataSet.

    Args:
      filespec: the set of files referenced by the path. This is used as a path
        prefix.
      usage: the usage mode for the data contained in the files.
    """
    self._filespec = filespec
    self._preprocessed_file_spec = None
    self._usage = usage

  @staticmethod
  def get_dataset_files(dataset):
    """Returns a list of files for the given list of datasets.

    Args:
      dataset: A DataSet object or list of DataSets.

    Returns:
      A list of the files in the passed dataset.
    """
    if isinstance(dataset, DataSet):
      return [dataset.filespec]
    else:
      return [d.filespec for d in dataset]

  @staticmethod
  def any_require_preprocessing(dataset):
    """Returns whether any of the passed datasets require preprocessing.

    Args:
      dataset: A DataSet object or list of DataSets.

    Returns:
      Whether any of the passed datasets require preprocessing.
    """
    if isinstance(dataset, DataSet):
      return dataset.requires_preprocessing
    else:
      return any(d.requires_preprocessing for d in dataset)

  @property
  def filespec(self):
    """Retrieves the file spec defining the dataset.

    Returns:
      The dataset's filespec.
    """
    return self._filespec

  @property
  def preprocessed_filespec(self):
    """Retrieves the file spec representing this dataset's preprocessing output.

    Returns:
      A the preprocessed file spec.
    """
    return self._preprocessed_file_spec

  @property
  def requires_preprocessing(self):
    """Indicates whether this dataset needs to be preprocessed.

    Returns:
      whether this dataset needs to be preprocessed.
    """
    return self._preprocessed_file_spec is not None

  @property
  def usage(self):
    """Retrieves the usage mode associated with the dataset.

    Returns:
      the usage mode associated with the dataset.
    """
    return self._usage

  def preprocess_to(self, filespec):
    """Flags this dataset as requiring preprocessing.

    Args:
      filespec: the set of output files to produce during preprocessing, used as
        a path prefix.

    Returns:
      self
    """
    self._preprocessed_file_spec = filespec
    return self

  @staticmethod
  def training(filespec):
    """Creates a training dataset.

    Args:
      filespec: the set of files referenced by the path, with an optional '*' to
        refer to a pattern.

    Returns:
      A DataSet with usable for Training.
    """
    return DataSet(filespec, DataSetUsage.TRAINING)

  @staticmethod
  def prediction(filespec):
    """Creates a prediction dataset.

    Args:
      filespec: the set of files referenced by the path, with an optional '*' to
        refer to a pattern.

    Returns:
      A DataSet with usable for Prediction.
    """
    return DataSet(filespec, DataSetUsage.PREDICTION)

  @staticmethod
  def evaluation(filespec):
    """Creates an evaluation dataset.

    Args:
      filespec: the set of files referenced by the path, with an optional '*' to
        refer to a pattern.

    Returns:
      A DataSet with usable for Evaluation.
    """
    return DataSet(filespec, DataSetUsage.EVALUATION)
