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
# pylint: disable=g-import-not-at-top
"""Classes and methods for predictions on a trained machine learning model.
"""
import os
from _interfaces import Model
from _interfaces import PredictionClient

_version = os.getenv("CLOUDML_ENDPOINT_VERSION")

if _version == "v1beta1":
  from _prediction_lib_beta import columnarize
  from _prediction_lib_beta import COLUMNARIZE_TIME
  from _prediction_lib_beta import create_model
  from _prediction_lib_beta import decode_base64
  from _prediction_lib_beta import DefaultModel
  from _prediction_lib_beta import encode_base64
  from _prediction_lib_beta import ENGINE
  from _prediction_lib_beta import INPUTS_KEY
  from _prediction_lib_beta import load_model
  from _prediction_lib_beta import local_predict
  from _prediction_lib_beta import OUTPUTS_KEY
  from _prediction_lib_beta import PredictionError
  from _prediction_lib_beta import rowify
  from _prediction_lib_beta import ROWIFY_TIME
  from _prediction_lib_beta import SESSION_RUN_ENGINE_NAME
  from _prediction_lib_beta import SESSION_RUN_TIME
  from _prediction_lib_beta import SessionClient
  from _prediction_lib_beta import Stats
  from _prediction_lib_beta import Timer
else:
  from prediction_lib import columnarize
  from prediction_lib import COLUMNARIZE_TIME
  from prediction_lib import create_model
  from prediction_lib import decode_base64
  from prediction_lib import DefaultModel
  from prediction_lib import encode_base64
  from prediction_lib import ENGINE
  from prediction_lib import INPUTS_KEY
  from prediction_lib import load_model
  from prediction_lib import local_predict
  from prediction_lib import OUTPUTS_KEY
  from prediction_lib import PredictionError
  from prediction_lib import rowify
  from prediction_lib import ROWIFY_TIME
  from prediction_lib import SESSION_RUN_ENGINE_NAME
  from prediction_lib import SESSION_RUN_TIME
  from prediction_lib import SessionClient
  from prediction_lib import Stats
  from prediction_lib import Timer
