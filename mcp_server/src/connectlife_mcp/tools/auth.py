"""Authentication MCP tools: login, logout, whoami."""

from connectlife.api import LifeConnectAuthError

from ..server import mcp, session_manager
from ..session import SessionError


@mcp.tool()
async def login(username: str, password: str) -> dict:
    """Log in to ConnectLife and obtain a session token.

    The returned ``session_id`` must be passed to all other tools.
    Only username + password authentication is supported (no SSO).

    Returns a dict with ``session_id`` on success, or ``error`` on failure.
    """
    try:
        session_id = await session_manager.create(username, password)
    except LifeConnectAuthError:
        return {"error": "Invalid username or password"}
    except ConnectionError as err:
        return {"error": str(err)}
    except RuntimeError as err:
        return {"error": str(err)}
    return {"session_id": session_id, "username": username}


@mcp.tool()
async def logout(session_id: str) -> dict:
    """Log out and invalidate the session.

    Cancels background polling and frees all server-side resources.
    """
    removed = await session_manager.remove(session_id)
    if not removed:
        return {"error": "Session not found"}
    return {"message": "Logged out successfully"}


@mcp.tool()
async def whoami(session_id: str) -> dict:
    """Return information about the current session.

    Includes username, session age, and number of linked appliances.
    """
    try:
        session = session_manager.get(session_id)
    except SessionError as err:
        return {"error": str(err)}
    return {
        "username": session.username,
        "session_id": session.session_id,
        "created_at": session.created_at.isoformat(),
        "last_used": session.last_used.isoformat(),
        "appliance_count": len(session.appliances),
    }
