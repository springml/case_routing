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
"""Cloud ML SDK version constants.
"""
import os

# Google Cloud Machine Learning SDK Version info.
__version__ = '0.1.9.1-alpha'  # Don't bump up to 0.1.10 as gcloud will break.

# The pip version of TF that this version of the SDK is known to be
# compatible with.  This may not be the version the user has installed.
# Also note that tensorflow may not be pip installable by the user depending
# on their system, or they may have/want the GPU version.
tf_version = 'tensorflow==1.0.0'

required_install_packages = [
    'oauth2client == 2.2.0',
    'six >= 1.10.0, < 2.0',
    'apache-beam[gcp] >= 2.0.0',  # This should be pinned before release.
    'google-cloud-logging >= 0.23.0, < 1.0',
    'bs4 >= 0.0.1, < 1.0',
    'numpy >= 1.10.4',  # Don't pin numpy, as it requires a recompile.
    'pillow == 3.4.1',  # pillow 3.4.2 requires libjpeg and will break things.
    'crcmod >= 1.7, < 2.0',
    'nltk >= 3.2.1, < 4.0',
    'pyyaml >= 3.11, < 4.0',
    'google-gax == 0.15.1',
    'protobuf >= 3.1.0, < 4.0'
]

# The version of this SDK that can be used by Dataflow.
sdk_location = os.environ.get(
    'CLOUDSDK_ML_LOCATION_OVERRIDE',
    'gs://cloud-ml/sdk/cloudml-' + __version__ + '.dataflow.tar.gz')

# The Cloud Storage location of the installed sdk.
installed_sdk_location = 'gs://cloud-ml/sdk/cloudml-' + __version__ + '.tar.gz'

# The Cloud Storage location of a no dependencies version of the sdk.
nodeps_sdk_location = 'gs://cloud-ml/sdk/cloudml-' + __version__ + '.nodeps.tar.gz'

# The Cloud Storage location of the released samples.
samples_location = 'gs://cloud-ml/sdk/cloudml-samples-' + __version__ + '.tar.gz'

# The Cloud Storage location of the documentation.
docs_location = 'gs://cloud-ml/sdk/cloudml-docs-' + __version__ + '.tar.gz'
