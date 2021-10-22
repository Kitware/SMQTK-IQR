IQR Classes
-----------

Here we list and briefly describe the high level algorithm interfaces which SMQTK-IQR provides.
Some implementations will require additional dependencies that cannot be packaged with SMQTK-IQR.


IqrController
+++++++++++++
This interface represents algorithms that classify ``IqrController`` instances into discrete labels or label confidences.

.. autoclass:: smqtk_iqr.iqr.iqr_controller.IqrController
   :members:
   :private-members:

IqrSession
++++++++++
This interface represents algorithms that classify ``IqrSession`` instances into discrete labels or label confidences.

.. autoclass:: smqtk_iqr.iqr.iqr_session.IqrSession
   :members:
   :private-members:
