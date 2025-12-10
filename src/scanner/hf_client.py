"""
HuggingFace Hub API Client

Handles all interactions with the HuggingFace Hub API.
"""
import logging
from typing import Any, Optional
from pathlib import Path

import httpx
from huggingface_hub import HfApi, hf_hub_download, list_repo_files

logger = logging.getLogger(__name__)


class HuggingFaceClient:
    """Client for interacting with HuggingFace Hub API."""

    def __init__(self, token: Optional[str] = None):
        """
        Initialize HuggingFace client.

        Args:
            token: Optional HF API token for higher rate limits
        """
        self.token = token
        self.api = HfApi(token=token)
        self.base_url = "https://huggingface.co/api"
        self._client = httpx.Client(
            timeout=30.0,
            headers={"Authorization": f"Bearer {token}"} if token else {}
        )

    def get_models(
        self,
        sort: str = "downloads",
        direction: int = -1,
        limit: int = 50,
        filter_task: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Get models from HuggingFace Hub.

        Args:
            sort: Sort field (downloads, likes, lastModified)
            direction: Sort direction (-1 for descending)
            limit: Maximum number of models to return
            filter_task: Optional task filter (e.g., "text-generation")

        Returns:
            List of model metadata dictionaries
        """
        logger.info(f"Fetching top {limit} models sorted by {sort}")

        params = {
            "sort": sort,
            "direction": direction,
            "limit": limit,
            "full": "true",  # Get full metadata
        }

        if filter_task:
            params["filter"] = filter_task

        try:
            response = self._client.get(f"{self.base_url}/models", params=params)
            response.raise_for_status()
            models = response.json()
            logger.info(f"Successfully fetched {len(models)} models")
            return models
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch models: {e}")
            raise

    def get_model_info(self, model_id: str) -> dict[str, Any]:
        """
        Get detailed information about a specific model.

        Args:
            model_id: Model identifier (e.g., "meta-llama/Llama-2-7b-hf")

        Returns:
            Model metadata dictionary
        """
        logger.debug(f"Fetching info for model: {model_id}")

        try:
            response = self._client.get(f"{self.base_url}/models/{model_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch model info for {model_id}: {e}")
            raise

    def list_model_files(self, model_id: str) -> list[str]:
        """
        List all files in a model repository.

        Args:
            model_id: Model identifier

        Returns:
            List of file paths in the repository
        """
        logger.debug(f"Listing files for model: {model_id}")

        try:
            files = list_repo_files(model_id, token=self.token)
            return list(files)
        except Exception as e:
            logger.error(f"Failed to list files for {model_id}: {e}")
            raise

    def download_file(
        self,
        model_id: str,
        filename: str,
        local_dir: Path,
        force: bool = False,
    ) -> Optional[Path]:
        """
        Download a specific file from a model repository.

        Args:
            model_id: Model identifier
            filename: File to download
            local_dir: Local directory to save to
            force: Force re-download even if file exists

        Returns:
            Path to downloaded file, or None if failed
        """
        local_path = local_dir / filename

        if local_path.exists() and not force:
            logger.debug(f"File already exists: {local_path}")
            return local_path

        logger.debug(f"Downloading {filename} from {model_id}")

        try:
            downloaded_path = hf_hub_download(
                repo_id=model_id,
                filename=filename,
                local_dir=local_dir,
                token=self.token,
            )
            return Path(downloaded_path)
        except Exception as e:
            logger.warning(f"Failed to download {filename} from {model_id}: {e}")
            return None

    def get_model_readme(self, model_id: str) -> Optional[str]:
        """
        Get the README/model card content.

        Args:
            model_id: Model identifier

        Returns:
            README content as string, or None if not found
        """
        try:
            response = self._client.get(
                f"https://huggingface.co/{model_id}/raw/main/README.md"
            )
            if response.status_code == 200:
                return response.text
            return None
        except Exception as e:
            logger.warning(f"Failed to fetch README for {model_id}: {e}")
            return None

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
