# Copyright 2016 Google Inc. All Rights Reserved. Licensed under the Apache
# License, Version 2.0 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

"""Define a Wide + Deep model for classification on structured data."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import multiprocessing

import tensorflow as tf
from tensorflow.contrib import layers
from tensorflow.contrib.learn.python.learn.utils import input_fn_utils

tf.logging.set_verbosity(tf.logging.INFO)

# Define the format of your input data including unused columns
CSV_COLUMNS =  ['content_length',
 'content_word_count',
 'group1',
 'group2',
 'group3',
 'group4',
 'group5',
 'group6',
 'is_am',
 'is_weekday',
 'subject_length',
 'subject_word_count',
 'nlp_consumer_goods',
 'nlp_events',
 'nlp_locations',
 'nlp_organizations',
 'nlp_persons',
 'nlp_work_of_arts',
 'sentiment_scores',
 'group_outcome']

CSV_COLUMN_DEFAULTS = [[0.0],[0.0],[0.0],[0.0],[0.0],[0.0],[0.0],[0.0],[" "], [" "], [0.0],[0.0],[0.0],[0.0],[0.0],[0.0],[0.0],[0.0],[0.0],[0]]
 
LABEL_COLUMN = 'group_outcome'
LABELS = [0, 1, 2, 3, 4, 5]

CATEGORICAL_COLUMNS = ["is_am", "is_weekday"]
CONTINUOUS_COLUMNS = ['content_length',
 'content_word_count',
 'group1',
 'group2',
 'group3',
 'group4',
 'group5',
 'group6',
 'subject_length',
 'subject_word_count',
 'nlp_consumer_goods',
 'nlp_events',
 'nlp_locations',
 'nlp_organizations',
 'nlp_persons',
 'nlp_work_of_arts',
 'sentiment_scores']


# Define the initial ingestion of each feature used by your model.
INPUT_COLUMNS = [
  # Continous columns
  tf.contrib.layers.real_valued_column("content_length"),
  tf.contrib.layers.real_valued_column("content_word_count"),
  tf.contrib.layers.real_valued_column("subject_length"),
  tf.contrib.layers.real_valued_column("subject_word_count"),
  tf.contrib.layers.real_valued_column("nlp_consumer_goods"),
  tf.contrib.layers.real_valued_column("nlp_events"),
  tf.contrib.layers.real_valued_column("nlp_locations"),
  tf.contrib.layers.real_valued_column("nlp_organizations"),
  tf.contrib.layers.real_valued_column("nlp_persons"),
  tf.contrib.layers.real_valued_column("nlp_work_of_arts"),
  tf.contrib.layers.real_valued_column("sentiment_scores"),
  tf.contrib.layers.real_valued_column("group1"),
  tf.contrib.layers.real_valued_column("group2"),
  tf.contrib.layers.real_valued_column("group3"),
  tf.contrib.layers.real_valued_column("group4"),
  tf.contrib.layers.real_valued_column("group5"),
  tf.contrib.layers.real_valued_column("group6"),
  # Categorical  columns
  tf.contrib.layers.sparse_column_with_keys(column_name="is_am", keys=["Yes", "No"]),
  tf.contrib.layers.sparse_column_with_keys(column_name="is_weekday", keys=["Yes", "No"])
]
 
def build_estimator(model_dir, embedding_size=8, hidden_units=None):
  """Build a wide and deep model for predicting income category.
  Wide and deep models use deep neural nets to learn high level abstractions
  about complex features or interactions between such features.
  These models then combined the outputs from the DNN with a linear regression
  performed on simpler features. This provides a balance between power and
  speed that is effective on many structured data problems.
  You can read more about wide and deep models here:
  https://research.googleblog.com/2016/06/wide-deep-learning-better-together-with.html
  To define model we can use the prebuilt DNNCombinedLinearClassifier class,
  and need only define the data transformations particular to our dataset, and then
  assign these (potentially) transformed features to either the DNN, or linear
  regression portion of the model.
  Args:
    model_dir: str, the model directory used by the Classifier for checkpoints
      summaries and exports.
    embedding_size: int, the number of dimensions used to represent categorical
      features when providing them as inputs to the DNN.
    hidden_units: [int], the layer sizes of the DNN (input layer first)
  Returns:
    A DNNCombinedLinearClassifier
  """
  (content_length, content_word_count, subject_length, subject_word_count, 
    nlp_consumer_goods, nlp_events, nlp_locations, nlp_organizations, nlp_persons,
    nlp_work_of_arts, sentiment_scores, group1, group2, group3, group4,  group5,
    group6, is_am, is_weekday) = INPUT_COLUMNS
 
  # Engineered featuers
  content_length_bucket = tf.contrib.layers.bucketized_column(content_length, boundaries=[100, 200, 300, 400])
  subject_length_bucket = tf.contrib.layers.bucketized_column(subject_length, boundaries=[10, 15, 20, 25, 30])

  wide_columns = [
   is_am, is_weekday, content_length_bucket, subject_length_bucket
  ]

  deep_columns = [
    content_length, content_word_count, subject_length, subject_word_count, 
    nlp_consumer_goods, nlp_events, nlp_locations, nlp_organizations, nlp_persons,
    nlp_work_of_arts, sentiment_scores, group1, group2, group3, group4,  group5,
    group6
  ]
  return tf.contrib.learn.DNNLinearCombinedClassifier(
      model_dir=model_dir,
      linear_feature_columns=wide_columns,
      dnn_feature_columns=deep_columns,
      n_classes=6,
      dnn_hidden_units=hidden_units or [50, 50])


def parse_label_column(label_string_tensor):
  """Parses a string tensor into the label tensor
  Args:
    label_string_tensor: Tensor of dtype string. Result of parsing the
    CSV column specified by LABEL_COLUMN
  Returns:
    A Tensor of the same shape as label_string_tensor, should return
    an int64 Tensor representing the label index for classification tasks,
    and a float32 Tensor representing the value for a regression task.
  """
  # Build a Hash Table inside the graph
  table = tf.contrib.lookup.string_to_index_table_from_tensor(
      tf.constant(LABELS))

  # Use the hash table to convert string labels to ints
  return table.lookup(label_string_tensor)


def serving_input_fn():
  """Builds the input subgraph for prediction.
  This serving_input_fn accepts raw Tensors inputs which will be fed to the
  server as JSON dictionaries. The values in the JSON dictionary will be
  converted to Tensors of the appropriate type.
  Returns:
     tf.contrib.learn.input_fn_utils.InputFnOps, a named tuple
     (features, labels, inputs) where features is a dict of features to be
     passed to the Estimator, labels is always None for prediction, and
     inputs is a dictionary of inputs that the prediction server should expect
     from the user.
  """
  feature_placeholders = {
      column.name: tf.placeholder(column.dtype, [None])
      for column in INPUT_COLUMNS
  }
  features = {
      key: tf.expand_dims(tensor, -1)
      for key, tensor in feature_placeholders.items()
    }

  return input_fn_utils.InputFnOps(
    features,
    None,
    feature_placeholders
  )



def generate_input_fn(filenames,
                      num_epochs=None,
                      shuffle=False,
                      skip_header_lines=0,
                      batch_size=40):
  """Generates an input function for training or evaluation.
  Args:
      filenames: [str] list of CSV files to read data from.
      num_epochs: int how many times through to read the data.
        If None will loop through data indefinitely
      shuffle: bool, whether or not to randomize the order of data.
        Controls randomization of both file order and line order within
        files.
      skip_header_lines: int set to non-zero in order to skip header lines
        in CSV files.
      batch_size: int First dimension size of the Tensors returned by
        input_fn
  Returns:
      A function () -> (features, indices) where features is a dictionary of
        Tensors, and indices is a single Tensor of label indices.
  """
  def _input_fn():
    files = tf.concat([
      tf.train.match_filenames_once(filename)
      for filename in filenames
    ], axis=0)

    filename_queue = tf.train.string_input_producer(
        files, num_epochs=num_epochs, shuffle=shuffle)
    reader = tf.TextLineReader(skip_header_lines=skip_header_lines)

    _, rows = reader.read_up_to(filename_queue, num_records=batch_size)

    # DNNLinearCombinedClassifier expects rank 2 tensors.
    row_columns = tf.expand_dims(rows, -1)
    columns = tf.decode_csv(row_columns, record_defaults=CSV_COLUMN_DEFAULTS)
    features = dict(zip(CSV_COLUMNS, columns))

    # # Remove unused columns
    # for col in UNUSED_COLUMNS:
    #   features.pop(col)

    label = features[LABEL_COLUMN]  

    # remove label from features
    features.pop('group_outcome', 'group_outcome key not a feature')
 
    if shuffle:
      # This operation maintains a buffer of Tensors so that inputs are
      # well shuffled even between batches.
      features = tf.train.shuffle_batch(
          features,
          batch_size,
          capacity=batch_size * 10,
          min_after_dequeue=batch_size*2 + 1,
          num_threads=multiprocessing.cpu_count(),
          enqueue_many=True,
          allow_smaller_final_batch=True
      )
 
    return features, label
  return _input_fn
  
 
'''
# To train model locally (good idea before mounting in gcloud)
rm -r case-routing-model/output
gcloud ml-engine local train \
    --module-name case-routing-model.task \
    --package-path case-routing-model/ \
    -- \
    --train-file case-routing-model/data/caserouting_train.csv \
    --eval-file case-routing-model/data/caserouting_validation.csv \
    --train-steps 10000 \
    --eval-steps 100 \
    --job-dir case-routing-model/output \
    --verbosity INFO 
 
# view results in tensorboard
# python -m tensorflow.tensorboard --logdir=case-routing-model/output --port=8080
# http://localhost:8080/
 
 
https://console.cloud.google.com/storage/browser?project=mlpdm-168115

export PROJECT_ID=emailinsight-1
export JOB_NAME=train_${USER}_$(date +%Y%m%d_%H%M%S)
export BUCKET=gs://email_insights_perms
export TRAIN_PATH=${BUCKET}/jobs/${JOB_NAME}


gcloud ml-engine jobs submit training ${JOB_NAME} --job-dir ${TRAIN_PATH}/models/ --runtime-version 1.0 \
 --package-path=caseroutingmodel --module-name=caseroutingmodel.task \
 --staging-bucket=${BUCKET} --region=us-central1 -- --train-file ${BUCKET}/caseroutingmodel/data/caserouting_train.csv \
 --eval-file {BUCKET}/caseroutingmodel/data/caserouting_validation.csv --train-steps 10000

# do this through the GUI
models -> create
pdmdemo/jobs/train_manuel_amunategui_20170602_132023/models/export/Servo/1496437905348/


# gcloud components update
 
gcloud ml-engine predict --model case_routing_model_v1 --version v1 --json-instances data/test1.json



'''
