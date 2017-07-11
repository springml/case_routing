# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Interfaces and other classes for providing custom code for prediction."""


class Model(object):
  """A Model performs predictions on a given list of instances.

  The input instances are the raw values sent by the user. It is the
  responsibility of a Model to translate these instances into
  actual predictions.

  Note that this class is service agnostic, e.g., no assumptions are made
  about JSON or base64 encoding -- those conversions are taken care of by
  their respective services (in this case, the online prediction web server).
  The inputs and outputs here are Python data types. A particular Model
  handles a particular type of input.
  """

  def predict(self, instances, stats=None):
    """Returns predictions for the provided instances.

    Instances are the decoded values from the request. Clients need not worry
    about decoding json nor base64 decoding.

    Args:
      instances: list of instances, as described in the API.
      stats: Stats object for recording timing information.

    Returns:
      A two-element tuple (inputs, outputs). Both inputs and outputs are
      lists. Each input/output is a dict mapping input/output alias to the
      value for that input/output.

    Raises:
      PredictionError: if an error occurs during prediction.
    """
    raise NotImplementedError()

  @property
  def signature(self):
    """Returns the SignatureDef for this model."""
    raise NotImplementedError()


class PredictionClient(object):
  """A client for Prediction.

  No assumptions are made about whether the prediction happens in process,
  across processes, or even over the network.

  The inputs, unlike Model.predict, have already been "columnarized", i.e.,
  a dict mapping input names to values for a whole batch, much like
  Session.run's feed_dict parameter. The return value is the same format.
  """

  def predict(self, inputs, stats):
    """Produces predictions for the given inputs.

    Args:
      inputs: a dict mapping input names to values
      stats: Stats object for recording timing information.

    Returns:
      A dict mapping output names to output values, similar to the input
      dict.
    """
    raise NotImplementedError()

  @property
  def signature(self):
    """Returns the SignatureDef for the model this client uses."""
    raise NotImplementedError()


class Preprocessor(object):
  """Interface for processing instances one-by-one before prediction."""

  def preprocess(self, instance):
    """The preprocessing function.

    Args:
      instance: a single instance in the instances provided to the predict()
        method.

    Returns:
      The processed instance to use in the predict() method.
    """
    raise NotImplementedError()


class Postprocessor(object):
  """Interface for processing instances one-by-one after prediction."""

  def postprocess(self, instance):
    """The postprocessing function.

    Args:
      instance: a single instance in the instances outputted by the predict()
        method.

    Returns:
      The processed instance to return as the final prediction output.
    """
    raise NotImplementedError()


# Specify the method interface for users to implement, so disable the unused
# argument rule.
def from_client(client, model_path):  # pylint: disable=unused-argument
  """Creates a model using the given client and path.

  Path is useful, e.g., to load files from the exported directory containing
  the model.

  Args:
    client: An instance of Client for performing prediction.
    model_path: The path to the stored model.

  Returns:
    An instance implementing the following:
      Model
      -or-
      Preprocessor and/or Postprocessor
  """
  raise NotImplementedError()
