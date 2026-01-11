"""
Cerise Core - Main Entry Point

Run with: python -m apps.core.main
Or: uvicorn apps.core.main:app --reload
"""

import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.core.api import create_app  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Create app instance
app = create_app()


def main():
    """Main entry point"""
    import uvicorn

    uvicorn.run(
        "apps.core.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
