"""
AI News Aggregation Module

Fetches, scores, and generates daily AI news digests.
"""

from .digest import DigestGenerator
from .fetcher import NewsFetcher
from .scorer import RelevanceScorer

__all__ = ["NewsFetcher", "RelevanceScorer", "DigestGenerator"]
