# Copyright 2013 Google Inc. All Rights Reserved.
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

"""Command to set properties."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as c_exc
from googlecloudsdk.command_lib.config import completers
from googlecloudsdk.command_lib.config import flags
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import remote_completion


class Set(base.Command):
  """Set a Cloud SDK property.

  By default, sets the property in your active configuration only. Use the
  `--installation` flag to set the property across all configurations. See
  `gcloud topic configurations` for more information.

  ## AVAILABLE PROPERTIES

  {properties}

  ## EXAMPLES

  To set the project property in the core section, run:

    $ {command} project myProject

  To set the zone property in the compute section, run:

    $ {command} compute/zone zone3
  """

  detailed_help = {'properties': properties.VALUES.GetHelpString()}

  @staticmethod
  def Args(parser):
    """Adds args for this command."""
    parser.add_argument(
        'property',
        metavar='SECTION/PROPERTY',
        completer=completers.PropertiesCompleter,
        help='The property to be set. Note that SECTION/ is optional while '
        'referring to properties in the core section.')
    parser.add_argument(
        'value',
        completer=Set.ValueCompleter,
        help='The value to be set.')

    flags.INSTALLATION_FLAG.AddToParser(parser)

  @staticmethod
  def ValueCompleter(prefix, parsed_args, **unused_kwargs):
    prop = properties.FromString(getattr(parsed_args, 'property'))
    if not prop:
      # No property was given, or it was invalid.
      return

    if prop.choices:
      return [c for c in prop.choices if c.startswith(prefix)]

    if not prop.resource:
      # No collection associated with the property.
      return
    cli_generator = Set.GetCLIGenerator()
    if not cli_generator:
      return

    completer = remote_completion.RemoteCompletion.GetCompleterForResource(
        prop.resource, cli_generator, command_line=prop.resource_command_path)
    return completer(prefix=prefix, parsed_args=parsed_args, **unused_kwargs)

  def Run(self, args):
    scope = (properties.Scope.INSTALLATION if args.installation
             else properties.Scope.USER)

    prop = properties.FromString(args.property)
    if not prop:
      raise c_exc.InvalidArgumentException(
          'property', 'Must be in the form: [SECTION/]PROPERTY')
    properties.PersistProperty(prop, args.value, scope=scope)

    scope_msg = ''
    if args.installation:
      scope_msg = 'installation '
    log.status.Print('Updated {0}property [{1}].'.format(scope_msg, prop))



