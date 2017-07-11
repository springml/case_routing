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
"""Command to analyze short audio."""

from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.ml.speech import speech_command_util


class Recognize(base.Command):
  """Get transcripts of short (less than 60 seconds) audio from an audio file.

  Get a transcript of an audio file that is less than 60 seconds. You can use
  an audio file that is on your local drive or a Google Cloud Storage URL.

  If the audio is longer than 60 seconds, you will get an error. Please use
  `{parent_command} recognize-long-running` instead.

  {auth_hints}
  """

  detailed_help = {'auth_hints': speech_command_util.SPEECH_AUTH_HELP}

  @staticmethod
  def Args(parser):
    # Format in json because ML API users are expected to prefer json.
    parser.display_info.AddFormat('json')
    speech_command_util.AddRecognizeFlags(parser)

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Raises:
      googlecloudsdk.api_lib.ml.speech.exceptions.AudioException, if audio
          is not found locally and does not appear to be Google Cloud Storage
          URL.
      googlecloudsdk.api_lib.util.exceptions.HttpException, if there is an
          error returned by the API.

    Returns:
      The results of the request.
    """
    return speech_command_util.RunRecognizeCommand(
        args.audio, args.language, long_running=False,
        sample_rate=args.sample_rate, hints=args.hints,
        max_alternatives=args.max_alternatives,
        filter_profanity=args.filter_profanity, encoding=args.encoding)
