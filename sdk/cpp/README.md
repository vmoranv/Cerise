# Cerise Plugin SDK (C++)

Cerise Core plugins can be written in any language that can speak the stdio JSON-RPC protocol.

This C++ SDK is intentionally minimal and expects you to use a JSON library (for example `nlohmann::json`).

## Protocol (stdio transport)

- One JSON object per line (newline-delimited).
- Requests from Core:
  - `initialize` (params: `config`, `permissions`)
  - `execute` (params: `ability`/`skill`/`tool`/`name`, `params`/`arguments`, `context`)
  - `health`
  - `shutdown`
- Responses: JSON-RPC 2.0 compatible objects (`result` or `error`).

See `sdk/cpp/cerise_plugin.hpp` for a tiny runner.

