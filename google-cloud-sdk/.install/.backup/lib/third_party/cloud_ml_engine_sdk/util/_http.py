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
"""Implements HTTP client helper functionality."""
import json
import urllib

import httplib2

from google.cloud.ml.util import _exceptions
from google.cloud.ml.util import _retry

# TODO(user): Start using the requests library instead.


class _Http(object):
  """A helper class for making HTTP requests.
  """

  def __init__(self):
    pass

  # The default retry policy will rety up to 10 times with the following delays
  # (ignoring fuzz):
  # [1, 2, 4, 8, 16, 30, 30, 30, 30, 30]
  # So the default retry policy retries for ~3 minutes before giving up.
  @staticmethod
  @_retry.with_exponential_backoff(initial_delay_secs=1.0, num_retries=10)
  def request(url,
              args=None,
              data=None,
              headers=None,
              method=None,
              credentials=None,
              raw_response=False):
    """Issues HTTP requests.

    Args:
      url: the URL to request.
      args: optional query string arguments.
      data: optional data to be sent within the request.
      headers: optional headers to include in the request.
      method: optional HTTP method to use. If unspecified this is inferred
          (GET or POST) based on the existence of request data.
      credentials: optional set of credentials to authorize the request.
      raw_response: whether the raw response content should be returned as-is.
    Returns:
      The parsed response object.
    Raises:
      Exception when the HTTP request fails or the response cannot be processed.
    """
    if headers is None:
      headers = {}

    headers['user-agent'] = 'GoogleCloudMLSDK/1.0'
    # Add querystring to the URL if there are any arguments.
    if args is not None:
      qs = urllib.urlencode(args)
      url = url + '?' + qs

    # Setup method to POST if unspecified, and appropriate request headers
    # if there is data to be sent within the request.
    if data is not None:
      if method is None:
        method = 'POST'

      # data could still be ''.
      if data:
        # If there is a content type specified, use it (and the data) as-is.
        # Otherwise, assume JSON, and serialize the data object.
        if 'Content-Type' not in headers:
          data = json.dumps(data)
          headers['Content-Type'] = 'application/json'
      headers['Content-Length'] = str(len(data))
    else:
      if method == 'POST':
        headers['Content-Length'] = '0'

    # If the method is still unset, i.e. it was unspecified, and there
    # was no data to be POSTed, then default to GET request.
    if method is None:
      method = 'GET'

    # Create an Http object to issue requests. Associate the credentials
    # with it if specified to perform authorization.
    #
    http = httplib2.Http()
    if credentials is not None:
      http = credentials.authorize(http)

    try:
      response, content = http.request(
          url, method=method, body=data, headers=headers)
      if 200 <= response.status < 300:
        if raw_response:
          return content
        return json.loads(content)
      else:
        raise _exceptions._RequestException(response.status, content)  # pylint: disable=protected-access
    except ValueError:
      raise Exception('Failed to process HTTP response.')
    except httplib2.HttpLib2Error:
      raise Exception('Failed to send HTTP request.')
