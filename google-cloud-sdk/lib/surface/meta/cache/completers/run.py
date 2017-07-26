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

"""The meta cache completers run command."""

import sys

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import parser_extensions
from googlecloudsdk.command_lib.meta import cache_util
from googlecloudsdk.command_lib.util import parameter_info_lib
from googlecloudsdk.core import log
from googlecloudsdk.core import module_util
from googlecloudsdk.core.console import console_io


class _FunctionCompleter(object):
  """Convert an argparse function completer to a resource_cache completer."""

  def __init__(self, completer):
    self._completer = completer
    self.parameters = None

  def ParameterInfo(self, parsed_args, argument):
    del argument
    return parsed_args

  def Complete(self, prefix, parameter_info):
    return self._completer(prefix, parsed_args=parameter_info)


def _GetCompleter(module_path, cache=None, qualify=None, **kwargs):
  """Returns an instantiated completer for module_path."""
  completer = module_util.ImportModule(module_path)
  if not isinstance(completer, type):
    return _FunctionCompleter(completer)
  try:
    return completer(
        cache=cache,
        qualified_parameter_names=qualify,
        **kwargs)
  except TypeError:
    return _FunctionCompleter(completer())


class AddCompleterResourceFlags(parser_extensions.DynamicPositionalAction):
  """Adds resource argument flags based on the completer."""

  def __init__(self, *args, **kwargs):
    super(AddCompleterResourceFlags, self).__init__(*args, **kwargs)
    self.__argument = None
    self.__completer = None

  def GenerateArgs(self, namespace, module_path):
    kwargs = namespace.kwargs or {}
    self.__completer = _GetCompleter(
        module_path, qualify=namespace.qualify, **kwargs)
    args = {}
    if self.__completer.parameters:
      for parameter in self.__completer.parameters:
        dest = parameter_info_lib.GetDestFromParam(parameter.name)
        if hasattr(namespace, dest):
          # Don't add if its already been added.
          continue
        flag = parameter_info_lib.GetFlagFromDest(dest)
        args[parameter.name] = base.Argument(
            flag,
            dest=dest,
            category='RESOURCE COMPLETER',
            help='{} `{}` parameter value.'.format(
                self.__completer.__class__.__name__, parameter.name))
    self.__argument = base.Argument(
        'resource_to_complete',
        nargs='?',
        help=('The partial resource name to complete. Omit to enter an '
              'interactive loop that reads a partial resource name from the '
              'input and lists the possible prefix matches on the output '
              'or displays an ERROR message.'))
    args[self.__argument.name] = self.__argument
    return args

  def Completions(self, prefix, parsed_args, **kwargs):
    parameter_info = self.__completer.ParameterInfo(
        parsed_args, self.__argument)
    return self.__completer.Complete(prefix, parameter_info)


class Run(base.Command):
  """Cloud SDK completer module tester.

  *{command}* is an ideal way to debug completer modules without interference
  from the shell.  Shells typically ignore completer errors by disabling all
  standard output, standard error and exception messaging.  Specify
  `--verbosity=INFO` to enable completion and resource cache tracing.
  """

  @staticmethod
  def Args(parser):
    cache_util.AddCacheFlag(parser)
    parser.add_argument(
        '--qualify',
        metavar='NAME',
        type=arg_parsers.ArgList(),
        help=('A list of resource parameter names that must always be '
              'qualified. This is a manual setting for testing. The CLI sets '
              'this automatically.'))
    parser.add_argument(
        '--kwargs',
        metavar='NAME=VALUE',
        type=arg_parsers.ArgDict(),
        help=('Keyword arg dict passed to the completer constructor. For '
              'example, use this to set the resource collection and '
              'list command for `DeprecatedListCommandCompleter`:\n\n'
              '  --kwargs=collection=...,list_command_path="..."'))
    parser.add_argument(
        '--stack-trace',
        action='store_true',
        default=True,
        help=('Enable all exception stack traces, including Cloud SDK core '
              'exceptions.'))
    parser.AddDynamicPositional(
        'module_path',
        action=AddCompleterResourceFlags,
        help=('The completer module path. Run $ gcloud meta completers list` '
              'to list the avilable completers. A completer module may declare '
              'additional flags. Specify `--help` after _MODULE_PATH_ '
              'for details on the module specific flags.'))

  def Run(self, args):
    """Returns the results for one completion."""
    with cache_util.GetCache(args.cache, create=True) as cache:
      log.info('cache name {}'.format(cache.name))
      if not args.kwargs:
        args.kwargs = {}
      completer = _GetCompleter(
          args.module_path, cache=cache, qualify=args.qualify, **args.kwargs)
      parameter_info = completer.ParameterInfo(
          args, args.GetPositionalArgument('resource_to_complete'))
      if args.resource_to_complete is not None:
        matches = completer.Complete(args.resource_to_complete, parameter_info)
        return [matches]
      while True:
        name = console_io.PromptResponse('COMPLETE> ')
        if name is None:
          break
        try:
          completions = completer.Complete(name, parameter_info)
        except (Exception, SystemExit) as e:  # pylint: disable=broad-except
          if args.stack_trace:
            raise Exception(e), None, sys.exc_info()[2]
          else:
            log.error(unicode(e))
          continue
        if completions:
          print '\n'.join(completions)
      sys.stderr.write('\n')
      return None
