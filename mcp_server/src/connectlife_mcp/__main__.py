"""Entry point for the ConnectLife MCP server.

Usage:
    python -m connectlife_mcp

Environment variables:
    FASTMCP_HOST              Bind host  (default: 127.0.0.1)
    FASTMCP_PORT              Bind port  (default: 8000)
    CONNECTLIFE_SESSION_TTL   Session idle TTL in seconds (default: 86400)
    CONNECTLIFE_POLL_INTERVAL Appliance poll interval in seconds (default: 60)
    CONNECTLIFE_MAX_SESSIONS  Max concurrent sessions (default: 100)
    LOG_LEVEL                 Python log level (default: INFO)
"""

import logging
import os

from .server import mcp

# Trigger tool registration (all @mcp.tool() decorators in sub-modules).
from . import tools  # noqa: F401

_LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, _LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def main() -> None:
    """Start the HTTP MCP server (blocking)."""
    mcp.run(transport="http")


if __name__ == "__main__":
    main()
