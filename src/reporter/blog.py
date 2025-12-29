"""
Blog generator for HuggingHugh.

Generates blog index and individual post pages from markdown content.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import markdown
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """
    Parse YAML frontmatter from markdown content.

    Args:
        content: Raw markdown content with frontmatter

    Returns:
        Tuple of (metadata dict, content without frontmatter)
    """
    if not content.startswith("---"):
        return {}, content

    # Find the closing ---
    end_match = re.search(r"\n---\n", content[3:])
    if not end_match:
        return {}, content

    frontmatter = content[3 : end_match.start() + 3]
    body = content[end_match.end() + 3 :]

    # Simple YAML parsing (just key: value pairs)
    metadata = {}
    for line in frontmatter.strip().split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            # Convert types
            if value.isdigit():
                value = int(value)
            elif value.lower() in ("true", "false"):
                value = value.lower() == "true"

            metadata[key] = value

    return metadata, body


class BlogGenerator:
    """Generates blog pages from markdown content."""

    def __init__(
        self,
        templates_dir: Path,
        content_dir: Path,
        output_dir: Path,
        base_url: str = "",
        site_url: str = "https://hugginghugh.com",
    ):
        """
        Initialize blog generator.

        Args:
            templates_dir: Directory containing Jinja2 templates
            content_dir: Directory containing blog markdown files
            output_dir: Directory for output HTML files
            base_url: Base URL for relative links
            site_url: Absolute URL for SEO
        """
        self.templates_dir = Path(templates_dir)
        self.content_dir = Path(content_dir)
        self.output_dir = Path(output_dir)
        self.base_url = base_url.rstrip("/")
        self.site_url = site_url.rstrip("/")

        # Set up Jinja2
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=True,
        )

        # Set up Markdown converter
        self.md = markdown.Markdown(
            extensions=[
                "fenced_code",
                "tables",
                "toc",
                "meta",
            ]
        )

    def load_posts(self) -> list[dict[str, Any]]:
        """
        Load all blog posts from the content directory.

        Returns:
            List of post metadata dictionaries, sorted by date descending
        """
        blog_dir = self.content_dir / "blog"
        if not blog_dir.exists():
            logger.warning(f"Blog content directory not found: {blog_dir}")
            return []

        posts = []
        for md_file in blog_dir.glob("*.md"):
            try:
                content = md_file.read_text()
                metadata, body = parse_frontmatter(content)

                if not metadata.get("title") or not metadata.get("slug"):
                    logger.warning(f"Skipping {md_file}: missing title or slug")
                    continue

                # Convert markdown to HTML
                self.md.reset()
                html_content = self.md.convert(body)

                # Parse date
                date_str = metadata.get("date", "")
                if isinstance(date_str, str):
                    try:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    except ValueError:
                        date_obj = datetime.now()
                else:
                    date_obj = datetime.now()

                post = {
                    "title": metadata.get("title", ""),
                    "slug": metadata.get("slug", ""),
                    "date": date_obj.strftime("%B %d, %Y"),
                    "date_iso": date_obj.strftime("%Y-%m-%d"),
                    "date_obj": date_obj,
                    "category": metadata.get("category", "General"),
                    "excerpt": metadata.get("excerpt", ""),
                    "read_time": metadata.get("read_time", 5),
                    "content": html_content,
                    "file": md_file.name,
                }

                posts.append(post)
                logger.debug(f"Loaded blog post: {post['title']}")

            except Exception as e:
                logger.error(f"Error loading {md_file}: {e}")

        # Sort by date descending
        posts.sort(key=lambda x: x["date_obj"], reverse=True)

        return posts

    def generate_blog_index(self, posts: list[dict[str, Any]]) -> Path:
        """
        Generate the blog index page.

        Args:
            posts: List of post metadata

        Returns:
            Path to generated index.html
        """
        template = self.env.get_template("blog_index.html")

        context = {
            "base_url": self.base_url,
            "site_url": self.site_url,
            "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "posts": posts,
        }

        html_content = template.render(**context)

        # Create blog directory
        blog_output = self.output_dir / "blog"
        blog_output.mkdir(parents=True, exist_ok=True)

        index_file = blog_output / "index.html"
        index_file.write_text(html_content)

        logger.info(f"Blog index generated: {index_file} ({len(posts)} posts)")
        return index_file

    def generate_blog_post(
        self,
        post: dict[str, Any],
        all_posts: list[dict[str, Any]],
    ) -> Path:
        """
        Generate an individual blog post page.

        Args:
            post: Post metadata dictionary
            all_posts: All posts for related posts feature

        Returns:
            Path to generated post HTML
        """
        template = self.env.get_template("blog_post.html")

        # Find related posts (same category, excluding current)
        related_posts = [
            p for p in all_posts if p["slug"] != post["slug"] and p["category"] == post["category"]
        ][:3]

        # If not enough same-category posts, add recent ones
        if len(related_posts) < 3:
            other_posts = [
                p for p in all_posts if p["slug"] != post["slug"] and p not in related_posts
            ]
            related_posts.extend(other_posts[: 3 - len(related_posts)])

        context = {
            "base_url": self.base_url,
            "site_url": self.site_url,
            "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "post": post,
            "related_posts": related_posts,
        }

        html_content = template.render(**context)

        # Create blog directory
        blog_output = self.output_dir / "blog"
        blog_output.mkdir(parents=True, exist_ok=True)

        post_file = blog_output / f"{post['slug']}.html"
        post_file.write_text(html_content)

        logger.info(f"Blog post generated: {post_file}")
        return post_file

    def generate_all(self) -> list[Path]:
        """
        Generate all blog pages.

        Returns:
            List of generated file paths
        """
        posts = self.load_posts()

        if not posts:
            logger.info("No blog posts found")
            return []

        generated = []

        # Generate index
        generated.append(self.generate_blog_index(posts))

        # Generate individual posts
        for post in posts:
            generated.append(self.generate_blog_post(post, posts))

        logger.info(f"Blog generation complete: {len(generated)} pages")
        return generated
