Pending Release Notes
=====================

Updates / New Features
----------------------

Auto-negative Selection

 * Add auto-negative selection in IqrSession for negative adjudications
   in case where none are provided

CI

 * Add a Github action to build the SMQTK-IQR web demo Docker image

 * Add workflow to inherit the smqtk-core publish workflow

Web

 * Transfer IQR web demo from mono-repo to this repo

 * Transfer web classifier service from mono-repo to this repo

Miscellaneous

 * Add a wrapper script to pull the versioning/changelog update helper from
   smqtk-core to use here without duplication.

Fixes
-----

CI

* Also run CI unittests for PRs targetting branches that match the `release*`
  glob.

Dependency Versions

* Update the developer dependency and locked version of ipython to address a
  security vulnerability.
