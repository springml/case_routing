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
"""Command for creating images."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import csek_utils
from googlecloudsdk.api_lib.compute import image_utils
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute import flags as compute_flags
from googlecloudsdk.command_lib.compute.images import flags
from googlecloudsdk.command_lib.util import labels_util


def _Args(parser, release_track):
  """Set Args based on Release Track."""
  # GA Args
  parser.display_info.AddFormat(flags.LIST_FORMAT)

  sources_group = parser.add_mutually_exclusive_group(required=True)
  flags.AddCommonArgs(parser)
  flags.AddCommonSourcesArgs(parser, sources_group)

  Create.DISK_IMAGE_ARG = flags.MakeDiskImageArg()
  Create.DISK_IMAGE_ARG.AddArgument(parser, operation_type='create')
  csek_utils.AddCsekKeyArgs(parser, resource_type='image')

  labels_util.AddCreateLabelsFlags(parser)

  # Alpha and Beta Args
  if release_track in (base.ReleaseTrack.BETA, base.ReleaseTrack.ALPHA):
    flags.AddCloningImagesArgs(parser, sources_group)
    flags.MakeForceCreateArg().AddToParser(parser)


@base.ReleaseTracks(base.ReleaseTrack.GA)
class Create(base.CreateCommand):
  """Create Google Compute Engine images."""

  _ALLOW_RSA_ENCRYPTED_CSEK_KEYS = False

  _GUEST_OS_FEATURES = image_utils.GUEST_OS_FEATURES

  @classmethod
  def Args(cls, parser):
    _Args(parser, cls.ReleaseTrack())
    flags.AddGuestOsFeaturesArg(parser, cls._GUEST_OS_FEATURES)

  def Run(self, args):
    """Returns a list of requests necessary for adding images."""
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    client = holder.client
    messages = client.messages
    resource_parser = holder.resources

    image_ref = Create.DISK_IMAGE_ARG.ResolveAsResource(args, holder.resources)
    image = messages.Image(
        name=image_ref.image,
        description=args.description,
        sourceType=messages.Image.SourceTypeValueValuesEnum.RAW,
        family=args.family)

    csek_keys = csek_utils.CsekKeyStore.FromArgs(
        args, self._ALLOW_RSA_ENCRYPTED_CSEK_KEYS)
    if csek_keys:
      image.imageEncryptionKey = csek_utils.MaybeToMessage(
          csek_keys.LookupKey(image_ref,
                              raise_if_missing=args.require_csek_key_create),
          client.apitools_client)

    # Validate parameters.
    if args.source_disk_zone and not args.source_disk:
      raise exceptions.ToolException(
          'You cannot specify [--source-disk-zone] unless you are specifying '
          '[--source-disk].')

    source_image_project = getattr(args, 'source_image_project', None)
    source_image = getattr(args, 'source_image', None)
    source_image_family = getattr(args, 'source_image_family', None)

    if source_image_project and not (source_image or source_image_family):
      raise exceptions.ToolException(
          'You cannot specify [--source-image-project] unless you are '
          'specifying [--source-image] or [--source-image-family].')

    if source_image or source_image_family:
      image_expander = image_utils.ImageExpander(client, resource_parser)
      _, source_image_ref = image_expander.ExpandImageFlag(
          user_project=image_ref.project,
          image=source_image,
          image_family=source_image_family,
          image_project=source_image_project,
          return_image_resource=True)
      image.sourceImage = source_image_ref.selfLink
      image.sourceImageEncryptionKey = csek_utils.MaybeLookupKeyMessage(
          csek_keys, source_image_ref, client.apitools_client)

    # TODO(b/30086260): use resources.REGISTRY.Parse() for GCS URIs.
    if args.source_uri:
      source_uri = utils.NormalizeGoogleStorageUri(args.source_uri)
      image.rawDisk = messages.Image.RawDiskValue(source=source_uri)
    elif args.source_disk:
      source_disk_ref = flags.SOURCE_DISK_ARG.ResolveAsResource(
          args, holder.resources,
          scope_lister=compute_flags.GetDefaultScopeLister(client))
      image.sourceDisk = source_disk_ref.SelfLink()
      image.sourceDiskEncryptionKey = csek_utils.MaybeLookupKeyMessage(
          csek_keys, source_disk_ref, client.apitools_client)

    if args.licenses:
      image.licenses = args.licenses

    guest_os_features = getattr(args, 'guest_os_features', [])
    if guest_os_features:
      guest_os_feature_messages = []
      for feature in guest_os_features:
        gf_type = messages.GuestOsFeature.TypeValueValuesEnum(feature)
        guest_os_feature = messages.GuestOsFeature()
        guest_os_feature.type = gf_type
        guest_os_feature_messages.append(guest_os_feature)
      image.guestOsFeatures = guest_os_feature_messages

    request = messages.ComputeImagesInsertRequest(
        image=image,
        project=image_ref.project)

    args_labels = getattr(args, 'labels', None)
    if args_labels:
      labels = messages.Image.LabelsValue(additionalProperties=[
          messages.Image.LabelsValue.AdditionalProperty(
              key=key, value=value)
          for key, value in sorted(args_labels.iteritems())])
      request.image.labels = labels

    alpha_or_beta = self.ReleaseTrack() in (
        base.ReleaseTrack.BETA, base.ReleaseTrack.ALPHA)
    if alpha_or_beta and args.force_create:
      request.forceCreate = True

    return client.MakeRequests([(client.apitools_client.images, 'Insert',
                                 request)])


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class CreateBeta(Create):

  # Used in CreateRequests. We only want to allow RSA key wrapping in
  # alpha/beta, *not* GA.
  _ALLOW_RSA_ENCRYPTED_CSEK_KEYS = True

  _GUEST_OS_FEATURES = image_utils.GUEST_OS_FEATURES_BETA


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class CreateAlpha(CreateBeta):

  _GUEST_OS_FEATURES = image_utils.GUEST_OS_FEATURES_ALPHA


Create.detailed_help = {
    'brief': 'Create Google Compute Engine images',
    'DESCRIPTION': """\
        *{command}* is used to create custom disk images.
        The resulting image can be provided during instance or disk creation
        so that the instance attached to the resulting disks has access
        to a known set of software or files from the image.

        Images can be created from gzipped compressed tarball containing raw
        disk data or from existing disks in any zone.

        Images are global resources, so they can be used across zones and
        projects.

        To learn more about creating image tarballs, visit
        [](https://cloud.google.com/compute/docs/creating-custom-image)
        """,
}

CreateBeta.detailed_help = Create.detailed_help
CreateAlpha.detailed_help = Create.detailed_help
