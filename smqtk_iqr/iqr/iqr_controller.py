import atexit
import threading
import time
import logging
from typing import Optional, Callable, Hashable, Tuple, Type, Dict
from types import TracebackType

from smqtk_iqr.iqr import IqrSession


LOG = logging.getLogger(__name__)


class IqrController:
    """
    Main controlling object for one or more IQR Sessions.

    In order to interface with a web server, methods defined here are
    thread-safe.

    This class may be used with the ``with`` statement. This will enable the
    instance's primary lock, preventing any other action from being performed
    on the instance while inside the with statement. The lock is reentrant, so
    nested with-statements will not dead-lock.

    """

    def __init__(
        self, expire_enabled: bool = False,
        expire_check: float = 30,
        expire_callback: Optional[Callable] = None
    ) -> None:
        """
        Initialize the controller.

        Session timeout, when enabled, is set on a session-by-session basis,
        i.e. different session may have different time out values if desired.
        When expiration is not enabled, session timeout values are ignored.

        :param expire_enabled: Enable/Disable session expiry. If enabled, a
            thread is started for monitoring and removal.

        :param expire_check: Interval, in seconds, that we check for session
            expiration.

        :param expire_callback: Optional callable that should take one
            positional parameter, the session that is expiring, and is called
            when the session expires and just before it is removed from this
            controller.

            The provided function, when called, will be within this
            controller's lock.

            If expiration is NOT enabled, or if a session is not given a
            timeout, this callback function is not used.

        """
        # Map of uuid to the search state
        self._iqr_sessions: Dict[Hashable, IqrSession] = {}
        # Map of sessions with timeout's enabled and the time out value in
        # seconds
        self._iqr_session_timeout: Dict = {}
        # Map of the UNIX time a session was last accessed
        self._iqr_session_last_access: Dict = {}

        # RLock for iqr_session[*] maps.
        self._map_rlock = threading.RLock()

        self._expire_enabled = expire_enabled
        self._expire_interval = expire_check
        self._expire_thread_stop_event = threading.Event()
        # prevents calling _handle_session_expiration when not enabled
        self._expire_thread_stop_event.set()
        self._expire_thread = None  # type: Optional[threading.Thread]
        self._expire_callback = expire_callback  # type: Optional[Callable]

        # If enabled, start expiration monitor thread
        if self._expire_enabled:
            atexit.register(self.stop_expiration_monitor)
            self.start_expiration_monitor()

    def __enter__(self) -> "IqrController":
        self._map_rlock.acquire()
        return self

    def __exit__(
            self, exc_type: Optional[Type],
            exc_val: Optional[BaseException],
            exc_tb: Optional[TracebackType]
    ) -> None:
        self._map_rlock.release()

    def _handle_session_expiration(self) -> None:
        """
        Run on a separate thread periodic checks and removals of sessions that
        have expired.
        """
        while not self._expire_thread_stop_event.wait(self._expire_interval):
            # scan timeout-set sessions, removing those that have timed out
            now = time.time()
            with self._map_rlock:
                LOG.debug("Checking session expiration timeouts")
                for sid in self._iqr_session_timeout.keys():
                    to = self._iqr_session_timeout[sid]
                    la = self._iqr_session_last_access[sid]
                    t = now - la
                    if t > to:
                        LOG.debug("-> Expiring session '%s' "
                                  "(last-access: %s, timeout: %s, "
                                  "now: %s)", sid, la, to, now)
                        if hasattr(self._expire_callback, '__call__'):
                            LOG.debug("   - Executing callback")
                            # type igore because callable will not be None
                            self._expire_callback(self._iqr_sessions[sid])  # type: ignore
                        self.remove_session(sid)

        LOG.debug("End of expiration handle function")

    def start_expiration_monitor(self) -> None:
        """
        Initialize unique thread to check for session expiration if the feature
        is enabled. This does nothing if the feature is not enabled.

        We stop the previous thread if one was started.

        """
        with self._map_rlock:
            self.stop_expiration_monitor()

            if self._expire_enabled:
                LOG.debug("Starting session expiration monitor thread")
                self._expire_thread = threading.Thread(
                    target=self._handle_session_expiration
                )
                self._expire_thread.daemon = True
                self._expire_thread_stop_event.clear()
                self._expire_thread.start()

    def stop_expiration_monitor(self) -> None:
        """
        Stop the session expiration monitoring thread if one has been started.
        Otherwise this method does nothing.
        """
        with self._map_rlock:
            if self._expire_thread:
                LOG.debug("Stopping session expiration monitor thread")
                self._expire_thread_stop_event.set()
                self._expire_thread.join()
                self._expire_thread = None
                LOG.debug("Stopping session expiration monitor thread -- Done")

    def session_uuids(self) -> Tuple:
        """
        Return a tuple of all currently registered IqrSessions.

        This does NOT update session last access in regards to session
        expiration.

        :return: a tuple of all currently registered IqrSessions.

        """
        with self._map_rlock:
            return tuple(self._iqr_sessions)

    def has_session_uuid(self, session_uuid: Hashable) -> bool:
        """ Check if this controller contains a session referenced by the given
        ID.

        Performance using this function is faster compared to getting all UUIDs
        and performing a linear search (because hash tables).

        This does NOT update session last access in regards to session
        expiration.

        :param session_uuid: Possible UUID of a session

        :return: True of the given UUID references a session in this controller
            and false if not.

        """
        with self._map_rlock:
            return session_uuid in self._iqr_sessions

    def add_session(self, iqr_session: IqrSession, timeout: float = 0) -> Hashable:
        """ Initialize a new IQR Session, returning the uuid of that session

        This controller indexes the given session by its UUID.

        :param iqr_session: The IqrSession instance to add

        :param timeout: The optional timeout, in seconds.

        :return: UUID of new IQR Session

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

    def get_session(self, session_uuid: Hashable) -> IqrSession:
        """
        Return the session instance for the given UUID

        :raises KeyError: The given UUID doesn't exist in this controller.

        :param session_uuid: UUID if the session to get

        :return: IqrSession instance for the given UUID

        """
        with self._map_rlock:
            if session_uuid in self._iqr_session_timeout:
                self._iqr_session_last_access[session_uuid] = time.time()
            return self._iqr_sessions[session_uuid]

    def remove_session(self, session_uuid: Hashable) -> None:
        """
        Remove an IQR Session by session UUID.

        :raises KeyError: The given UUID doesn't exist in this controller.

        :param session_uuid: Session UUID

        """
        with self._map_rlock:
            del self._iqr_sessions[session_uuid]
            if session_uuid in self._iqr_session_timeout:
                del self._iqr_session_timeout[session_uuid]
                del self._iqr_session_last_access[session_uuid]
