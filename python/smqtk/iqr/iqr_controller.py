import atexit
import threading
import time
import uuid

from smqtk.utils import SmqtkObject


class IqrController (SmqtkObject):
    """
    Main controlling object for one or more IQR Sessions.

    In order to interface with a web server, methods defined here are
    thread-safe.

    This class may be used with the ``with`` statement. This will enable the
    instance's primary lock, preventing any other action from being performed
    on the instance while inside the with statement. The lock is reentrant, so
    nested with-statements will not dead-lock.

    """

    def __init__(self, expire_enabled=False, expire_check=30):
        """
        Initialize the controller.

        Session timeout, when enabled, is set on a session-by-session basis,
        i.e. different session may have different time out values if desired.
        When expiration is not enabled, session timeout values are ignored.

        :param expire_enabled: Enable/Disable session expiry. If enabled, a
            thread is started for monitoring and removal.
        :type expire_enabled:

        :param expire_check: Interval, in seconds, that we check for session
            expiration.
        :type expire_check: float
        """

        # Map of uuid to the search state
        #: :type: dict[collections.Hashable, IqrSession]
        self._iqr_sessions = {}
        # Map of sessions with timeout's enabled and the time out value in
        # seconds
        #: :type
        self._iqr_session_timeout = {}
        # Map of the UNIX time a session was last accessed
        self._iqr_session_last_access = {}

        # RLock for iqr_session[*] maps.
        self._map_rlock = threading.RLock()

        self._expire_enabled = expire_enabled
        self._expire_interval = expire_check
        self._expire_thread_stop_event = threading.Event()
        # prevents calling _handle_session_expiration when not enabled
        self._expire_thread_stop_event.set()
        self._expire_thread = None

        # If enabled, start expiration monitor thread
        if self._expire_enabled:
            self._log.debug("Starting session expiration monitor thread")
            self._expire_thread = threading.Thread(
                target=self._handle_session_expiration
            )
            self._expire_thread.daemon = True
            self._expire_thread_stop_event.clear()  # revert L:57
            self._expire_thread.start()
            atexit.register(self._stop_expiration_monitor)

    def __enter__(self):
        self._map_rlock.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._map_rlock.release()

    def _handle_session_expiration(self):
        """
        Run on a separate thread periodic checks and removals of sessions that
        have expired.
        """
        while not self._expire_thread_stop_event.wait(self._expire_interval):
            # scan timeout-set sessions, removing those that have timed out
            now = time.time()
            with self._map_rlock:
                self._log.debug("Checking session expiration timeouts")
                for sid in self._iqr_session_timeout.keys():
                    to = self._iqr_session_timeout[sid]
                    la = self._iqr_session_last_access[sid]
                    t = now - la
                    if t > to:
                        self._log.debug("-> Expiring session '%s' "
                                        "(last-access: %s, timeout: %s, "
                                        "now: %s)", sid, la, to, now)
                        self.remove_session(sid)

        self._log.debug("End of expiration handle function")

    def _stop_expiration_monitor(self):
        if self._expire_thread:
            self._log.debug("Stopping session expiration monitor thread")
            self._expire_thread_stop_event.set()
            self._expire_thread.join()
            self._log.debug("Stopping session expiration monitor thread -- Done")

    def session_uuids(self):
        """
        Return a tuple of all currently registered IqrSessions.

        This does NOT update session last access in regards to session
        expiration.

        :return: a tuple of all currently registered IqrSessions.
        :rtype: tuple of collections.Hashable

        """
        with self._map_rlock:
            return tuple(self._iqr_sessions)

    def has_session_uuid(self, session_uuid):
        """ Check if this controller contains a session referenced by the given
        ID.

        Performance using this function is faster compared to getting all UUIDs
        and performing a linear search (because hash tables).

        This does NOT update session last access in regards to session
        expiration.

        :param session_uuid: Possible UUID of a session
        :type session_uuid: collections.Hashable

        :return: True of the given UUID references a session in this controller
            and false if not.
        :rtype: bool

        """
        with self._map_rlock:
            return session_uuid in self._iqr_sessions

    def add_session(self, iqr_session, timeout=0):
        """ Initialize a new IQR Session, returning the uuid of that session

        This controller indexes the given session by its UUID.

        :param iqr_session: The IqrSession instance to add
        :type iqr_session: smqtk.iqr.iqr_session.IqrSession

        :param timeout: The optional timeout, in seconds.
        :type timeout: float

        :return: UUID of new IQR Session
        :rtype: collections.Hashable

        """
        timeout = float(timeout)
        with self._map_rlock:
            sid = iqr_session.uuid
            if sid in self._iqr_sessions:
                raise RuntimeError("Cannot use given session as its UUID "
                                   "already exists in the controller session "
                                   "map: %s" % sid)

            self._iqr_sessions[sid] = iqr_session
            if timeout > 0:
                self._iqr_session_timeout[sid] = timeout
                self._iqr_session_last_access[sid] = time.time()
            return sid

    def get_session(self, session_uuid):
        """
        Return the session instance for the given UUID

        :raises KeyError: The given UUID doesn't exist in this controller.

        :param session_uuid: UUID if the session to get
        :type session_uuid: collections.Hashable

        :return: IqrSession instance for the given UUID
        :rtype: smqtk.iqr.iqr_session.IqrSession

        """
        with self._map_rlock:
            if session_uuid in self._iqr_session_timeout:
                self._iqr_session_last_access = time.time()
            return self._iqr_sessions[session_uuid]

    def remove_session(self, session_uuid):
        """
        Remove an IQR Session by session UUID.

        :raises KeyError: The given UUID doesn't exist in this controller.

        :param session_uuid: Session UUID
        :type session_uuid: collections.Hashable

        """
        with self._map_rlock:
            del self._iqr_sessions[session_uuid]
            if session_uuid in self._iqr_session_timeout:
                del self._iqr_session_timeout[session_uuid]
                del self._iqr_session_last_access[session_uuid]
