===========
SMQTK - IQR
===========

Intent
------

This package provides the tools and web interface for using SMQTK's IQR
platform.

Tutorials
---------

* `IQR Playground <docker/smqtk_iqr_playground/README.rst>`_.


Contributing
------------

See the SMQTK-Core docs on `CONTRIBUTING <https://github.com/Kitware/SMQTK-Core/blob/master/CONTRIBUTING.md>`_.


Documentation
-------------

You can build the Sphinx documentation locally for the most up-tp-date
reference:

.. code:: bash

    # Install dependencies
    poetry install
    # Navigate to the documentation root.
    cd docs
    # Build the docs.
    poetry run make html
    # Open in your favorite browser!
    firefox _build/html/index.html
