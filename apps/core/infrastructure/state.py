"""
State Store

Persistent state management with in-memory cache and JSON file backend.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StateStore:
    """State storage with persistence"""

    def __init__(self, storage_path: str | Path | None = None):
        self._state: dict[str, Any] = {}
        self._storage_path = Path(storage_path) if storage_path else None
        self._dirty = False
        self._lock = asyncio.Lock()

        if self._storage_path and self._storage_path.exists():
            self._load()

    def _load(self) -> None:
        """Load state from file"""
        if not self._storage_path:
            return
        try:
            with open(self._storage_path, encoding="utf-8") as f:
                self._state = json.load(f)
            logger.info(f"Loaded state from {self._storage_path}")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load state: {e}")
            self._state = {}

    def _save(self) -> None:
        """Save state to file"""
        if not self._storage_path or not self._dirty:
            return
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(self._state, f, ensure_ascii=False, indent=2)
            self._dirty = False
            logger.debug(f"Saved state to {self._storage_path}")
        except OSError as e:
            logger.error(f"Failed to save state: {e}")

    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value by key (supports dot notation)"""
        async with self._lock:
            return self._get_nested(key, default)

    def get_sync(self, key: str, default: Any = None) -> Any:
        """Synchronous get"""
        return self._get_nested(key, default)

    def _get_nested(self, key: str, default: Any = None) -> Any:
        """Get nested value using dot notation"""
        keys = key.split(".")
        value = self._state
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    async def set(self, key: str, value: Any) -> None:
        """Set a value by key (supports dot notation)"""
        async with self._lock:
            self._set_nested(key, value)
            self._dirty = True
            self._save()

    def set_sync(self, key: str, value: Any) -> None:
        """Synchronous set"""
        self._set_nested(key, value)
        self._dirty = True
        self._save()

    def _set_nested(self, key: str, value: Any) -> None:
        """Set nested value using dot notation"""
        keys = key.split(".")
        state = self._state
        for k in keys[:-1]:
            state = state.setdefault(k, {})
        state[keys[-1]] = value

    async def delete(self, key: str) -> bool:
        """Delete a key"""
        async with self._lock:
            keys = key.split(".")
            state = self._state
            for k in keys[:-1]:
                if k not in state:
                    return False
                state = state[k]
            if keys[-1] in state:
                del state[keys[-1]]
                self._dirty = True
                self._save()
                return True
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        return await self.get(key) is not None

    async def keys(self, prefix: str = "") -> list[str]:
        """Get all keys with optional prefix"""
        async with self._lock:
            if not prefix:
                return list(self._state.keys())
            return [k for k in self._state.keys() if k.startswith(prefix)]

    async def all(self) -> dict[str, Any]:
        """Get all state"""
        async with self._lock:
            return self._state.copy()

    async def clear(self) -> None:
        """Clear all state"""
        async with self._lock:
            self._state = {}
            self._dirty = True
            self._save()

    async def update(self, data: dict[str, Any]) -> None:
        """Update multiple keys"""
        async with self._lock:
            for key, value in data.items():
                self._set_nested(key, value)
            self._dirty = True
            self._save()

    def create_namespace(self, namespace: str) -> "NamespacedStore":
        """Create a namespaced store"""
        return NamespacedStore(self, namespace)


class NamespacedStore:
    """State store scoped to a namespace"""

    def __init__(self, store: StateStore, namespace: str):
        self._store = store
        self._namespace = namespace

    def _prefixed(self, key: str) -> str:
        """Add namespace prefix"""
        return f"{self._namespace}.{key}"

    async def get(self, key: str, default: Any = None) -> Any:
        return await self._store.get(self._prefixed(key), default)

    async def set(self, key: str, value: Any) -> None:
        await self._store.set(self._prefixed(key), value)

    async def delete(self, key: str) -> bool:
        return await self._store.delete(self._prefixed(key))

    async def exists(self, key: str) -> bool:
        return await self._store.exists(self._prefixed(key))
