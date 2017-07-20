# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Update cluster command."""

from apitools.base.py import exceptions as apitools_exceptions

from googlecloudsdk.api_lib.container import api_adapter
from googlecloudsdk.api_lib.container import kubeconfig as kconfig
from googlecloudsdk.api_lib.container import util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.container import flags
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io


class InvalidAddonValueError(util.Error):
  """A class for invalid --update-addons input."""

  def __init__(self, value):
    message = ('invalid --update-addons value {0}; '
               'must be ENABLED or DISABLED.'.format(value))
    super(InvalidAddonValueError, self).__init__(message)


class InvalidPasswordError(util.Error):
  """A class for invalid --set-password input."""

  def __init__(self, value, error):
    message = ('invalid --set-password value "{0}"; {1}'.format(value, error))
    super(InvalidPasswordError, self).__init__(message)


def _ValidatePassword(val):
  if len(val) < 16:
    raise InvalidPasswordError(val, 'Password must be at least length 16')
  return


def _ParseAddonDisabled(val):
  if val == 'ENABLED':
    return False
  if val == 'DISABLED':
    return True
  raise InvalidAddonValueError(val)


def _AddCommonArgs(parser):
  parser.add_argument(
      'name',
      metavar='NAME',
      help='The name of the cluster to update.')
  parser.add_argument(
      '--node-pool',
      help='Node pool to be updated.')
  flags.AddAsyncFlag(parser)


def _AddMutuallyExclusiveArgs(mutex_group):
  """Add all arguments that need to be mutually exclusive from each other."""
  mutex_group.add_argument(
      '--monitoring-service',
      help='The monitoring service to use for the cluster. Options '
      'are: "monitoring.googleapis.com" (the Google Cloud Monitoring '
      'service),  "none" (no metrics will be exported from the cluster)')
  mutex_group.add_argument(
      '--update-addons',
      type=arg_parsers.ArgDict(spec={
          api_adapter.INGRESS: _ParseAddonDisabled,
          api_adapter.HPA: _ParseAddonDisabled,
      }),
      dest='disable_addons',
      metavar='ADDON=ENABLED|DISABLED',
      help='''Cluster addons to enable or disable. Options are
{hpa}=ENABLED|DISABLED
{ingress}=ENABLED|DISABLED'''.format(
    hpa=api_adapter.HPA, ingress=api_adapter.INGRESS))
  mutex_group.add_argument(
      '--generate-password',
      action='store_true',
      default=None,
      help='Ask the server to generate a secure password and use that as the '
      'admin password.')
  mutex_group.add_argument(
      '--set-password',
      action='store_true',
      default=None,
      help='Set the admin password to the user specified value.')


def _AddAdditionalZonesArg(mutex_group):
  mutex_group.add_argument(
      '--additional-zones',
      type=arg_parsers.ArgList(),
      metavar='ZONE',
      help="""\
The set of additional zones in which the cluster's node footprint should be
replicated. All zones must be in the same region as the cluster's primary zone.

Note that the exact same footprint will be replicated in all zones, such that
if you created a cluster with 4 nodes in a single zone and then use this option
to spread across 2 more zones, 8 additional nodes will be created.

Multiple locations can be specified, separated by commas. For example:

  $ {command} example-cluster --zone us-central1-a --additional-zones us-central1-b,us-central1-c

To remove all zones other than the cluster's primary zone, pass the empty string
to the flag. For example:

  $ {command} example-cluster --zone us-central1-a --additional-zones ""
""")


