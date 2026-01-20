# API Overview

Cerise provides REST API and WebSocket interfaces for interacting with the core service.

## Basic Information

- **Base URL**: `http://localhost:8000`
- **API Version**: v1

## Endpoint List

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat` | Send chat message |
| GET | `/api/character` | Get current character info |
| GET | `/api/plugins` | Get plugin list |
| GET | `/api/health` | Health check |

For details, see:
- [REST API](./rest.md)
- [WebSocket](./websocket.md)
