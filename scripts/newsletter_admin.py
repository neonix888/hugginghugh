#!/usr/bin/env python3
"""
HuggingHugh Newsletter Admin Tool

Manage newsletter subscribers from the command line.

Usage:
    python scripts/newsletter_admin.py stats          # Show subscriber stats
    python scripts/newsletter_admin.py list           # List active subscribers
    python scripts/newsletter_admin.py export         # Export to CSV
    python scripts/newsletter_admin.py export --json  # Export to JSON
    python scripts/newsletter_admin.py add EMAIL      # Add subscriber manually
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.newsletter.subscriber import SubscriberDB

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def show_stats():
    """Show subscriber statistics."""
    with SubscriberDB() as db:
        stats = db.get_subscriber_count()
        print("\nNewsletter Statistics")
        print("=" * 30)
        print(f"Total signups:    {stats['total']}")
        print(f"Active:           {stats['active']}")
        print(f"Pending:          {stats['pending']}")
        print(f"Unsubscribed:     {stats['unsubscribed']}")
        print()


def list_subscribers(limit: int = 50):
    """List active subscribers."""
    with SubscriberDB() as db:
        subscribers = db.get_active_subscribers()

        print(f"\nActive Subscribers ({len(subscribers)} total)")
        print("=" * 60)

        for i, sub in enumerate(subscribers[:limit], 1):
            date = sub.subscribed_at.strftime("%Y-%m-%d") if sub.subscribed_at else "N/A"
            print(f"{i:3}. {sub.email:<40} ({date})")

        if len(subscribers) > limit:
            print(f"\n... and {len(subscribers) - limit} more")
        print()


def export_subscribers(format: str = "csv", output_file: str = None):
    """Export subscribers to file."""
    with SubscriberDB() as db:
        data = db.export_subscribers(format=format)

        if output_file:
            Path(output_file).write_text(data)
            print(f"Exported to {output_file}")
        else:
            print(data)


def add_subscriber(email: str, source: str = "admin"):
    """Manually add a subscriber."""
    with SubscriberDB() as db:
        success, message, subscriber = db.add_subscriber(
            email=email,
            source=source,
            require_confirmation=False,  # Skip confirmation for admin adds
        )

        if success:
            print(f"Added: {email}")
            print(f"Message: {message}")
        else:
            print(f"Failed: {message}")


def main():
    parser = argparse.ArgumentParser(
        description="HuggingHugh Newsletter Admin Tool",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Stats command
    subparsers.add_parser("stats", help="Show subscriber statistics")

    # List command
    list_parser = subparsers.add_parser("list", help="List active subscribers")
    list_parser.add_argument("--limit", type=int, default=50, help="Maximum subscribers to show")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export subscribers")
    export_parser.add_argument("--json", action="store_true", help="Export as JSON (default: CSV)")
    export_parser.add_argument("--output", "-o", type=str, help="Output file path")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add subscriber manually")
    add_parser.add_argument("email", help="Email address to add")
    add_parser.add_argument("--source", default="admin", help="Source identifier")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == "stats":
            show_stats()
        elif args.command == "list":
            list_subscribers(args.limit)
        elif args.command == "export":
            format = "json" if args.json else "csv"
            export_subscribers(format, args.output)
        elif args.command == "add":
            add_subscriber(args.email, args.source)
        return 0

    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
