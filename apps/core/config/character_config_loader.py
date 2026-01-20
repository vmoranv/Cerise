"""
Character config loading helpers.
"""

from pathlib import Path

import yaml

from .schemas import CharacterConfig


class CharacterConfigLoaderMixin:
    data_dir: Path

    def load_character_config(self, name: str = "default") -> CharacterConfig:
        """Load character configuration."""
        config_path = self.data_dir / "characters" / f"{name}.yaml"

        if not config_path.exists():
            if name == "default":
                self._create_default_character_config(config_path)
            else:
                raise FileNotFoundError(f"Character not found: {name}")

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return CharacterConfig(**data)

    def save_character_config(self, config: CharacterConfig, name: str = "default") -> None:
        """Save character configuration."""
        config_path = self.data_dir / "characters" / f"{name}.yaml"
        data = config.model_dump()

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True)

    def list_characters(self) -> list[str]:
        """List available characters."""
        chars_dir = self.data_dir / "characters"
        return [p.stem for p in chars_dir.glob("*.yaml")]

    def _create_default_character_config(self, path: Path) -> None:
        """Create default character config."""
        default = CharacterConfig()

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(default.model_dump(), f, allow_unicode=True)
