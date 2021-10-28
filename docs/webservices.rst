.. _webapplabel:

Web Service and Demonstration Applications
==========================================

Included in this package are a few web-based service and demonstration applications,
providing a view into the functionality provided by the included algorithms and utilities.


.. _run_application:

runApplication
--------------

This script can be used to run any conforming (derived from `SmqtkWebApp`) SMQTK web based application.
Web services should be runnable via the ``bin/runApplication.py`` script.

.. argparse::
   :ref: smqtk_iqr.utils.runApplication.cli_parser
   :prog: runApplication


Sample Web Applications
-----------------------

.. toctree::
   :maxdepth: 3

   webservices/iqrdemonstration
