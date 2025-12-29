"""
Newsletter subscriber management.

Stores and manages email subscribers in PostgreSQL.
"""

import hashlib
import logging
import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import psycopg2
from psycopg2.extras import RealDictCursor

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


def parse_database_url(url: str) -> dict:
    """Parse a DATABASE_URL into connection parameters."""
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "database": parsed.path.lstrip("/") or "hugginghugh",
        "user": parsed.username or "hugginghugh",
        "password": parsed.password or "",
    }


# Email validation regex
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


@dataclass
class Subscriber:
    """Represents a newsletter subscriber."""

    id: Optional[int] = None
    email: str = ""
    email_hash: str = ""
    subscribed_at: Optional[datetime] = None
    confirmed: bool = False
    confirmed_at: Optional[datetime] = None
    unsubscribed: bool = False
    unsubscribed_at: Optional[datetime] = None
    confirm_token: Optional[str] = None
    unsubscribe_token: Optional[str] = None
    source: str = "website"


def validate_email(email: str) -> bool:
    """Validate email format."""
    if not email or len(email) > 254:
        return False
    return bool(EMAIL_REGEX.match(email.lower().strip()))


def hash_email(email: str) -> str:
    """Create a hash of the email for privacy-preserving lookups."""
    normalized = email.lower().strip()
    return hashlib.sha256(normalized.encode()).hexdigest()


def generate_token() -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(32)


