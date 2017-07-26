# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Command to analyze sentiments."""

from googlecloudsdk.api_lib.ml.language import util
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.ml.language import flags
from googlecloudsdk.command_lib.ml.language import language_command_util


@base.ReleaseTracks(base.ReleaseTrack.GA)
class AnalyzeSentimentGa(base.Command):
  """Use Google Cloud Natural Language API to identify sentiments in a text.

  Sentiment Analysis inspects the given text and identifies the prevailing
  emotional opinion within the text, especially to determine a writer's
  attitude as positive, negative, or neutral.

  {service_account_help}

  {language_help}
  """

  detailed_help = {
      'service_account_help': language_command_util.SERVICE_ACCOUNT_HELP,
      'language_help': language_command_util.LANGUAGE_HELP
  }

  @staticmethod
  def Args(parser):
    parser.display_info.AddFormat('json')
    flags.AddLanguageFlags(parser)

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Raises:
      ContentFileError: if content file can't be found and is not a Google
          Cloud Storage URL.
      ContentError: if content is given but empty.
      googlecloudsdk.api_lib.util.exceptions.HttpException: if the API returns
          an error.

    Returns:
      the result of the analyze sentiment command.
    """
    return language_command_util.RunLanguageCommand(
        'analyzeSentiment',
        content_file=args.content_file,
        content=args.content,
        language=args.language,
        content_type=args.content_type,
        encoding_type=args.encoding_type,
        api_version=util.LANGUAGE_GA_VERSION)


@base.ReleaseTracks(base.ReleaseTrack.BETA, base.ReleaseTrack.ALPHA)
class AnalyzeSentimentBeta(AnalyzeSentimentGa):
  """Use Google Cloud Natural Language API to identify sentiments in a text.

  Sentiment Analysis inspects the given text and identifies the prevailing
  emotional opinion within the text, especially to determine a writer's
  attitude as positive, negative, or neutral.

  {service_account_help}

  {language_help}
  """

  detailed_help = {
      'service_account_help': language_command_util.SERVICE_ACCOUNT_HELP,
      'language_help': language_command_util.LANGUAGE_HELP_BETA
  }

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Raises:
      ContentFileError: if content file can't be found and is not a Google
          Cloud Storage URL.
      ContentError: if content is given but empty.
      googlecloudsdk.api_lib.util.exceptions.HttpException: if the API returns
          an error.

    Returns:
      the result of the analyze sentiment command.
    """
    return language_command_util.RunLanguageCommand(
        'analyzeSentiment',
        content_file=args.content_file,
        content=args.content,
        language=args.language,
        content_type=args.content_type,
        encoding_type=args.encoding_type,
        api_version=util.LANGUAGE_BETA_VERSION)
