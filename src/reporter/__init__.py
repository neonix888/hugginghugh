"""
Report generation module
"""

from .badges import BadgeGenerator
from .blog import BlogGenerator
from .dashboard import DashboardGenerator
from .html_generator import HTMLReportGenerator

__all__ = ["HTMLReportGenerator", "DashboardGenerator", "BlogGenerator", "BadgeGenerator"]
