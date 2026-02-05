# Plugin Development Guide

Cerise Core plugins run as an external process (stdio) or an external service (HTTP). They communicate with Core via **JSON-RPC 2.0** and expose a set of **abilities/tools** that can be called by the runtime/LLM.

This page covers: directory layout, `manifest.json`, the protocol, configuration, permissions, dependency install, SDKs, and debugging tips.

---

## 1. What you build

A plugin is:

- a directory
- a `manifest.json`
- an entrypoint executable/script

Lifecycle:

- Core starts the plugin
- Core sends `initialize`
- Plugin returns abilities
- Core sends `execute` for tool calls
- Plugin returns `{ success, data|error, emotion_hint }`

---

## 2. Directory layout

Recommended (Python example):

```
my-plugin/
  manifest.json
  main.py
  requirements.txt      # optional
  _conf_schema.json      # optional, recommended (Star Config schema)
```

`name` must be a safe short name (recommend `kebab-case`), and must not contain `/`, `\\` or `:`.

---

## 3. manifest.json

Example (stdio + Node.js):

```json
{
  "name": "web-search",
  "version": "1.0.0",
  "display_name": "Web Search",
  "description": "Search the web",
  "runtime": {
    "language": "nodejs",
    "entry": "index.js",
    "command": "node index.js",
    "transport": "stdio"
  },
  "abilities": [
    {
      "name": "web_search",
      "description": "Search the web",
      "parameters": {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"]
      }
    }
  ]
}
```

Key fields:

- `runtime.transport`: `stdio` or `http`
- `runtime.command`: optional explicit command (highest priority for stdio)
- `runtime.http_url`: required for HTTP transport (Core POSTs to `${http_url}/rpc`)
- `abilities[]`: static abilities (Core will prefer abilities returned from `initialize` if provided)

---

## 4. Ability (tool) schema

Each ability should include:

- `name` (unique, prefer `snake_case` + plugin prefix)
- `description`
- `parameters` (JSON Schema, OpenAI function-calling style)

Core also accepts `inputSchema` / `input_schema` and normalizes it into `parameters`.

---

## 5. JSON-RPC protocol

- newline-delimited JSON (one JSON object per line)
- stdout is reserved for protocol messages; write logs to stderr

### initialize

Request:

```json
{"jsonrpc":"2.0","method":"initialize","params":{"plugin_name":"web-search","config":{},"permissions":[]},"id":1}
```

Response:

```json
{"jsonrpc":"2.0","result":{"success":true,"abilities":[{"name":"web_search","description":"...","parameters":{}}]},"id":1}
```

Core will look for abilities in: `result.abilities` / `result.skills` / `result.tools` / `result.mcp.tools`.

### execute

Request:

```json
{
  "jsonrpc": "2.0",
  "method": "execute",
  "params": {
    "ability": "web_search",
    "params": {"query": "cerise"},
    "context": {"user_id": "u1", "session_id": "s1", "permissions": []}
  },
  "id": 2
}
```

Response:

```json
{"jsonrpc":"2.0","result":{"success":true,"data":{},"error":null,"emotion_hint":"satisfied"},"id":2}
```

`health` returns `{ "healthy": true }`. `shutdown` returns `{ "success": true }` and the plugin should exit.

---

## 6. Configuration (Star Config)

For user-facing configuration, Cerise uses **Star Config**:

- Schema: `_conf_schema.json` in plugin directory
- Stored config: under Cerise data dir (`stars/*_config.json`)
- Passed to plugin as `initialize.params.config`

Admin endpoints:

- `GET /admin/stars/{name}/schema`
- `GET /admin/stars/{name}/config`
- `PUT /admin/stars/{name}/config`

---

## 7. Permissions & security

- CapabilityScheduler controls whether a tool is visible/usable.
- `context.permissions` is passed into `execute`; your plugin should enforce permission checks for sensitive operations.
- Validate all inputs (length limits, URL allow-lists, etc.).

Core also truncates tool outputs (default 4000 chars) to keep context clean.

---

## 8. Dependency install (optional)

If enabled (`plugins.auto_install_dependencies: true`), Core can install plugin deps:

- Python: `requirements.txt` (or `manifest.dependencies`) into per-plugin venv (`plugins.python_venv_dir`, default `.venv`)
- Node: `npm install --omit=dev`
- Go: `go mod download`

Admin endpoints:

- `POST /admin/plugins/{name}/deps/install`
- `GET /admin/plugins/{name}/deps/status`

---

## 9. SDKs

In-repo minimal SDKs:

- Python: `sdk/python/cerise_plugin/`
- Node.js: `sdk/nodejs/cerise-plugin.js`
- Go: `sdk/go/cerise_plugin.go`
- C++: `sdk/cpp/cerise_plugin.hpp`

For production plugins, vendor/copy the SDK into your plugin repo (or publish/install it as a package).
