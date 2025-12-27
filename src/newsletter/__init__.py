"""
Newsletter module for HuggingHugh.
"""
from .subscriber import SubscriberDB, Subscriber
from .api import create_newsletter_app

__all__ = ["SubscriberDB", "Subscriber", "create_newsletter_app"]
