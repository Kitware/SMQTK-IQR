import os
import unittest
import unittest.mock as mock

from smqtk_iqr.web.search_app.modules.iqr.iqr_search import IqrSearch
from smqtk_iqr.web.search_app import IqrSearchDispatcher
from smqtk_dataprovider.impls.data_set.memory import DataMemorySet

from smqtk_core import Pluggable


class TestIqrSearch (unittest.TestCase):
    """
    Unit tests pertaining to the IqrSearch class.
    """

    # Patch in this module for stub implementation access.
    # noinspection PyUnresolvedReferences
    @mock.patch.dict(os.environ, {
        Pluggable.PLUGIN_ENV_VAR: __name__
    })
    def setUp(self) -> None:
        """
        Make an instance of the IqrSearchDispatcher application
        """
        # Setup configuration for test application
        config = IqrSearchDispatcher.get_default_config()
        self.dispatcher_app = IqrSearchDispatcher(config)

        # Setup dataset
        self.dataset = DataMemorySet()

    def test_iqr_search(self) -> None:
        """
        Test creation of an IqrSearch instance
        """
        app = IqrSearch(self.dispatcher_app, "test", self.dataset, ".")

        assert app.mod_upload is not None
        assert app.mod_static_dir is not None
