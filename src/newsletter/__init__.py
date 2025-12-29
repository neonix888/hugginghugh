"""
Newsletter module for HuggingHugh.
"""

from .api import create_newsletter_app
from .subscriber import Subscriber, SubscriberDB

__all__ = ["SubscriberDB", "Subscriber", "create_newsletter_app"]
