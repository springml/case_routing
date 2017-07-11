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
# ==============================================================================

"""Constants for export/import.

See: go/tf-exporter for these constants and directory structure.
"""

VERSION_FORMAT_SPECIFIER = "%08d"
ASSETS_DIRECTORY = "assets"
META_GRAPH_DEF_FILENAME = "export.meta"
VARIABLES_FILENAME = "export"
VARIABLES_FILENAME_V2 = "export.data"
VARIABLES_FILENAME_PATTERN = "export-?????-of-?????"
VARIABLES_FILENAME_PATTERN_V2 = "export.data-?????-of-?????"
VARIABLES_INDEX_FILENAME_V2 = "export.index"
INIT_OP_KEY = "serving_init_op"
SIGNATURES_KEY = "serving_signatures"
ASSETS_KEY = "serving_assets"
GRAPH_KEY = "serving_graph"
INPUTS_KEY = "inputs"
OUTPUTS_KEY = "outputs"
KEYS_KEY = "keys"


def keys_used_for_serving():
  """Return a list of all keys used for predictions."""
  return [
      INIT_OP_KEY,
      SIGNATURES_KEY,
      ASSETS_KEY,
      GRAPH_KEY,
      INPUTS_KEY,
      OUTPUTS_KEY,
      KEYS_KEY,
  ]
