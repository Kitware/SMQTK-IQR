Pending Release Notes
=====================

Updates / New Features
----------------------

Tutorial to Perform IQR on Prepopulated Descriptor Set

* Added directory `docs/tutorialsfile` that has code to perform IQR on a
  prepopulated descriptor set. Documentation found in `demo_notes.sh`.

* Updated `pyproject.toml` to accept more recent versions of pillow package.

* Updated `smqtk_iqr/utils/mongo_sessions.py` for flask version 2.0.1 by
  extracting `cookie_session_name` from config file.

* Modified `mqtk_iqr/web/search_app/modules/iqr/static/js/smqtk.iqr_refine_view.js`
  to enable "Toggle Random Results" and "Refine" buttons at beginning of session.

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
