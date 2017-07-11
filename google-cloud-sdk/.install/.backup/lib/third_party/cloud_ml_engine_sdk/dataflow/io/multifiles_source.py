# Copyright 2017 Google Inc. All Rights Reserved.
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Mutiple files/file patterns source.

Multiple File source, which reads the union of multiple files and/or file
patterns.
"""

from apache_beam import coders
from apache_beam.io import iobase
from apache_beam.io.filesystem import CompressionTypes
from apache_beam.io.iobase import Read
from apache_beam.io.range_trackers import OffsetRangeTracker
from apache_beam.io.textio import _TextSource as TextSource
from apache_beam.io.tfrecordio import _TFRecordSource as TFRecordSource
from apache_beam.transforms import PTransform
from apache_beam.transforms.display import DisplayDataItem

# pylint: disable=g-import-not-at-top
try:
  from apache_beam.options.value_provider import ValueProvider
  from apache_beam.options.value_provider import StaticValueProvider
except ImportError:
  from apache_beam.utils.value_provider import ValueProvider
  from apache_beam.utils.value_provider import StaticValueProvider
# pylint: enable=g-import-not-at-top

FILE_LIST_SEPARATOR = ','


class MultiFilesSource(iobase.BoundedSource):
  """Base class for multiple files source.

  Support to read multiple files or file patterns separated by a comma. Subclass
  should implement create_source() to actually create sources to use.
  """

  def __init__(self, file_patterns, **kwargs):
    # Handle the templated values.
    if not isinstance(file_patterns, (basestring, ValueProvider)):
      raise TypeError('%s: file_pattern must be of type string'
                      ' or ValueProvider; got %r instead'
                      % (self.__class__.__name__, file_patterns))

    if isinstance(file_patterns, basestring):
      file_patterns = StaticValueProvider(str, file_patterns)
    self._file_patterns = file_patterns
    self._sources = []
    self._kwargs = kwargs

  def _populate_sources_lazily(self):
    # We need to do it lazily because self._file_patterns can be a templated
    # value and must be evaluated at runtime.
    if not self._sources:
      # dedup repeated files or file patterns.
      for file_pattern in list(set(self._file_patterns.get().split(
          FILE_LIST_SEPARATOR))):
        self._sources.append(self.create_source(file_pattern.strip(),
                                                **self._kwargs))

  def estimate_size(self):
    self._populate_sources_lazily()
    return sum(s.estimate_size() for s in self._sources)

  def get_range_tracker(self, start_position, stop_position):
    self._populate_sources_lazily()
    if start_position is None:
      start_position = 0
    if stop_position is None:
      stop_position = len(self._sources)

    return OffsetRangeTracker(start_position, stop_position)

  def create_source(self, file_pattern, **kwargs):
    raise NotImplementedError('MultiFilesSource cannot be used directly.')

  def read(self, range_tracker):
    self._populate_sources_lazily()
    start_source = range_tracker.start_position()
    stop_source = range_tracker.stop_position()

    for source_ix in range(start_source, stop_source):
      if not range_tracker.try_claim(source_ix):
        break
      sub_range_tracker = self._sources[source_ix].get_range_tracker(None, None)
      for record in self._sources[source_ix].read(sub_range_tracker):
        yield record

  def split(self, desired_bundle_size, start_position=None,
            stop_position=None):
    self._populate_sources_lazily()
    if start_position or stop_position:
      raise ValueError(
          'Multi-files initial splitting is not supported. Expected start and '
          'stop positions to be None. Received %r and %r respectively.' %
          (start_position, stop_position))

    for source in self._sources:
      for bundle in source.split(desired_bundle_size):
        yield bundle

  def display_data(self):
    return {'file_patterns': DisplayDataItem(str(self._file_patterns),
                                             label='File Patterns')}


class _MultiTextSource(MultiFilesSource):
  """Multiple files source for Text source."""
  # TODO(user): Currently liquid sharding is performed on source boundaries.
  # For text files, a more complicated RangeTracker can be implemented to
  # support liquid sharding within sub-sources if needed. See ConcatRangeTracker
  # in concat_source.py for reference.

  def create_source(self, file_pattern, min_bundle_size=0,
                    compression_type=CompressionTypes.AUTO,
                    strip_trailing_newlines=True,
                    coder=coders.StrUtf8Coder(),
                    validate=True,
                    skip_header_lines=0):
    return TextSource(file_pattern=file_pattern,
                      min_bundle_size=min_bundle_size,
                      compression_type=compression_type,
                      strip_trailing_newlines=strip_trailing_newlines,
                      coder=coders.StrUtf8Coder(),
                      validate=validate,
                      skip_header_lines=skip_header_lines)


# TODO(user): currently compression_type is not a ValueProvider valure in
# filebased_source, thereby we have to make seperate classes for
# non-compressed and compressed version of TFRecord sources. Consider to
# make the compression_type a ValueProvider in filebased_source.
class _MultiTFRecordSource(MultiFilesSource):
  """Multiple files source for TFRecord source."""

  def create_source(self, file_pattern):
    return TFRecordSource(
        file_pattern=file_pattern,
        coder=coders.BytesCoder(),
        compression_type=CompressionTypes.AUTO,
        validate=True)


class _MultiTFRecordGZipSource(MultiFilesSource):
  """Multiple files source for TFRecord source gzipped."""

  def create_source(self, file_pattern):
    return TFRecordSource(
        file_pattern=file_pattern,
        coder=coders.BytesCoder(),
        compression_type=CompressionTypes.GZIP,
        validate=True)


class ReadFromMultiFilesText(PTransform):
  """A PTransform for reading text files or files patterns.

  It is a wrapper of ReadFromText but supports multiple files or
  files patterns.
  """

  def __init__(
      self,
      file_patterns,
      min_bundle_size=0,
      compression_type=CompressionTypes.AUTO,
      strip_trailing_newlines=True,
      coder=coders.StrUtf8Coder(),
      validate=True,
      skip_header_lines=0,
      **kwargs):
    """Initialize the ReadFromText transform.

    Args:
      file_patterns: The file paths/patterns to read from as local file paths
      or GCS files. Paths/patterns seperated by commas.
      min_bundle_size: Minimum size of bundles that should be generated when
        splitting this source into bundles. See ``FileBasedSource`` for more
        details.
      compression_type: Used to handle compressed input files. Typical value
        is CompressionTypes.AUTO, in which case the underlying file_path's
        extension will be used to detect the compression.
      strip_trailing_newlines: Indicates whether this source should remove
        the newline char in each line it reads before decoding that line.
      coder: Coder used to decode each line.
      validate: flag to verify that the files exist during the pipeline
        creation time.
      skip_header_lines: Number of header lines to skip. Same number is skipped
        from each source file. Must be 0 or higher. Large number of skipped
        lines might impact performance.
       **kwargs: optional args dictionary.
    """

    super(ReadFromMultiFilesText, self).__init__(**kwargs)
    self._source = _MultiTextSource(
        file_patterns,
        min_bundle_size=min_bundle_size,
        compression_type=compression_type,
        strip_trailing_newlines=strip_trailing_newlines,
        coder=coder,
        validate=validate,
        skip_header_lines=skip_header_lines)

  def expand(self, pvalue):
    return pvalue.pipeline | Read(self._source)


class ReadFromMultiFilesTFRecord(PTransform):
  """Transform for reading multiple TFRecord sources.

  It is a wrapper of ReadFromTFRecord but supports multiple files or
  files patterns.
  """

  def __init__(self,
               file_patterns,
               **kwargs):
    """Initialize a ReadFromMultiFilesTFRecord transform.

    Args:
      file_patterns: file glob patterns to read TFRecords from.
       **kwargs: optional args dictionary.

    Returns:
      A ReadFromTFRecord transform object.
    """
    super(ReadFromMultiFilesTFRecord, self).__init__(**kwargs)
    self._source = _MultiTFRecordSource(file_patterns)

  def expand(self, pvalue):
    return pvalue.pipeline | Read(self._source)


class ReadFromMultiFilesTFRecordGZip(PTransform):
  """Transform for reading multiple TFRecord Gzipped sources.

  It is a wrapper of ReadFromTFRecord gzipped but supports multiple files or
  files patterns.
  """

  def __init__(self,
               file_patterns,
               **kwargs):
    """Initialize a ReadFromMultiFilesTFRecordGzip transform.

    Args:
      file_patterns: file glob patterns to read TFRecords from.
       **kwargs: optional args dictionary.

    Returns:
      A ReadFromTFRecord transform object.
    """
    super(ReadFromMultiFilesTFRecordGZip, self).__init__(**kwargs)
    self._source = _MultiTFRecordGZipSource(file_patterns)

  def expand(self, pvalue):
    return pvalue.pipeline | Read(self._source)
