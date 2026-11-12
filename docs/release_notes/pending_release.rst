Pending Release Notes
=====================

Updates / New Features
----------------------

* Updated supported Python versions to 3.10 through 3.14.

* Updated CI to use ``actions/setup-python`` on Ubuntu 24.04 instead of job
  containers to avoid container registry pull limits.

* Updated NumPy requirements to match the other SMQTK packages and refreshed
  dependency requirements for supported Python versions and security fixes.

* Required SMQTK-Indexing 0.19.0 and SMQTK-Relevancy 0.18.0 for Python 3.14
  support and NumPy 2 compatibility.

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

* Refreshed locked dependencies for security fixes and the published
  SMQTK-Indexing and SMQTK-Relevancy releases.

* Corrected reStructuredText formatting in the release instructions and
  IqrSession documentation.

* Replaced Codecov uploads with a GitHub Actions coverage job that combines
  coverage across Python versions and saves reports and a job summary.

* Added tests for MongoDB session persistence, cookie handling, and expiration.

* Required Tornado 6.6 or newer on Python 3.11 and newer to address security
  advisories in the documentation and notebook dependencies.

* Raised the minimum PyMongo version to 4.18.3 to address a security advisory.

* Adapted existing session persistence, cookie access, and file downloads to
  the PyMongo 4 and Flask 3 APIs.

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

Known Issues
------------

* Python 3.10 retains Pillow 12.3.0 and Tornado 6.5.10 because their patched
  releases require Python 3.11. Newer Pillow and Tornado security advisories
  remain unresolved on Python 3.10; Python 3.11 and newer require Pillow 13
  and Tornado 6.6 with these fixes.
