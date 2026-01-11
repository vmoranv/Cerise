"""
Ability Registry

Central registry for managing abilities (built-in and plugins).
"""

import importlib.util
import json
import logging
from pathlib import Path

from .base import AbilityContext, AbilityResult, BaseAbility

logger = logging.getLogger(__name__)


class AbilityRegistry:
    """Registry for ability management"""

    _abilities: dict[str, BaseAbility] = {}
    _ability_classes: dict[str, type[BaseAbility]] = {}

    @classmethod
    def register(cls, ability: BaseAbility) -> None:
        """Register an ability instance"""
        if ability.name in cls._abilities:
            logger.warning(f"Ability '{ability.name}' already registered, overwriting")
        cls._abilities[ability.name] = ability
        logger.info(f"Registered ability: {ability.name} ({ability.display_name})")

    @classmethod
    def register_class(cls, ability_class: type[BaseAbility]) -> None:
        """Register an ability class for lazy instantiation"""
        # Create a temporary instance to get the name
        # This assumes the class can be instantiated without arguments
        cls._ability_classes[ability_class.__name__] = ability_class

    @classmethod
    def get(cls, name: str) -> BaseAbility | None:
        """Get an ability by name"""
        return cls._abilities.get(name)

    @classmethod
    def list_abilities(cls) -> list[str]:
        """List all registered ability names"""
        return list(cls._abilities.keys())

    @classmethod
    def get_all(cls) -> dict[str, BaseAbility]:
        """Get all registered abilities"""
        return cls._abilities.copy()

    @classmethod
    async def execute(
        cls,
        ability_name: str,
        params: dict,
        context: AbilityContext,
    ) -> AbilityResult:
        """Execute an ability by name"""
        ability = cls.get(ability_name)
        if not ability:
            return AbilityResult(
                success=False,
                error=f"Ability '{ability_name}' not found",
            )

        # Check permissions
        for perm in ability.required_permissions:
            if perm not in context.permissions:
                return AbilityResult(
                    success=False,
                    error=f"Missing permission: {perm}",
                )

        # Validate parameters
        if not await ability.validate_params(params):
            return AbilityResult(
                success=False,
                error="Invalid parameters",
            )

        # Execute
        try:
            return await ability.execute(params, context)
        except Exception as e:
            logger.exception(f"Error executing ability '{ability_name}'")
            return AbilityResult(
                success=False,
                error=str(e),
            )

    @classmethod
    async def load_plugins(cls, plugins_dir: str | Path) -> None:
        """Load plugins from a directory"""
        plugins_path = Path(plugins_dir)
        if not plugins_path.exists():
            logger.warning(f"Plugins directory not found: {plugins_path}")
            return

        for plugin_dir in plugins_path.iterdir():
            if not plugin_dir.is_dir() or plugin_dir.name.startswith("_"):
                continue

            manifest_path = plugin_dir / "manifest.json"
            if not manifest_path.exists():
                logger.warning(f"No manifest.json in {plugin_dir}")
                continue

            try:
                await cls._load_plugin(plugin_dir, manifest_path)
            except Exception:
                logger.exception(f"Failed to load plugin from {plugin_dir}")

    @classmethod
    async def _load_plugin(cls, plugin_dir: Path, manifest_path: Path) -> None:
        """Load a single plugin"""
        with open(manifest_path) as f:
            manifest = json.load(f)

        entry_point = plugin_dir / manifest["entry_point"]
        class_name = manifest["class_name"]

        # Dynamic import
        spec = importlib.util.spec_from_file_location(manifest["name"], entry_point)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            ability_class = getattr(module, class_name)
            ability_instance = ability_class()

            await ability_instance.on_load()
            cls.register(ability_instance)

            logger.info(f"Loaded plugin: {manifest['name']} v{manifest['version']}")

    @classmethod
    def get_tool_schemas(cls) -> list[dict]:
        """Get all abilities as OpenAI-compatible tool schemas"""
        return [ability.to_tool_schema() for ability in cls._abilities.values()]

    @classmethod
    def unregister(cls, name: str) -> bool:
        """Unregister an ability"""
        if name in cls._abilities:
            del cls._abilities[name]
            return True
        return False

    @classmethod
    async def unload_all(cls) -> None:
        """Unload all abilities"""
        for ability in cls._abilities.values():
            await ability.on_unload()
        cls._abilities.clear()