@base.ReleaseTracks(base.ReleaseTrack.GA)
class Update(base.UpdateCommand):
  """Update cluster settings for an existing container cluster."""

  @staticmethod
  def Args(parser):
    """Register flags for this command.

    Args:
      parser: An argparse.ArgumentParser-like object. It is mocked out in order
          to capture some information, but behaves like an ArgumentParser.
    """
    _AddCommonArgs(parser)
    group = parser.add_mutually_exclusive_group(required=True)
    _AddMutuallyExclusiveArgs(group)
    flags.AddClusterAutoscalingFlags(parser, group, hidden=True)
    flags.AddMasterAuthorizedNetworksFlags(parser, group, hidden=True)
    flags.AddEnableLegacyAuthorizationFlag(group, hidden=True)
    flags.AddStartIpRotationFlag(group, hidden=True)
    flags.AddCompleteIpRotationFlag(group, hidden=True)
    flags.AddUpdateLabelsFlag(group, suppressed=True)
    flags.AddRemoveLabelsFlag(group, suppressed=True)
    flags.AddNetworkPolicyFlags(group, hidden=True)

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      Some value that we want to have printed later.
    """
    adapter = self.context['api_adapter']

    cluster_ref = adapter.ParseCluster(args.name,
                                       getattr(args, 'region', None))
    # Make sure it exists (will raise appropriate error if not)
    cluster = adapter.GetCluster(cluster_ref)

    # locations will be None if additional-zones was specified, an empty list
    # if it was specified with no argument, or a populated list if zones were
    # provided. We want to distinguish between the case where it isn't
    # specified (and thus shouldn't be passed on to the API) and the case where
    # it's specified as wanting no additional zones, in which case we must pass
    # the cluster's primary zone to the API.
    # TODO(b/29578401): Remove the hasattr once the flag is GA.
    locations = None
    if hasattr(args, 'additional_zones') and args.additional_zones is not None:
      locations = sorted([cluster_ref.zone] + args.additional_zones)

    if args.generate_password or args.set_password:
      if args.generate_password:
        password = ''
        options = api_adapter.SetMasterAuthOptions(
            action=api_adapter.SetMasterAuthOptions.GENERATE_PASSWORD,
            password=password)
      else:
        password = raw_input('Please enter the new password:')
        _ValidatePassword(password)
        options = api_adapter.SetMasterAuthOptions(
            action=api_adapter.SetMasterAuthOptions.SET_PASSWORD,
            password=password)

      try:
        op_ref = adapter.SetMasterAuth(cluster_ref, options)
        del password
        del options
      except apitools_exceptions.HttpError as error:
        del password
        del options
        raise exceptions.HttpException(error, util.HTTP_ERROR_FORMAT)
    elif args.enable_network_policy is not None:
      console_io.PromptContinue(
          message='Enabling/Disabling Network Policy causes a rolling '
          'update of all cluster nodes, similar to performing a cluster '
          'upgrade.  This operation is long-running and will block other '
          'operations on the cluster (including delete) until it has run '
          'to completion.',
          cancel_on_no=True)
      options = api_adapter.SetNetworkPolicyOptions(
          enabled=args.enable_network_policy)
      try:
        op_ref = adapter.SetNetworkPolicy(cluster_ref, options)
      except apitools_exceptions.HttpError as error:
        raise exceptions.HttpException(error, util.HTTP_ERROR_FORMAT)
    elif args.start_ip_rotation:
      console_io.PromptContinue(
          message='This will start an IP Rotation on cluster [{name}]. The '
          'master will be updated to serve on a new IP address in addition to '
          'the current IP address. Container Engine will then recreate all '
          'nodes ({num_nodes} nodes) to point to the new IP address. This '
          'operation is long-running and will block other operations on the '
          'cluster (including delete) until it has run to completion.'
          .format(name=cluster.name, num_nodes=cluster.currentNodeCount),
          cancel_on_no=True)
      try:
        op_ref = adapter.StartIpRotation(cluster_ref)
      except apitools_exceptions.HttpError as error:
        raise exceptions.HttpException(error, util.HTTP_ERROR_FORMAT)
    elif args.complete_ip_rotation:
      console_io.PromptContinue(
          message='This will complete the in-progress IP Rotation on cluster '
          '[{name}]. The master will be updated to stop serving on the old IP '
          'address and only serve on the new IP address. Make sure all API '
          'clients have been updated to communicate with the new IP address '
          '(e.g. by running `gcloud container clusters get-credentials '
          '--project {project} --zone {zone} {name}`). This operation is long-'
          'running and will block other operations on the cluster (including '
          'delete) until it has run to completion.'
          .format(name=cluster.name, project=cluster_ref.projectId,
                  zone=cluster.zone),
          cancel_on_no=True)
      try:
        op_ref = adapter.CompleteIpRotation(cluster_ref)
      except apitools_exceptions.HttpError as error:
        raise exceptions.HttpException(error, util.HTTP_ERROR_FORMAT)
    elif args.update_labels is not None:
      try:
        op_ref = adapter.UpdateLabels(cluster_ref, args.update_labels)
      except apitools_exceptions.HttpError as error:
        raise exceptions.HttpException(error, util.HTTP_ERROR_FORMAT)
    elif args.remove_labels is not None:
      try:
        op_ref = adapter.RemoveLabels(cluster_ref, args.remove_labels)
      except apitools_exceptions.HttpError as error:
        raise exceptions.HttpException(error, util.HTTP_ERROR_FORMAT)
    else:
      enable_master_authorized_networks = args.enable_master_authorized_networks

      if args.enable_legacy_authorization is not None:
        op_ref = adapter.SetLegacyAuthorization(
            cluster_ref,
            args.enable_legacy_authorization)
      else:
        options = api_adapter.UpdateClusterOptions(
            monitoring_service=args.monitoring_service,
            disable_addons=args.disable_addons,
            enable_autoscaling=args.enable_autoscaling,
            min_nodes=args.min_nodes,
            max_nodes=args.max_nodes,
            node_pool=args.node_pool,
            locations=locations,
            enable_master_authorized_networks=
            enable_master_authorized_networks,
            master_authorized_networks=args.master_authorized_networks)
        op_ref = adapter.UpdateCluster(cluster_ref, options)

    if not args.async:
      adapter.WaitForOperation(
          op_ref, 'Updating {0}'.format(cluster_ref.clusterId))

      log.UpdatedResource(cluster_ref)

      if args.start_ip_rotation or args.complete_ip_rotation:
        cluster = adapter.GetCluster(cluster_ref)
        try:
          util.ClusterConfig.Persist(cluster, cluster_ref.projectId)
        except kconfig.MissingEnvVarError as error:
          log.warning(error.message)


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class UpdateBeta(Update):
  """Update cluster settings for an existing container cluster."""

  @staticmethod
  def Args(parser):
    _AddCommonArgs(parser)
    group = parser.add_mutually_exclusive_group(required=True)
    _AddMutuallyExclusiveArgs(group)
    flags.AddClusterAutoscalingFlags(parser, group, hidden=True)
    _AddAdditionalZonesArg(group)
    flags.AddMasterAuthorizedNetworksFlags(parser, group, hidden=True)
    flags.AddEnableLegacyAuthorizationFlag(group)
    flags.AddStartIpRotationFlag(group)
    flags.AddCompleteIpRotationFlag(group)
    flags.AddUpdateLabelsFlag(group)
    flags.AddRemoveLabelsFlag(group)
    flags.AddNetworkPolicyFlags(group, hidden=True)


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class UpdateAlpha(Update):
  """Update cluster settings for an existing container cluster."""

  @staticmethod
  def Args(parser):
    _AddCommonArgs(parser)
    group = parser.add_mutually_exclusive_group(required=True)
    _AddMutuallyExclusiveArgs(group)
    flags.AddClusterAutoscalingFlags(parser, group)
    _AddAdditionalZonesArg(group)
    flags.AddMasterAuthorizedNetworksFlags(parser, group, hidden=True)
    flags.AddEnableLegacyAuthorizationFlag(group)
    flags.AddStartIpRotationFlag(group)
    flags.AddCompleteIpRotationFlag(group)
    flags.AddUpdateLabelsFlag(group)
    flags.AddRemoveLabelsFlag(group)
    flags.AddNetworkPolicyFlags(group, hidden=False)
