"""
Top Models Fetcher

Fetches and processes the top N models from HuggingFace Hub.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .hf_client import HuggingFaceClient

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Structured model information."""

    model_id: str
    author: str
    model_name: str
    downloads: int
    likes: int
    tags: list[str]
    pipeline_tag: Optional[str]
    library_name: Optional[str]
    last_modified: Optional[datetime]
    created_at: Optional[datetime]
    private: bool
    gated: bool
    sha: Optional[str]
    siblings: list[dict] = field(default_factory=list)  # File list
    card_data: dict = field(default_factory=dict)  # Model card metadata

    @property
    def org_name(self) -> str:
        """Get organization/author name."""
        return self.author

    @property
    def safe_filename(self) -> str:
        """Get a safe filename for this model."""
        return self.model_id.replace("/", "_")

    @property
    def has_safetensors(self) -> bool:
        """Check if model uses safetensors format."""
        return any(s.get("rfilename", "").endswith(".safetensors") for s in self.siblings)

    @property
    def has_pickle(self) -> bool:
        """Check if model has pickle files (security risk)."""
        risky_extensions = [".bin", ".pkl", ".pickle", ".pt", ".pth"]
        return any(
            any(s.get("rfilename", "").endswith(ext) for ext in risky_extensions)
            for s in self.siblings
        )

    @property
    def file_count(self) -> int:
        """Get total number of files."""
        return len(self.siblings)

    @property
    def total_size_bytes(self) -> int:
        """Get total size of all files in bytes."""
        return sum(s.get("size", 0) for s in self.siblings)

    @property
    def total_size_gb(self) -> float:
        """Get total size in gigabytes."""
        return self.total_size_bytes / (1024**3)

    @property
    def license(self) -> Optional[str]:
        """Get license from card data."""
        return self.card_data.get("license")

    @property
    def is_verified_org(self) -> bool:
        """Check if the author is a verified organization."""
        # Major verified orgs on HuggingFace
        verified_orgs = {
            "meta-llama",
            "google",
            "microsoft",
            "facebook",
            "openai",
            "huggingface",
            "mistralai",
            "stabilityai",
            "bigscience",
            "EleutherAI",
            "tiiuae",
            "Qwen",
            "deepseek-ai",
            "nvidia",
            "databricks",
            "NousResearch",
            "allenai",
            "anthropic",
        }
        return self.author in verified_orgs


def get_top_models(
    limit: int = 50,
    token: Optional[str] = None,
) -> list[ModelInfo]:
    """
    Fetch top models from HuggingFace Hub.

    Args:
        limit: Number of models to fetch
        token: Optional HF API token

    Returns:
        List of ModelInfo objects
    """
    logger.info(f"Fetching top {limit} models from HuggingFace Hub")

    with HuggingFaceClient(token=token) as client:
        raw_models = client.get_models(sort="downloads", limit=limit)

    models = []
    for raw in raw_models:
        try:
            model_id = raw.get("id", raw.get("modelId", ""))
            parts = model_id.split("/", 1)
            author = parts[0] if len(parts) > 1 else ""
            model_name = parts[1] if len(parts) > 1 else parts[0]

            # Parse dates
            last_modified = None
            if raw.get("lastModified"):
                try:
                    last_modified = datetime.fromisoformat(
                        raw["lastModified"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            created_at = None
            if raw.get("createdAt"):
                try:
                    created_at = datetime.fromisoformat(raw["createdAt"].replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass

            model = ModelInfo(
                model_id=model_id,
                author=author,
                model_name=model_name,
                downloads=raw.get("downloads", 0),
                likes=raw.get("likes", 0),
                tags=raw.get("tags", []),
                pipeline_tag=raw.get("pipeline_tag"),
                library_name=raw.get("library_name"),
                last_modified=last_modified,
                created_at=created_at,
                private=raw.get("private", False),
                gated=raw.get("gated", False) if raw.get("gated") else False,
                sha=raw.get("sha"),
                siblings=raw.get("siblings", []),
                card_data=raw.get("cardData", {}),
            )
            models.append(model)
            logger.debug(f"Processed model: {model_id} ({model.downloads:,} downloads)")

        except Exception as e:
            logger.error(f"Failed to process model {raw.get('id', 'unknown')}: {e}")
            continue

    logger.info(f"Successfully processed {len(models)} models")
    return models


def filter_models(
    models: list[ModelInfo],
    min_downloads: int = 0,
    exclude_private: bool = True,
    exclude_gated: bool = False,
    require_library: Optional[str] = None,
) -> list[ModelInfo]:
    """
    Filter models based on criteria.

    Args:
        models: List of models to filter
        min_downloads: Minimum download count
        exclude_private: Exclude private models
        exclude_gated: Exclude gated models
        require_library: Only include models using this library

    Returns:
        Filtered list of models
    """
    filtered = []

    for model in models:
        if model.downloads < min_downloads:
            continue
        if exclude_private and model.private:
            continue
        if exclude_gated and model.gated:
            continue
        if require_library and model.library_name != require_library:
            continue
        filtered.append(model)

    logger.info(f"Filtered {len(models)} models to {len(filtered)}")
    return filtered
