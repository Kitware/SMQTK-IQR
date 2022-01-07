Pending Release Notes
=====================

Updates / New Features
----------------------

Auto-negative Selection

 * Add auto-negative selection in IqrSession for negative adjudications
   in case where none are provided

CI

 * Add a Github action to build the SMQTK-IQR web demo Docker image

Web

 * Transfer IQR web demo from mono-repo to this repo

 * Transfer web classifier service from mono-repo to this repo

Fixes
-----

CI

* Also run CI unittests for PRs targetting branches that match the `release*`
    glob.
