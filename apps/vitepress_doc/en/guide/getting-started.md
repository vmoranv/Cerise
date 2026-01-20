# Quick Start

## Requirements

- Python 3.11+
- Node.js 18+
- pnpm

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/cerise.git
cd cerise

# Install dependencies
pnpm install

# Install Python dependencies
cd apps/core
uv sync
```

## Start Services

```bash
# Start core service
cd apps/core
uv run python main.py

# Start TTS service (optional)
cd apps/tts-server
uv run python main.py
```

## Configuration

Default configuration files will be created in `~/.cerise/` on first run. You can edit these files to customize settings.

For detailed configuration instructions, see [Configuration Guide](./configuration.md).
