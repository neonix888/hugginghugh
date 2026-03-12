"""
Model Fetcher

Downloads model metadata files for SBOM analysis.
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Optional

from .hf_client import HuggingFaceClient
from .top_models import ModelInfo

logger = logging.getLogger(__name__)

# Files to download for analysis (metadata only, no weights).
# NOTE: tokenizer.json excluded - it can be 30+ MB per model and is never
# read by the SBOM generator (which only needs tokenizer_class from config.json).
METADATA_FILES = [
    "config.json",
    "tokenizer_config.json",
    "preprocessor_config.json",
    "generation_config.json",
    "special_tokens_map.json",
    "model_index.json",
    "README.md",
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
]


class ModelFetcher:
    """Fetches model metadata files for analysis."""

    def __init__(
        self,
        cache_dir: Path,
        token: Optional[str] = None,
        skip_existing: bool = True,
    ):
        """
        Initialize model fetcher.

        Args:
            cache_dir: Directory to cache downloaded files
            token: Optional HF API token
            skip_existing: Skip download if files already exist
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.token = token
        self.skip_existing = skip_existing
        self.client = HuggingFaceClient(token=token)

    def get_model_dir(self, model: ModelInfo) -> Path:
        """Get the cache directory for a model."""
        return self.cache_dir / model.safe_filename

    def fetch_model_metadata(
        self,
        model: ModelInfo,
        force: bool = False,
    ) -> dict:
        """
        Fetch metadata files for a model.

        Args:
            model: Model to fetch
            force: Force re-download even if cached

        Returns:
            Dictionary with fetch results
        """
        model_dir = self.get_model_dir(model)

        # Check if already cached
        if self.skip_existing and model_dir.exists() and not force:
            metadata_file = model_dir / "metadata.json"
            if metadata_file.exists():
                logger.debug(f"Using cached metadata for {model.model_id}")
                return json.loads(metadata_file.read_text())

        logger.info(f"Fetching metadata for {model.model_id}")
        model_dir.mkdir(parents=True, exist_ok=True)

        # Get list of files in the repo
        try:
            repo_files = self.client.list_model_files(model.model_id)
        except Exception as e:
            logger.error(f"Failed to list files for {model.model_id}: {e}")
            repo_files = []

        # Download metadata files
        downloaded_files = []
        failed_files = []

        for filename in METADATA_FILES:
            if filename in repo_files or filename == "README.md":
                result = self.client.download_file(
                    model_id=model.model_id,
                    filename=filename,
                    local_dir=model_dir,
                    force=force,
                )
                if result:
                    downloaded_files.append(filename)
                else:
                    failed_files.append(filename)

        # Analyze file types in repo
        file_analysis = self._analyze_repo_files(repo_files)

        # Build metadata result
        result = {
            "model_id": model.model_id,
            "author": model.author,
            "model_name": model.model_name,
            "downloads": model.downloads,
            "likes": model.likes,
            "tags": model.tags,
            "pipeline_tag": model.pipeline_tag,
            "library_name": model.library_name,
            "last_modified": model.last_modified.isoformat() if model.last_modified else None,
            "created_at": model.created_at.isoformat() if model.created_at else None,
            "private": model.private,
            "gated": model.gated,
            "sha": model.sha,
            "license": model.license,
            "is_verified_org": model.is_verified_org,
            "has_safetensors": model.has_safetensors,
            "has_pickle": model.has_pickle,
            "file_count": model.file_count,
            "total_size_gb": round(model.total_size_gb, 2),
            "downloaded_files": downloaded_files,
            "failed_files": failed_files,
            "repo_files": repo_files,
            "file_analysis": file_analysis,
            "cache_dir": str(model_dir),
        }

        # Save metadata
        metadata_file = model_dir / "metadata.json"
        metadata_file.write_text(json.dumps(result, indent=2, default=str))

        # Parse and save config.json if present
        config_file = model_dir / "config.json"
        if config_file.exists():
            try:
                config = json.loads(config_file.read_text())
                result["model_config"] = config
            except json.JSONDecodeError:
                logger.warning(f"Invalid config.json for {model.model_id}")

        logger.info(f"Fetched {len(downloaded_files)} files for {model.model_id}")
        return result

    def _analyze_repo_files(self, files: list[str]) -> dict:
        """
        Analyze files in the repository.

        Args:
            files: List of file paths

        Returns:
            Analysis dictionary
        """
        analysis = {
            "safetensors_files": [],
            "pytorch_files": [],
            "onnx_files": [],
            "tensorflow_files": [],
            "config_files": [],
            "tokenizer_files": [],
            "other_files": [],
            "total_files": len(files),
            "format_summary": {
                "safetensors": 0,
                "pytorch": 0,
                "onnx": 0,
                "tensorflow": 0,
            },
        }

        for filepath in files:
            filename = filepath.lower()

            if filename.endswith(".safetensors"):
                analysis["safetensors_files"].append(filepath)
                analysis["format_summary"]["safetensors"] += 1

            elif filename.endswith((".bin", ".pt", ".pth")):
                analysis["pytorch_files"].append(filepath)
                analysis["format_summary"]["pytorch"] += 1

            elif filename.endswith(".onnx"):
                analysis["onnx_files"].append(filepath)
                analysis["format_summary"]["onnx"] += 1

            elif filename.endswith((".pb", ".h5", ".keras")):
                analysis["tensorflow_files"].append(filepath)
                analysis["format_summary"]["tensorflow"] += 1

            elif filename.endswith(".json") and "config" in filename:
                analysis["config_files"].append(filepath)

            elif "tokenizer" in filename:
                analysis["tokenizer_files"].append(filepath)

            else:
                analysis["other_files"].append(filepath)

        # Determine primary format
        if analysis["format_summary"]["safetensors"] > 0:
            analysis["primary_format"] = "safetensors"
        elif analysis["format_summary"]["pytorch"] > 0:
            analysis["primary_format"] = "pytorch"
        elif analysis["format_summary"]["onnx"] > 0:
            analysis["primary_format"] = "onnx"
        elif analysis["format_summary"]["tensorflow"] > 0:
            analysis["primary_format"] = "tensorflow"
        else:
            analysis["primary_format"] = "unknown"

        return analysis

    def clear_cache(self, model: Optional[ModelInfo] = None):
        """
        Clear cached files.

        Args:
            model: Specific model to clear, or None to clear all
        """
        if model:
            model_dir = self.get_model_dir(model)
            if model_dir.exists():
                shutil.rmtree(model_dir)
                logger.info(f"Cleared cache for {model.model_id}")
        else:
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True)
                logger.info("Cleared all model cache")

    def close(self):
        """Close the client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