class SubscriberDB:
    """
    Database interface for newsletter subscribers.

    Uses PostgreSQL for storage with privacy-preserving email hashing.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        Initialize database connection.

        Connection parameters can be passed directly or via environment variables:
        - DATABASE_URL (preferred): postgresql://user:pass@host:port/dbname
        - Or individual: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
        """
        # Check for DATABASE_URL first (standard format)
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            db_config = parse_database_url(database_url)
            self.host = host or db_config["host"]
            self.port = port or db_config["port"]
            self.database = database or db_config["database"]
            self.user = user or db_config["user"]
            self.password = password or db_config["password"]
        else:
            # Fall back to individual environment variables
            self.host = host or os.environ.get("DB_HOST", "localhost")
            self.port = port or int(os.environ.get("DB_PORT", "5432"))
            self.database = database or os.environ.get("DB_NAME", "hugginghugh")
            self.user = user or os.environ.get("DB_USER", "hugginghugh")
            self.password = password or os.environ.get("DB_PASSWORD", "")
        self.conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self):
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
            )
            self.conn.autocommit = False
            logger.debug("Newsletter database connected")
        except psycopg2.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def init_schema(self):
        """Initialize the subscribers table."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS newsletter_subscribers (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(254) NOT NULL,
                    email_hash VARCHAR(64) UNIQUE NOT NULL,
                    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confirmed BOOLEAN DEFAULT FALSE,
                    confirmed_at TIMESTAMP,
                    unsubscribed BOOLEAN DEFAULT FALSE,
                    unsubscribed_at TIMESTAMP,
                    confirm_token VARCHAR(64),
                    unsubscribe_token VARCHAR(64) UNIQUE,
                    source VARCHAR(50) DEFAULT 'website',
                    ip_address VARCHAR(45),
                    user_agent TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_subscribers_email_hash
                    ON newsletter_subscribers(email_hash);
                CREATE INDEX IF NOT EXISTS idx_subscribers_confirmed
                    ON newsletter_subscribers(confirmed) WHERE confirmed = TRUE;
                CREATE INDEX IF NOT EXISTS idx_subscribers_active
                    ON newsletter_subscribers(unsubscribed) WHERE unsubscribed = FALSE;
            """
            )
            self.conn.commit()
            logger.info("Newsletter schema initialized")

    def add_subscriber(
        self,
        email: str,
        source: str = "website",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        require_confirmation: bool = True,
    ) -> tuple[bool, str, Optional[Subscriber]]:
        """
        Add a new subscriber.

        Args:
            email: Email address
            source: Where the signup came from
            ip_address: Client IP address
            user_agent: Client user agent
            require_confirmation: Whether to require email confirmation

        Returns:
            Tuple of (success, message, subscriber)
        """
        # Validate email
        if not validate_email(email):
            return False, "Invalid email address", None

        email_normalized = email.lower().strip()
        email_hashed = hash_email(email_normalized)

        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check if already subscribed
            cur.execute(
                "SELECT * FROM newsletter_subscribers WHERE email_hash = %s", (email_hashed,)
            )
            existing = cur.fetchone()

            if existing:
                if existing["unsubscribed"]:
                    # Re-subscribe
                    new_token = generate_token()
                    cur.execute(
                        """
                        UPDATE newsletter_subscribers
                        SET unsubscribed = FALSE,
                            unsubscribed_at = NULL,
                            confirmed = %s,
                            confirmed_at = %s,
                            confirm_token = %s,
                            subscribed_at = CURRENT_TIMESTAMP
                        WHERE email_hash = %s
                        RETURNING *
                    """,
                        (
                            not require_confirmation,
                            datetime.utcnow() if not require_confirmation else None,
                            new_token if require_confirmation else None,
                            email_hashed,
                        ),
                    )
                    subscriber = cur.fetchone()
                    self.conn.commit()
                    return (
                        True,
                        "Welcome back! You've been re-subscribed.",
                        self._row_to_subscriber(subscriber),
                    )
                elif not existing["confirmed"] and require_confirmation:
                    # Already pending confirmation
                    return (
                        True,
                        "Already subscribed. Check your email for confirmation.",
                        self._row_to_subscriber(existing),
                    )
                else:
                    # Already subscribed and confirmed
                    return True, "You're already subscribed!", self._row_to_subscriber(existing)

            # Add new subscriber
            confirm_token = generate_token() if require_confirmation else None
            unsubscribe_token = generate_token()

            cur.execute(
                """
                INSERT INTO newsletter_subscribers
                    (email, email_hash, confirmed, confirmed_at, confirm_token,
                     unsubscribe_token, source, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """,
                (
                    email_normalized,
                    email_hashed,
                    not require_confirmation,
                    datetime.utcnow() if not require_confirmation else None,
                    confirm_token,
                    unsubscribe_token,
                    source,
                    ip_address,
                    user_agent,
                ),
            )
            subscriber = cur.fetchone()
            self.conn.commit()

            if require_confirmation:
                return (
                    True,
                    "Thanks! Please check your email to confirm your subscription.",
                    self._row_to_subscriber(subscriber),
                )
            else:
                return True, "Thanks for subscribing!", self._row_to_subscriber(subscriber)

    def confirm_subscription(self, token: str) -> tuple[bool, str]:
        """
        Confirm a subscription using the confirmation token.

        Returns:
            Tuple of (success, message)
        """
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE newsletter_subscribers
                SET confirmed = TRUE,
                    confirmed_at = CURRENT_TIMESTAMP,
                    confirm_token = NULL
                WHERE confirm_token = %s AND confirmed = FALSE
                RETURNING id
            """,
                (token,),
            )
            result = cur.fetchone()
            self.conn.commit()

            if result:
                return True, "Your subscription is confirmed!"
            else:
                return False, "Invalid or expired confirmation link."

    def unsubscribe(self, token: str) -> tuple[bool, str]:
        """
        Unsubscribe using the unsubscribe token.

        Returns:
            Tuple of (success, message)
        """
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE newsletter_subscribers
                SET unsubscribed = TRUE,
                    unsubscribed_at = CURRENT_TIMESTAMP
                WHERE unsubscribe_token = %s AND unsubscribed = FALSE
                RETURNING id
            """,
                (token,),
            )
            result = cur.fetchone()
            self.conn.commit()

            if result:
                return True, "You've been unsubscribed. Sorry to see you go!"
            else:
                return False, "Invalid unsubscribe link or already unsubscribed."

    def get_active_subscribers(self) -> list[Subscriber]:
        """Get all active (confirmed and not unsubscribed) subscribers."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM newsletter_subscribers
                WHERE confirmed = TRUE AND unsubscribed = FALSE
                ORDER BY subscribed_at DESC
            """
            )
            return [self._row_to_subscriber(row) for row in cur.fetchall()]

    def get_subscriber_count(self) -> dict:
        """Get subscriber statistics."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE confirmed = TRUE AND unsubscribed = FALSE) as active,
                    COUNT(*) FILTER (WHERE confirmed = FALSE AND unsubscribed = FALSE) as pending,
                    COUNT(*) FILTER (WHERE unsubscribed = TRUE) as unsubscribed
                FROM newsletter_subscribers
            """
            )
            return dict(cur.fetchone())

    def export_subscribers(self, format: str = "csv") -> str:
        """
        Export active subscribers.

        Args:
            format: 'csv' or 'json'

        Returns:
            Formatted string of subscribers
        """
        subscribers = self.get_active_subscribers()

        if format == "json":
            import json

            return json.dumps(
                [
                    {"email": s.email, "subscribed_at": s.subscribed_at.isoformat()}
                    for s in subscribers
                ],
                indent=2,
            )
        else:
            lines = ["email,subscribed_at"]
            for s in subscribers:
                lines.append(f"{s.email},{s.subscribed_at.isoformat()}")
            return "\n".join(lines)

    def _row_to_subscriber(self, row: dict) -> Subscriber:
        """Convert a database row to a Subscriber object."""
        return Subscriber(
            id=row.get("id"),
            email=row.get("email", ""),
            email_hash=row.get("email_hash", ""),
            subscribed_at=row.get("subscribed_at"),
            confirmed=row.get("confirmed", False),
            confirmed_at=row.get("confirmed_at"),
            unsubscribed=row.get("unsubscribed", False),
            unsubscribed_at=row.get("unsubscribed_at"),
            confirm_token=row.get("confirm_token"),
            unsubscribe_token=row.get("unsubscribe_token"),
            source=row.get("source", "website"),
        )
