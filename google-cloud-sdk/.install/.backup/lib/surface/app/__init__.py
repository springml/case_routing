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

"""The gcloud app group."""

import sys

from googlecloudsdk.calliope import base


DETAILED_HELP = {
    'brief': 'Manage your App Engine deployments.',
    'DESCRIPTION': """
        The gcloud app command group lets you deploy and manage your Google App
        Engine apps. These commands replace their equivalents in the appcfg
        tool.

        App Engine is a platform for building scalable web applications
        and mobile backends. App Engine provides you with built-in services and
        APIs such as NoSQL datastores, memcache, and a user authentication API,
        common to most applications.

        More information on App Engine can be found here:
        https://cloud.google.com/appengine and detailed documentation can be
        found here: https://cloud.google.com/appengine/docs/
        """,
    'EXAMPLES': """\
        To run your app locally in the development application server, run:

          $ dev_appserver.py DEPLOYABLES

        To create a new deployment of one or more services, run:

          $ {command} deploy DEPLOYABLES

        To list your existing deployments, run:

          $ {command} versions list

        To generate config files for your source directory:

          $ {command} gen-config
        """
}


@base.ReleaseTracks(base.ReleaseTrack.ALPHA,
                    base.ReleaseTrack.BETA,
                    base.ReleaseTrack.GA)
class AppengineGA(base.Group):
  pass

AppengineGA.detailed_help = DETAILED_HELP
