"""
Newsletter API endpoints.

A minimal FastAPI application for handling newsletter signups.
Can run standalone or be integrated into a larger application.
"""

import logging
import os
import secrets
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, EmailStr, field_validator

from .subscriber import SubscriberDB, validate_email

logger = logging.getLogger(__name__)

# Admin API key from environment variable
ADMIN_API_KEY = os.environ.get("NEWSLETTER_ADMIN_API_KEY", "")


async def verify_admin_api_key(
    x_api_key: str = Header(None, alias="X-API-Key"),  # noqa: B008
):
    """
    Dependency to verify admin API key.

    Requires X-API-Key header matching NEWSLETTER_ADMIN_API_KEY env var.
    """
    if not ADMIN_API_KEY:
        logger.warning("NEWSLETTER_ADMIN_API_KEY not set - admin endpoints disabled")
        raise HTTPException(
            status_code=503,
            detail="Admin API not configured. Set NEWSLETTER_ADMIN_API_KEY environment variable.",
        )

    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing X-API-Key header",
        )

    # Use secrets.compare_digest to prevent timing attacks
    if not secrets.compare_digest(x_api_key, ADMIN_API_KEY):
        logger.warning(f"Invalid admin API key attempt")
        raise HTTPException(
            status_code=403,
            detail="Invalid API key",
        )

    return True


class SubscribeRequest(BaseModel):
    """Request model for newsletter subscription."""

    email: str
    source: str = "website"

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v):
        if not validate_email(v):
            raise ValueError("Invalid email address")
        return v.lower().strip()


class SubscribeResponse(BaseModel):
    """Response model for newsletter subscription."""

    success: bool
    message: str


def create_newsletter_app(
    site_url: str = "https://hugginghugh.com",
    require_confirmation: bool = False,  # Set to True for double opt-in
) -> FastAPI:
    """
    Create the newsletter FastAPI application.

    Args:
        site_url: Base URL for confirmation/unsubscribe links
        require_confirmation: Whether to require email confirmation (double opt-in)

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="HuggingHugh Newsletter API",
        description="Newsletter subscription management for HuggingHugh",
        version="1.0.0",
    )

    # CORS configuration
    allowed_origins = [
        "https://hugginghugh.com",
        "https://www.hugginghugh.com",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "ok", "service": "newsletter"}

    @app.post("/subscribe", response_model=SubscribeResponse)
    async def subscribe(request: Request, data: SubscribeRequest):
        """
        Subscribe to the newsletter.

        Accepts an email address and optional source identifier.
        Returns success status and a user-friendly message.
        """
        # Get client info for logging/security
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")[:500]

        try:
            with SubscriberDB() as db:
                success, message, subscriber = db.add_subscriber(
                    email=data.email,
                    source=data.source,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    require_confirmation=require_confirmation,
                )

                if success:
                    logger.info(f"Newsletter signup: {data.email[:3]}***@*** from {data.source}")
                else:
                    logger.warning(f"Newsletter signup failed: {message}")

                return SubscribeResponse(success=success, message=message)

        except Exception as e:
            logger.error(f"Newsletter signup error: {e}")
            raise HTTPException(status_code=500, detail="Subscription failed. Please try again.")

    @app.get("/confirm/{token}")
    async def confirm_subscription(token: str):
        """
        Confirm email subscription.

        Called when user clicks the confirmation link in their email.
        """
        try:
            with SubscriberDB() as db:
                success, message = db.confirm_subscription(token)

                # Return a simple HTML page
                html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Subscription {'Confirmed' if success else 'Error'} - HuggingHugh</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <style>
                        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                               display: flex; justify-content: center; align-items: center;
                               min-height: 100vh; margin: 0; background: #f5f5f5; }}
                        .card {{ background: white; padding: 2rem; border-radius: 8px;
                                box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; max-width: 400px; }}
                        h1 {{ color: {'#22c55e' if success else '#ef4444'}; }}
                        a {{ color: #3b82f6; }}
                    </style>
                </head>
                <body>
                    <div class="card">
                        <h1>{'Confirmed!' if success else 'Oops!'}</h1>
                        <p>{message}</p>
                        <p><a href="{site_url}">Return to HuggingHugh</a></p>
                    </div>
                </body>
                </html>
                """
                return HTMLResponse(content=html)

        except Exception as e:
            logger.error(f"Confirmation error: {e}")
            raise HTTPException(status_code=500, detail="Confirmation failed")

    @app.get("/unsubscribe/{token}")
    async def unsubscribe(token: str):
        """
        Unsubscribe from the newsletter.

        Called when user clicks the unsubscribe link in their email.
        """
        try:
            with SubscriberDB() as db:
                success, message = db.unsubscribe(token)

                html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Unsubscribed - HuggingHugh</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <style>
                        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                               display: flex; justify-content: center; align-items: center;
                               min-height: 100vh; margin: 0; background: #f5f5f5; }}
                        .card {{ background: white; padding: 2rem; border-radius: 8px;
                                box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; max-width: 400px; }}
                        h1 {{ color: #64748b; }}
                        a {{ color: #3b82f6; }}
                    </style>
                </head>
                <body>
                    <div class="card">
                        <h1>Unsubscribed</h1>
                        <p>{message}</p>
                        <p><a href="{site_url}">Return to HuggingHugh</a></p>
                    </div>
                </body>
                </html>
                """
                return HTMLResponse(content=html)

        except Exception as e:
            logger.error(f"Unsubscribe error: {e}")
            raise HTTPException(status_code=500, detail="Unsubscribe failed")

    @app.get("/stats", dependencies=[Depends(verify_admin_api_key)])
    async def get_stats():
        """
        Get subscriber statistics.

        Requires X-API-Key header with valid admin API key.
        """
        try:
            with SubscriberDB() as db:
                stats = db.get_subscriber_count()
                return stats
        except Exception as e:
            logger.error(f"Stats error: {e}")
            raise HTTPException(status_code=500, detail="Failed to get stats")

    @app.get("/subscribers", dependencies=[Depends(verify_admin_api_key)])
    async def get_subscribers():
        """
        Get all active subscribers with details.

        Requires X-API-Key header with valid admin API key.
        """
        try:
            with SubscriberDB() as db:
                subscribers = db.get_active_subscribers()
                return {
                    "total": len(subscribers),
                    "subscribers": [
                        {
                            "email": s.email,
                            "source": s.source,
                            "subscribed_at": (
                                s.subscribed_at.isoformat() if s.subscribed_at else None
                            ),
                            "confirmed": s.confirmed,
                        }
                        for s in subscribers
                    ],
                }
        except Exception as e:
            logger.error(f"Subscribers list error: {e}")
            raise HTTPException(status_code=500, detail="Failed to get subscribers")

    return app


# Create default app instance
app = create_newsletter_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
