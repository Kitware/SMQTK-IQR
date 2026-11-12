from datetime import datetime, timedelta
import unittest
from unittest import mock

import flask
from pymongo.collection import Collection

from smqtk_iqr.utils.mongo_sessions import MongoSession, MongoSessionInterface


class TestMongoSessionInterface(unittest.TestCase):

    def setUp(self) -> None:
        self.app = flask.Flask(__name__)
        self.app.config["SESSION_COOKIE_NAME"] = "custom_session"
        self.store = mock.Mock(spec=Collection)
        with mock.patch("smqtk_iqr.utils.mongo_sessions.MongoClient") as client:
            client.return_value.__getitem__.return_value.__getitem__.return_value = self.store
            self.interface = MongoSessionInterface(db="test")

    def test_save_session_with_pymongo_four(self) -> None:
        session = MongoSession({"user": "alice"}, sid="test-session")
        response = flask.Response()

        self.interface.save_session(self.app, session, response)

        self.store.replace_one.assert_called_once()
        query, document = self.store.replace_one.call_args.args
        self.assertEqual(query, {"_id": "test-session"})
        self.assertEqual(document["data"], {"user": "alice"})
        self.assertGreater(document["expiration"], datetime.utcnow())
        self.assertTrue(self.store.replace_one.call_args.kwargs["upsert"])
        cookie = response.headers["Set-Cookie"]
        self.assertIn("custom_session=test-session", cookie)
        self.assertIn("HttpOnly", cookie)

    def test_open_session_with_custom_cookie_name(self) -> None:
        self.store.find_one.return_value = {
            "_id": "test-session",
            "data": {"user": "alice"},
            "expiration": datetime.utcnow() + timedelta(hours=1),
        }
        with self.app.test_request_context(headers={"Cookie": "custom_session=test-session"}):
            session = self.interface.open_session(self.app, flask.request)

        self.assertEqual(session.sid, "test-session")
        self.assertEqual(session["user"], "alice")

    def test_delete_empty_session_with_flask_three(self) -> None:
        self.interface._delete_on_empty = True
        response = flask.Response()

        self.interface.save_session(self.app, MongoSession(sid="test-session"), response)

        self.store.replace_one.assert_not_called()
        cookie = response.headers["Set-Cookie"]
        self.assertIn("custom_session=;", cookie)
        self.assertIn("Max-Age=0", cookie)

    def test_expired_session_is_replaced(self) -> None:
        self.store.find_one.return_value = {
            "_id": "test-session",
            "data": {"user": "alice"},
            "expiration": datetime.utcnow() - timedelta(hours=1),
        }
        with self.app.test_request_context(headers={"Cookie": "custom_session=test-session"}):
            session = self.interface.open_session(self.app, flask.request)

        self.assertNotEqual(session.sid, "test-session")
        self.assertEqual(dict(session), {})
