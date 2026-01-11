#!/usr/bin/env python3
"""
Pixiv Search Plugin

A cross-language plugin example using Cerise SDK.
"""

import sys
from pathlib import Path

# Add SDK to path (in real deployment, SDK would be installed as package)
sdk_path = Path(__file__).parent.parent.parent / "sdk" / "python"
sys.path.insert(0, str(sdk_path))

from cerise_plugin import AbilityContext, AbilityResult, BasePlugin, run_plugin  # noqa: E402


class PixivSearchPlugin(BasePlugin):
    """Pixiv illustration search plugin"""

    def __init__(self):
        super().__init__()
        self.client = None

    def get_abilities(self) -> list[dict]:
        """Return abilities provided by this plugin"""
        return [
            {
                "name": "pixiv_search",
                "description": "搜索 Pixiv 上的插画作品",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "搜索关键词",
                        },
                        "count": {
                            "type": "integer",
                            "default": 5,
                            "description": "返回数量",
                        },
                    },
                    "required": ["keyword"],
                },
            }
        ]

    async def on_initialize(self, config: dict) -> bool:
        """Initialize Pixiv client"""
        self.config = config
        refresh_token = config.get("refresh_token")

        if not refresh_token:
            return True  # Will fail on execute

        try:
            from pixivpy3 import AppPixivAPI

            self.client = AppPixivAPI()
            self.client.auth(refresh_token=refresh_token)
            return True
        except ImportError:
            # pixivpy not installed
            return True
        except Exception:
            return False

    async def on_shutdown(self) -> None:
        """Cleanup"""
        self.client = None

    async def execute(
        self,
        ability: str,
        params: dict,
        context: AbilityContext,
    ) -> AbilityResult:
        """Execute ability"""
        if ability != "pixiv_search":
            return AbilityResult(
                success=False,
                error=f"Unknown ability: {ability}",
            )

        if not self.client:
            return AbilityResult(
                success=False,
                error="Pixiv 客户端未初始化",
            )

        keyword = params.get("keyword", "")
        count = params.get("count", 5)

        if not keyword:
            return AbilityResult(
                success=False,
                error="缺少搜索关键词",
            )

        try:
            result = self.client.search_illust(keyword)
            illusts = result.get("illusts", [])[:count]

            formatted = []
            for illust in illusts:
                formatted.append(
                    {
                        "id": illust.get("id"),
                        "title": illust.get("title", ""),
                        "author": illust.get("user", {}).get("name", ""),
                        "url": illust.get("image_urls", {}).get("medium", ""),
                    }
                )

            return AbilityResult(
                success=True,
                data={
                    "keyword": keyword,
                    "count": len(formatted),
                    "illustrations": formatted,
                },
                emotion_hint="excited" if formatted else "curious",
            )

        except Exception as e:
            return AbilityResult(
                success=False,
                error=str(e),
            )


if __name__ == "__main__":
    plugin = PixivSearchPlugin()
    run_plugin(plugin)
