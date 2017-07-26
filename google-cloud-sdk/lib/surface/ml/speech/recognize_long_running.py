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
"""Command to analyze long audio."""

from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.ml.speech import speech_command_util


class RecognizeLongRunning(base.Command):
  """Get transcripts of longer audio from an audio file.

  Get a transcript of audio up to 80 minutes in length. If the audio is
  under 60 seconds, you may also use `{parent_command} recognize` to
  analyze it.

  To block the command from completing until analysis is finished, run:

    $ {command} AUDIO_FILE --language LANGUAGE --sample-rate SAMPLE_RATE

  You can also receive an operation as the result of the command by running:

    $ {command} AUDIO_FILE --language LANGUAGE --sample-rate SAMPLE_RATE --async

  This will return information about an operation. To get information about the
  operation, run:

    $ {parent_command} operations describe OPERATION_ID

  To poll the operation until it's complete, run:

    $ {parent_command} operations wait OPERATION_ID

  {auth_hints}
  """

  detailed_help = {'auth_hints': speech_command_util.SPEECH_AUTH_HELP}

  @staticmethod
  def Args(parser):
    # Format in json because ML API users are expected to prefer json.
    parser.display_info.AddFormat('json')
    speech_command_util.AddRecognizeFlags(parser, require_sample_rate=True)
    base.ASYNC_FLAG.AddToParser(parser)

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
        args.audio, args.language, long_running=True,
        sample_rate=args.sample_rate, hints=args.hints,
        max_alternatives=args.max_alternatives,
        filter_profanity=args.filter_profanity, encoding=args.encoding,
        async=args.async)
