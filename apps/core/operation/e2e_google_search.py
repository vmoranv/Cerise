"""End-to-end operation layer validation script."""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
import webbrowser
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .service import OperationService


def _ensure_project_root() -> None:
    project_root = Path(__file__).resolve().parents[3]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def _connect_browser(service: OperationService) -> bool:
    pattern = re.compile(r"Chrome|Google|Edge|Firefox", re.IGNORECASE)
    return service.connect_by_title(pattern)


def run_search_flow(query: str, commits_url: str) -> int:
    if os.name != "nt":
        print("Operation E2E requires Windows GUI.")
        return 1

    _ensure_project_root()
    from .service import OperationService

    service = OperationService()

    try:
        webbrowser.open("https://www.google.com")
        time.sleep(2)

        if not _connect_browser(service):
            print("Failed to connect to browser window.")
            return 1

        service.bring_to_front()

        service.hotkey("ctrl", "l")
        service.type_text("https://www.google.com")
        service.key_press("enter")
        time.sleep(2)

        service.hotkey("ctrl", "l")
        service.type_text(query)
        service.key_press("enter")
        time.sleep(3)

        service.hotkey("ctrl", "l")
        service.type_text(commits_url)
        service.key_press("enter")
        time.sleep(3)
        return 0
    finally:
        service.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Operation layer E2E validation")
    parser.add_argument("--query", default="Cerise github")
    parser.add_argument("--commits-url", default="https://github.com/vmoranv/Cerise/commits/master")
    args = parser.parse_args()

    return run_search_flow(args.query, args.commits_url)


if __name__ == "__main__":
    raise SystemExit(main())
