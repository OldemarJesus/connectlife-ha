"""Shared FastMCP server instance and session manager singleton."""

import fastmcp

from .session import SessionManager

mcp = fastmcp.FastMCP(
    "ConnectLife MCP Server",
    instructions=(
        "Multi-tenant MCP server for ConnectLife smart appliances. "
        "Call 'login' first to obtain a session_id, then pass it to every other tool. "
        "Call 'logout' when done to free server resources."
    ),
)

session_manager = SessionManager()
