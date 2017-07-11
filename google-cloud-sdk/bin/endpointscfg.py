#!/usr/bin/env python
#
# Copyright 2015 Google Inc. All Rights Reserved.
#

"""A convenience wrapper for endpointscfg.py for appengine for python."""

import os

import bootstrapping.bootstrapping as bootstrapping
from googlecloudsdk.core.updater import update_manager


def main():
  """Runs endpointscfg.py."""
  update_manager.UpdateManager.EnsureInstalledAndRestart(
      ['app-engine-python'],
      command=__file__)

  bootstrapping.ExecutePythonTool(
      os.path.join('platform', 'google_appengine'), 'endpointscfg.py')


if __name__ == '__main__':
  bootstrapping.CommandStart('endpointscfg', component_id='core')
  bootstrapping.CheckUpdates('endpointscfg')
  main()
