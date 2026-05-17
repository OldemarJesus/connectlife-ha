# ConnectLife MCP Server

A standalone [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that exposes ConnectLife smart appliance control as MCP tools over HTTP.

It is published as a separate container image to GHCR and has **no dependency on Home Assistant**.

## Quick start (Docker / Podman)

```bash
# Pull the latest image
docker pull ghcr.io/<owner>/connectlife-mcp-server:latest

# Run (rootless-compatible — no privileged ports or root required)
docker run --rm -p 8000:8000 \
  -e FASTMCP_HOST=0.0.0.0 \
  ghcr.io/<owner>/connectlife-mcp-server:latest
```

The server binds to `0.0.0.0:8000` inside the container. Map it to a loopback port on the host for local-only access:

```bash
docker run --rm -p 127.0.0.1:8000:8000 ghcr.io/<owner>/connectlife-mcp-server:latest
```

## MCP endpoint

```
http://localhost:8000/mcp
```

Use this URL in your MCP client (e.g. Claude Desktop, Copilot Chat) with transport `streamable-http`.

## Authentication flow

There is **no server-level authentication layer**. All access control is through ConnectLife credentials.

1. Call the `login` tool with your ConnectLife `username` and `password`.
2. Use the returned `session_id` as a parameter in every subsequent tool call.
3. Call `logout` when done to release server resources.

> ⚠️ **Only expose this server to trusted clients.** Do not expose it publicly without an additional authentication proxy.

## Available tools

| Tool | Description |
|---|---|
| `login` | Log in and obtain a `session_id` |
| `logout` | Invalidate a session |
| `whoami` | Return session info |
| `list_appliances` | List all linked appliances |
| `get_appliance` | Get details for one appliance |
| `get_status` | Get all current property values |
| `get_daily_energy` | Get today's energy usage in kWh |
| `update_property` | Update a single property |
| `update_properties` | Update multiple properties at once |

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `FASTMCP_HOST` | `127.0.0.1` | Bind host (`0.0.0.0` for container use) |
| `FASTMCP_PORT` | `8000` | Bind port |
| `CONNECTLIFE_SESSION_TTL` | `86400` | Session idle TTL in seconds (24 h) |
| `CONNECTLIFE_POLL_INTERVAL` | `60` | Appliance poll interval in seconds |
| `CONNECTLIFE_MAX_SESSIONS` | `100` | Max concurrent sessions |
| `LOG_LEVEL` | `INFO` | Python log level |

## Session lifecycle

- Each `login` call starts a background polling task that refreshes appliance state every `CONNECTLIFE_POLL_INTERVAL` seconds.
- Sessions expire after `CONNECTLIFE_SESSION_TTL` seconds of inactivity.
- `logout` cancels polling immediately.

## Credentials

- Only **username + password** login is supported — the same restriction as the Home Assistant integration.
- SSO (Google, Apple, etc.) is **not** supported.
- If you use SSO, create a separate ConnectLife account and share your devices with it.

## Rootless container

The image runs as a non-root user (`uid 1000`). It is compatible with rootless Docker and Podman without any special configuration.

```bash
# Podman rootless example
podman run --rm -p 127.0.0.1:8000:8000 ghcr.io/<owner>/connectlife-mcp-server:latest
```

## Building locally

```bash
cd mcp_server
docker build -t connectlife-mcp-server .
docker run --rm -p 127.0.0.1:8000:8000 connectlife-mcp-server
```
