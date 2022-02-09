Pending Release Notes
=====================

Updates / New Features
----------------------

Auto-negative Selection

 * Added auto-negative selection in IqrSession for negative adjudications
   in case where none are provided.

CI

 * Added a Github action to build the SMQTK-IQR web demo Docker image.

 * Added workflow to inherit the smqtk-core publish workflow.

Web

 * Transferred IQR web demo from mono-repo to this repo.

 * Transferred web classifier service from mono-repo to this repo.

Miscellaneous

 * Added a wrapper script to pull the versioning/changelog update helper from
   smqtk-core to use here without duplication.

Fixes
-----

CI

* Modified CI unittests workflow to run for PRs targetting branches that match
  the `release*` glob.

Dependency Versions

* Updated the developer dependency and locked version of ipython to address a
  security vulnerability.

* Removed `jedi = "^0.17"` requirement and update to `ipython = "^7.17.3"`
  since recent ipython update appropriately addresses the dependency.
