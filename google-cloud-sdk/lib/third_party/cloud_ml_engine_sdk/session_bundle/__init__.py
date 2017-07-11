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
"""Internal methods used for session bundling.
"""
# Google Cloud Machine Learning SDK

# pylint: disable=wildcard-import
from _constants import *

# TODO(user): Change the call sites for load_session_bundle_from_path to access
# from session_bundle instead of session_bundle._session_bundle
from _session_bundle import load_session_bundle_from_path
