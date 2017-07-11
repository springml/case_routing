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

"""Importer for an exported TensorFlow model.

This module provides a function to create a SessionBundle containing both the
Session and MetaGraph.
"""
import logging
import os
import shutil
import tempfile


from google.cloud.ml.session_bundle import _constants
from google.cloud.ml.util import _file
# Import tf.contrib, otherwise Tensorflow won't load those operations,
# and imported graphs may need them.
import tensorflow.contrib  # pylint: disable=unused-import
from tensorflow.core.protobuf import meta_graph_pb2


def load_session_bundle_from_path(export_dir, target="", config=None):
  """Load session bundle from the given path.

  The function reads input from the export_dir, constructs the graph data to the
  default graph and restores the parameters for the session created.

  Args:
    export_dir: the directory that contains files exported by exporter.
    target: The execution engine to connect to. See target in tf.Session()
    config: A ConfigProto proto with configuration options. See config in
    tf.Session()

  Returns:
    session: a tensorflow session created from the variable files.
    meta_graph: a meta graph proto saved in the exporter directory.

  Raises:
    RuntimeError: if the required files are missing or contain unrecognizable
    fields, i.e. the exported model is invalid.
  """
  # TF brings in a numpy dependency, so load it lazily.
  import tensorflow as tf  # pylint: disable=g-import-not-at-top
  if hasattr(tf, "GIT_VERSION"):
    logging.info("tf.GIT_VERSION=%s", tf.GIT_VERSION)
  else:
    logging.info("tf.GIT_VERSION=unknown")

  meta_graph_filename = os.path.join(export_dir,
                                     _constants.META_GRAPH_DEF_FILENAME)
  if not _file.file_exists(meta_graph_filename):
    raise RuntimeError("Expected meta graph file missing %s" %
                       meta_graph_filename)

  variables_filename = ""
  variables_filename_list = []
  additional_files_to_copy = []
  checkpoint_sharded = False

  variables_index_filename = os.path.join(
      export_dir, _constants.VARIABLES_INDEX_FILENAME_V2)
  checkpoint_v2 = _file.file_exists(variables_index_filename)

  if checkpoint_v2:
    # The checkpoint is in v2 format.
    variables_filename = os.path.join(export_dir,
                                      _constants.VARIABLES_FILENAME_V2)
    # Check to see if the file "export" exists or not.
    if _file.file_exists(variables_filename):
      variables_filename_list = [variables_filename]
    else:
      # Check to see if the sharded file named "export-?????-of-?????" exists.
      variables_filename_pattern = os.path.join(
          export_dir, _constants.VARIABLES_FILENAME_PATTERN_V2)
      variables_filename_list = _file.glob_files(variables_filename_pattern)
      checkpoint_sharded = True
    # If the checkpoint is not local, we need to copy export.index locally too.
    additional_files_to_copy = [variables_index_filename]
  else:
    variables_filename = os.path.join(export_dir,
                                      _constants.VARIABLES_FILENAME)
    if _file.file_exists(variables_filename):
      variables_filename_list = [variables_filename]
    else:
      variables_filename = os.path.join(export_dir,
                                        _constants.VARIABLES_FILENAME_PATTERN)
      variables_filename_list = _file.glob_files(variables_filename)
      checkpoint_sharded = True

  if not variables_filename_list or not variables_filename:
    raise RuntimeError("No or bad checkpoint files found in %s" % export_dir)

  # Prepare the files to restore a session.
  restore_files = ""
  if checkpoint_v2 or not checkpoint_sharded:
    # For checkpoint v2 or v1 with non-sharded files, use "export" to restore
    # the session.
    restore_files = _constants.VARIABLES_FILENAME
  else:
    restore_files = _constants.VARIABLES_FILENAME_PATTERN

  # Reads meta graph file.
  meta_graph_def = meta_graph_pb2.MetaGraphDef()
  with _file.open_local_or_gcs(meta_graph_filename, "r") as f:
    logging.info("Reading metagraph from %s", meta_graph_filename)
    meta_graph_def.ParseFromString(f.read())

  collection_def = meta_graph_def.collection_def
  graph_def = tf.GraphDef()
  if _constants.GRAPH_KEY in collection_def:
    logging.info("Using value of collection %s for the graph.",
                 _constants.GRAPH_KEY)
    # Use serving graph_def in MetaGraphDef collection_def if exists
    graph_def_any = collection_def[_constants.GRAPH_KEY].any_list.value
    if len(graph_def_any) != 1:
      raise RuntimeError(
          "Expected exactly one serving GraphDef in : %s" % meta_graph_def)
    else:
      graph_def_any[0].Unpack(graph_def)
      # Replace the graph def in meta graph proto.
      meta_graph_def.graph_def.CopyFrom(graph_def)

      # TODO(user): If we don't clear the collections then import_meta_graph
      # fails. See
      # https://yaqs.googleplex.com/eng/q/5577391960752128
      #
      # We can't delete all the collections because some of them are used
      # by prediction to get the names of the input/output tensors.
      keys_to_delete = (set(meta_graph_def.collection_def.keys()) -
                        set(_constants.keys_used_for_serving()))
      for k in keys_to_delete:
        del meta_graph_def.collection_def[k]
  else:
    logging.info("No %s found in metagraph. Using metagraph as serving graph",
                 _constants.GRAPH_KEY)

  tf.reset_default_graph()
  sess = tf.Session(target, graph=None, config=config)
  # Import the graph.
  saver = tf.train.import_meta_graph(meta_graph_def)
  # Restore the session.
  if variables_filename_list[0].startswith("gs://"):
    # Make copy from GCS files.
    # TODO(user): Retire this once tensorflow can access GCS.
    try:
      temp_dir_path = tempfile.mkdtemp("local_variable_files")
      for f in variables_filename_list + additional_files_to_copy:
        _file.copy_file(f, os.path.join(temp_dir_path, os.path.basename(f)))

      saver.restore(sess, os.path.join(temp_dir_path, restore_files))
    finally:
      try:
        shutil.rmtree(temp_dir_path)
      except OSError as e:
        if e.message == "Cannot call rmtree on a symbolic link":
          # Interesting synthetic exception made up by shutil.rmtree.
          # Means we received a symlink from mkdtemp.
          # Also means must clean up the symlink instead.
          os.unlink(temp_dir_path)
        else:
          raise
  else:
    saver.restore(sess, os.path.join(export_dir, restore_files))

  init_op_tensor = None
  if _constants.INIT_OP_KEY in collection_def:
    init_ops = collection_def[_constants.INIT_OP_KEY].node_list.value
    if len(init_ops) != 1:
      raise RuntimeError(
          "Expected exactly one serving init op in : %s" % meta_graph_def)
    init_op_tensor = tf.get_collection(_constants.INIT_OP_KEY)[0]

  if init_op_tensor:
    # Run the init op.
    sess.run(fetches=[init_op_tensor])

  return sess, meta_graph_def
