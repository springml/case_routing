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
"""Text tokenizer functionality.
"""

import re

from bs4 import BeautifulSoup as bs
import nltk
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer
from nltk.util import ngrams as ng


def create_flat_tokenizer(
    split_regex=r'\w{1,}',
    stop_words='english',
    use_stemmer=False,
    ngrams=1,
    strip_html=False,
    removable_tags=None):
  r"""Returns a function for splitting a string into a sequence of tokens.

  Significantly faster implementations are prefererred when full generality
  is not required (including, notably, for categorical columns).
  Args:
    split_regex: A regex to group characters by. Defaults to \w{1,}, any
      alphanumeric character.
    stop_words: Which ntlk stop_words to use. Defaults to english.
    use_stemmer: Whether to use a porter stemmer. Defaults to False.
    ngrams: The maximum length of ngrams to return. Defaults to 1.
    strip_html: Whether to strip html. Defaults to False.
    removable_tags: Which tags to remove. Defaults to None.

  Returns:
    A safe tokenizer lambda function, will return empty sequence if the input
    string is '' or None.
  """
  # There is no guarantee that the tokenizer functions are consistent on their
  # treatment of the empty string (since the behavior depends on the provided
  # regexp).
  if split_regex is None:
    # Returning a tuple is faster than returning a list.
    return lambda text: (text,) if text else tuple()
  elif (ngrams == 1 and not stop_words
        and not use_stemmer and not strip_html):
    if split_regex == r'\S+':
      tokenizer_fn = str.split
    else:
      tokenizer_fn = re.compile(split_regex).findall
  else:
    tokenize = _TextTokenizer(
        regex=split_regex,
        stop_words=stop_words,
        use_stemmer=use_stemmer,
        ngrams=ngrams,
        strip_html=strip_html,
        removable_tags=removable_tags).tokenize
    tokenizer_fn = (
        lambda text: [gram for glist in tokenize(text) for gram in glist])

  # We need to make sure on all cases that we have consistent handling of the
  # absent value, in which case we always return empty 'tuple()'.
  return lambda text: tokenizer_fn(text) if text else tuple()


# _TextTokenizer is private for now and should be allocated via the
# optimizations provided by create_flat_tokenizer, if there's any reason / use
# case to make it public in the future please make sure analysis and transform
# use the same parameters and optimizations.
class _TextTokenizer(object):
  """A tokenizer for plain text.
  """

  def __init__(self, regex, stop_words, use_stemmer, ngrams, strip_html,
               removable_tags):
    r"""Initializes an instance a PlainTextTokenizer.

    Args:
      regex: A regex to group characters.
      stop_words: the list of stop_words to use
      use_stemmer: True if the words should be stemmed.
      ngrams: The maximum length of ngrams.
      strip_html: Boolean on whether html_markup should be removed before
        processing
      removable_tags: list of html tags whose text should be ignored

    Raises:
      ValueError: if ngrams is < 1.
    """
    self._prog = re.compile(regex)
    self._stop_words = self.get_stop_words(stop_words)
    if use_stemmer:
      self._stemmer = PorterStemmer()
    else:
      self._stemmer = None

    if ngrams < 1:
      raise ValueError('ngrams should be >= 1.')
    self._ngrams = ngrams
    self._strip_html = strip_html
    if strip_html:
      self._html_parser = _HtmlParser(removable_tags)

  def tokenize(self, text):
    """Tokenizes plain text into a set of word tokens.

    Args:
      text: The text to tokenize, should not be None.

    Returns:
      A nested list of ngrams from the tokenizer's regex.
    """
    if self._strip_html:
      text = self._html_parser.remove_markup(text)
    text = text.lower()
    # TODO(user): Use NLTK's regexp_tokenizer here.
    word_list = self._prog.findall(text)
    word_list = [word for word in word_list if word not in self._stop_words]
    if self._stemmer is not None:
      word_list = [self._stemmer.stem(word) for word in word_list]

    results = list()
    results.append(word_list)
    for i in range(2, self._ngrams + 1):
      ngrams_list = list()
      n_grams = ng(word_list, i)
      for grams in n_grams:
        ngrams_list.append(' '.join(grams))
      results.append(ngrams_list)

    return results

  @staticmethod
  def get_stop_words(stop_words_input):
    """Gets a set of stop-words to filter the text on.

    Args:
      stop_words_input: This can either be the string input to
        nltk.stopwords.words(), or a set/list of stop-words to filter on.

    Returns:
      A set of stop-words to filter the text on.

    Raises:
      ValueError: Input is an unknown string
    """
    if stop_words_input is None:
      return set()
    if isinstance(stop_words_input, set) or isinstance(stop_words_input, list):
      return set(stop_words_input)  # convert to a set because its faster
    if isinstance(stop_words_input, str):
      try:
        return set(stopwords.words(stop_words_input))
      except LookupError as _:
        # Download the stopwords data.  We'd have done this during setup,
        # but the location is user and platform specific.
        nltk.download('stopwords')
        return set(stopwords.words(stop_words_input))

    raise ValueError('Don\'t know how to set stop_words with %s' %
                     stop_words_input)


# _HtmlParser is private for now and it is only instantiated from
# _TextTokenizer, if there's any reason / use case to make it public in
# the future please make sure analysis and transform use the same parameters
# and optimizations.
class _HtmlParser(object):

  def __init__(self, removable_tags=None):
    self._removable_tags = removable_tags

  def remove_markup(self, html):
    soup = bs(html, 'html.parser')
    if self._removable_tags:
      _ = [tag.extract() for tag in soup.find_all(self._removable_tags)]
    html_text = soup.get_text()
    # Convert unicode string to str and remove multiple newlines caused by html
    return str(re.sub('[\n]+', '\n', html_text.strip()))
