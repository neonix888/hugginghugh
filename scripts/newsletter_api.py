#!/usr/bin/env python3
"""
HuggingHugh Newsletter API Server

Runs the newsletter subscription API as a standalone service.

Usage:
    python scripts/newsletter_api.py              # Run on default port 8001
    python scripts/newsletter_api.py --port 8002  # Run on custom port
    python scripts/newsletter_api.py --init-db    # Initialize database schema

The API should be proxied through nginx:
    location /api/newsletter/ {
        proxy_pass http://127.0.0.1:8001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def init_database():
    """Initialize the newsletter database schema."""
    from src.newsletter.subscriber import SubscriberDB

    logger.info("Initializing newsletter database schema...")
    try:
        with SubscriberDB() as db:
            db.init_schema()
        logger.info("Database schema initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


def run_server(host: str, port: int):
    """Run the newsletter API server."""
    import uvicorn

    from src.newsletter.api import create_newsletter_app

    app = create_newsletter_app()

    logger.info(f"Starting newsletter API on {host}:{port}")
    logger.info("Endpoints:")
    logger.info(f"  POST /subscribe - Subscribe to newsletter")
    logger.info(f"  GET  /confirm/{{token}} - Confirm subscription")
    logger.info(f"  GET  /unsubscribe/{{token}} - Unsubscribe")
    logger.info(f"  GET  /stats - Subscriber statistics (requires X-API-Key)")
    logger.info(f"  GET  /subscribers - List subscribers (requires X-API-Key)")
    logger.info(f"  GET  /health - Health check")

    uvicorn.run(app, host=host, port=port, log_level="info")


def main():
    parser = argparse.ArgumentParser(
        description="HuggingHugh Newsletter API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8001, help="Port to bind to (default: 8001)")
    parser.add_argument(
        "--init-db", action="store_true", help="Initialize database schema and exit"
    )

    args = parser.parse_args()

    if args.init_db:
        success = init_database()
        return 0 if success else 1

    run_server(args.host, args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
