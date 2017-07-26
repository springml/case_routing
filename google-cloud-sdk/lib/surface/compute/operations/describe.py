# Copyright 2014 Google Inc. All Rights Reserved.
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
"""Command for describing operations."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute import flags as compute_flags
from googlecloudsdk.command_lib.compute import scope as compute_scope
from googlecloudsdk.command_lib.compute.operations import flags
from googlecloudsdk.core import resources


def AddFlags(parser, is_ga):
  """Helper function for adding flags dependant on the release track."""
  flags.COMPUTE_OPERATION_ARG.AddArgument(parser, operation_type='describe')

  if not is_ga:
    parser.add_argument(
        '--user-accounts',
        action='store_true',
        help=('If provided, it is assumed that the requested operation is '
              'a Compute User Accounts operation. Mutually exclusive with '
              '--global, --region, and --zone flags.'))


@base.ReleaseTracks(base.ReleaseTrack.GA)
class DescribeGA(base.DescribeCommand):
  """Describe a Google Compute Engine operation."""

  def __init__(self, *args, **kwargs):
    super(DescribeGA, self).__init__(*args, **kwargs)
    self._ga = True

  @staticmethod
  def Args(parser):
    AddFlags(parser, True)

  @property
  def service(self):
    return self._service

  def _ValidateArgs(self, args):
    if getattr(args, 'user_accounts', None) is None:
      return
    for arg in ['global', 'region', 'zone']:
      if getattr(args, arg, None):
        raise exceptions.ConflictingArgumentsException(
            '--user-accounts', '--' + arg)

  def _ResolveAsAccountOperation(self, args, clouduseraccounts_holder):
    self._service = clouduseraccounts_holder.client.globalAccountsOperations
    return flags.ACCOUNT_OPERATION_ARG.ResolveAsResource(
        args, clouduseraccounts_holder.resources,
        default_scope=compute_scope.ScopeEnum.GLOBAL)

  def _RaiseWrongResourceCollectionException(self, got, path):
    expected_collections = [
        'compute.instances',
        'compute.globalOperations',
        'compute.regionOperations',
        'compute.zoneOperations',
        'clouduseraccounts.globalAccountsOperations',
    ]
    raise resources.WrongResourceCollectionException(
        expected=','.join(expected_collections),
        got=got,
        path=path)

  def CreateReference(self, args, compute_holder, clouduseraccounts_holder):
    self._ValidateArgs(args)

    if not self._ga and args.user_accounts:
      return self._ResolveAsAccountOperation(args, clouduseraccounts_holder)

    try:
      ref = flags.COMPUTE_OPERATION_ARG.ResolveAsResource(
          args,
          compute_holder.resources,
          default_scope=compute_scope.ScopeEnum.GLOBAL,
          scope_lister=compute_flags.GetDefaultScopeLister(
              compute_holder.client))
    except resources.WrongResourceCollectionException:
      try:
        return self._ResolveAsAccountOperation(args, clouduseraccounts_holder)
      except resources.WrongResourceCollectionException as ex:
        self._RaiseWrongResourceCollectionException(ex.got, ex.path)

    if ref.Collection() == 'compute.globalOperations':
      self._service = compute_holder.client.apitools_client.globalOperations
    elif ref.Collection() == 'compute.regionOperations':
      self._service = compute_holder.client.apitools_client.regionOperations
    else:
      self._service = compute_holder.client.apitools_client.zoneOperations
    return ref

  def ScopeRequest(self, ref, request):
    if ref.Collection() == 'compute.regionOperations':
      request.region = ref.region
    elif ref.Collection() == 'compute.zoneOperations':
      request.zone = ref.zone

  def Run(self, args):
    compute_holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    clouduseraccounts_holder = base_classes.ComputeUserAccountsApiHolder(
        self.ReleaseTrack())

    operation_ref = self.CreateReference(args, compute_holder,
                                         clouduseraccounts_holder)

    request_type = self.service.GetRequestType('Get')
    request = request_type(**operation_ref.AsDict())

    return compute_holder.client.MakeRequests([(self.service, 'Get',
                                                request)])[0]


@base.ReleaseTracks(base.ReleaseTrack.ALPHA, base.ReleaseTrack.BETA)
class DescribeBeta(DescribeGA):
  """Describe a Google Compute Engine operation."""

  def __init__(self, *args, **kwargs):
    super(DescribeBeta, self).__init__(*args, **kwargs)
    self._ga = False

  @staticmethod
  def Args(parser):
    AddFlags(parser, False)


def DetailedHelp(version):
  """Construct help text based on the command release track."""
  detailed_help = {
      'brief': 'Describe a Google Compute Engine operation',
      'DESCRIPTION': """\
        *{command}* displays all data associated with a Google Compute
        Engine operation in a project.
        """,
      'EXAMPLES': """\
        To get details about a global operation, run:

          $ {command} OPERATION --global

        To get details about a regional operation, run:

          $ {command} OPERATION --region us-central1

        To get details about a zonal operation, run:

          $ {command} OPERATION --zone us-central1-a
        """,
  }
  if version == 'BETA':
    detailed_help['EXAMPLES'] = """\
        To get details about a global operation, run:

          $ {command} OPERATION --global

        To get details about a regional operation, run:

          $ {command} OPERATION --region us-central1

        To get details about a zonal operation, run:

          $ {command} OPERATION --zone us-central1-a

        To get details about a Compute User Accounts operation, run:

          $ {command} OPERATION --user-accounts
        """
  return detailed_help

DescribeGA.detailed_help = DetailedHelp('GA')
DescribeBeta.detailed_help = DetailedHelp('BETA')
