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

* Updated CI unittests workflow to install optional packages.
  Reduced CodeCov report submission by skipping this step on scheduled runs.

Web

* Transferred IQR web demo from mono-repo to this repo.

* Transferred web classifier service from mono-repo to this repo.

Miscellaneous

* Added a wrapper script to pull the versioning/changelog update helper from
  smqtk-core to use here without duplication.

* Updated minimum version to Python 3.7

Fixes
-----

CI

* Update CI to work with the state of software in 2024.

* Modified CI unittests workflow to run for PRs targetting branches that match
  the `release*` glob.

Dependency Versions

* Updated the developer dependency and locked version of ipython to address a
  security vulnerability.

* Removed `jedi = "^0.17"` requirement and update to `ipython = "^7.17.3"`
  since recent ipython update appropriately addresses the dependency.

* Updated readthedocs config

* Use sys.exit instead of exit

* Updated pillow requirement to allow for more recent versions.

* Handle versions of werkzeug > 2.0.0 up to at least 3.0.4

* Handle versions of flask > 2.0.1 up to at least 3.0.3

Changes
-------

* Changed READMEs from .md to .rst and improved formatting consistency

* The "Toggle Random Results" and "Refine" buttons are now enabled by default
  to let the user test database images as queries.

* Added debugging information to server exception when ports are in use.

* Use xdoctest in testing instead of regular doctest
