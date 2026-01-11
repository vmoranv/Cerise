"""
Cerise Plugin SDK for Python

Use this SDK to create plugins that communicate with Cerise Core.
"""

import asyncio
import json
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AbilityContext:
    """Context passed to ability execution"""

    user_id: str = ""
    session_id: str = ""
    permissions: list[str] = field(default_factory=list)


@dataclass
class AbilityResult:
    """Result of ability execution"""

    success: bool
    data: Any = None
    error: str | None = None
    emotion_hint: str | None = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "emotion_hint": self.emotion_hint,
        }


class BasePlugin(ABC):
    """Base class for Cerise plugins"""

    def __init__(self):
        self.config: dict = {}
        self.permissions: list[str] = []

    @abstractmethod
    def get_abilities(self) -> list[dict]:
        """Return list of abilities provided by this plugin"""

    @abstractmethod
    async def execute(
        self,
        ability: str,
        params: dict,
        context: AbilityContext,
    ) -> AbilityResult:
        """Execute an ability"""

    async def on_initialize(self, config: dict) -> bool:
        """Called when plugin is initialized"""
        self.config = config
        return True

    async def on_shutdown(self) -> None:
        """Called when plugin is shutting down"""


class PluginRunner:
    """Runs a plugin and handles JSON-RPC communication"""

    def __init__(self, plugin: BasePlugin):
        self.plugin = plugin
        self._running = False

    async def run(self) -> None:
        """Main loop: read from stdin, write to stdout"""
        self._running = True

        while self._running:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                if not line:
                    break

                request = json.loads(line.strip())
                response = await self._handle_request(request)

                if response:
                    print(json.dumps(response), flush=True)

            except json.JSONDecodeError as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": f"Parse error: {e}"},
                    "id": None,
                }
                print(json.dumps(error_response), flush=True)
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": f"Internal error: {e}"},
                    "id": None,
                }
                print(json.dumps(error_response), flush=True)

    async def _handle_request(self, request: dict) -> dict | None:
        """Handle a JSON-RPC request"""
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id")

        # Notifications have no ID
        is_notification = req_id is None

        try:
            result = await self._dispatch(method, params)
            if is_notification:
                return None
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": req_id,
            }
        except Exception as e:
            if is_notification:
                return None
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)},
                "id": req_id,
            }

    async def _dispatch(self, method: str, params: dict) -> Any:
        """Dispatch to appropriate handler"""
        if method == "initialize":
            config = params.get("config", {})
            self.plugin.permissions = params.get("permissions", [])
            success = await self.plugin.on_initialize(config)
            return {
                "success": success,
                "abilities": self.plugin.get_abilities(),
            }

        elif method == "execute":
            ability = params.get("ability", "")
            exec_params = params.get("params", {})
            context_data = params.get("context", {})

            context = AbilityContext(
                user_id=context_data.get("user_id", ""),
                session_id=context_data.get("session_id", ""),
                permissions=context_data.get("permissions", []),
            )

            result = await self.plugin.execute(ability, exec_params, context)
            return result.to_dict()

        elif method == "health":
            return {"healthy": True}

        elif method == "shutdown":
            await self.plugin.on_shutdown()
            self._running = False
            return {"success": True}

        else:
            raise ValueError(f"Unknown method: {method}")

    def send_event(self, event_type: str, data: dict) -> None:
        """Send an event notification to Core"""
        notification = {
            "jsonrpc": "2.0",
            "method": "event",
            "params": {"type": event_type, "data": data},
        }
        print(json.dumps(notification), flush=True)

    def log(self, level: str, message: str) -> None:
        """Send a log message to Core"""
        notification = {
            "jsonrpc": "2.0",
            "method": "log",
            "params": {"level": level, "message": message},
        }
        print(json.dumps(notification), flush=True)


def run_plugin(plugin: BasePlugin) -> None:
    """Run a plugin (blocking)"""
    runner = PluginRunner(plugin)
    asyncio.run(runner.run())
