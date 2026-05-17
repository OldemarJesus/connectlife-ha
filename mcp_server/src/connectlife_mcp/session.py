"""Per-user session management for the ConnectLife MCP server."""

import asyncio
import logging
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from connectlife.api import ConnectLifeApi, LifeConnectAuthError, LifeConnectError
from connectlife.appliance import ConnectLifeAppliance

_LOGGER = logging.getLogger(__name__)

SESSION_TTL_SECONDS: int = int(os.environ.get("CONNECTLIFE_SESSION_TTL", "86400"))
POLL_INTERVAL_SECONDS: int = int(os.environ.get("CONNECTLIFE_POLL_INTERVAL", "60"))
MAX_SESSIONS: int = int(os.environ.get("CONNECTLIFE_MAX_SESSIONS", "100"))


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class SessionError(Exception):
    """Raised when a session is not found or has expired."""


@dataclass
class Session:
    session_id: str
    username: str
    api: ConnectLifeApi
    appliances: dict[str, ConnectLifeAppliance] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)
    last_used: datetime = field(default_factory=_utcnow)
    poll_task: asyncio.Task | None = field(default=None, repr=False, compare=False)


class SessionManager:
    """Thread-safe, per-user ConnectLife session registry."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create(self, username: str, password: str) -> str:
        """Authenticate with ConnectLife and return a new session token.

        Raises:
            LifeConnectAuthError: Invalid username / password.
            ConnectionError: Transient API failure.
            RuntimeError: Server-side session limit exceeded.
        """
        async with self._lock:
            if len(self._sessions) >= MAX_SESSIONS:
                self._evict_expired_locked()
                if len(self._sessions) >= MAX_SESSIONS:
                    raise RuntimeError("Maximum concurrent sessions reached")

        api = ConnectLifeApi(username, password)
        try:
            if not await api.authenticate():
                raise LifeConnectAuthError("Authentication failed")
            await api.login()
            await api.get_appliances()
        except LifeConnectAuthError:
            raise
        except LifeConnectError as err:
            raise ConnectionError(f"ConnectLife API error: {err}") from err

        session_id = secrets.token_urlsafe(32)
        session = Session(
            session_id=session_id,
            username=username,
            api=api,
            appliances={a.device_id: a for a in api.appliances},
        )
        session.poll_task = asyncio.create_task(
            self._poll_loop(session_id),
            name=f"poll-{session_id[:8]}",
        )

        async with self._lock:
            self._sessions[session_id] = session

        _LOGGER.info("Session created for %s (id=…%s)", username, session_id[-8:])
        return session_id

    def get(self, session_id: str) -> Session:
        """Return the active session or raise SessionError."""
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionError("Session not found or expired")
        ttl = timedelta(seconds=SESSION_TTL_SECONDS)
        if _utcnow() - session.last_used > ttl:
            asyncio.create_task(self.remove(session_id))
            raise SessionError("Session has expired")
        session.last_used = _utcnow()
        return session

    async def remove(self, session_id: str) -> bool:
        """Cancel and remove a session. Returns True if the session existed."""
        async with self._lock:
            session = self._sessions.pop(session_id, None)
        if session is None:
            return False
        if session.poll_task and not session.poll_task.done():
            session.poll_task.cancel()
        _LOGGER.info("Session removed (id=…%s)", session_id[-8:])
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evict_expired_locked(self) -> None:
        """Remove all expired sessions (must be called while holding self._lock)."""
        ttl = timedelta(seconds=SESSION_TTL_SECONDS)
        now = _utcnow()
        expired = [sid for sid, s in self._sessions.items() if now - s.last_used > ttl]
        for sid in expired:
            session = self._sessions.pop(sid, None)
            if session and session.poll_task and not session.poll_task.done():
                session.poll_task.cancel()
        if expired:
            _LOGGER.debug("Evicted %d expired session(s)", len(expired))

    async def _poll_loop(self, session_id: str) -> None:
        """Background coroutine: refresh appliance state every POLL_INTERVAL_SECONDS."""
        ttl = timedelta(seconds=SESSION_TTL_SECONDS)
        while True:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            session = self._sessions.get(session_id)
            if session is None:
                return
            if _utcnow() - session.last_used > ttl:
                await self.remove(session_id)
                return
            try:
                await session.api.get_appliances()
                session.appliances = {a.device_id: a for a in session.api.appliances}
            except LifeConnectAuthError:
                _LOGGER.warning(
                    "Session auth expired during poll (id=…%s) — removing", session_id[-8:]
                )
                await self.remove(session_id)
                return
            except Exception:
                _LOGGER.debug(
                    "Poll failed for session …%s", session_id[-8:], exc_info=True
                )
