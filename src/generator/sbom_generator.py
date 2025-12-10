"""
SBOM Generator for ML Models

Generates Software Bill of Materials using Syft, with special handling
for ML model dependencies.
"""
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Known ML framework dependencies
ML_FRAMEWORK_DEPS = {
    "transformers": {
        "core": ["torch", "tensorflow", "jax", "flax"],
        "common": [
            "tokenizers",
            "safetensors",
            "huggingface-hub",
            "accelerate",
            "datasets",
            "sentencepiece",
            "protobuf",
            "regex",
            "requests",
            "tqdm",
            "filelock",
            "numpy",
            "packaging",
            "pyyaml",
        ],
    },
    "diffusers": {
        "core": ["torch"],
        "common": [
            "transformers",
            "accelerate",
            "safetensors",
            "huggingface-hub",
            "pillow",
            "numpy",
        ],
    },
    "sentence-transformers": {
        "core": ["torch"],
        "common": ["transformers", "huggingface-hub", "scipy", "numpy"],
    },
    "peft": {
        "core": ["torch"],
        "common": ["transformers", "accelerate", "huggingface-hub"],
    },
    "timm": {
        "core": ["torch"],
        "common": ["huggingface-hub", "safetensors", "pillow", "numpy"],
    },
}


class SBOMGenerator:
    """Generates SBOM for ML models."""

    def __init__(
        self,
        syft_path: str = "syft",
        output_dir: Optional[Path] = None,
    ):
        """
        Initialize SBOM generator.

        Args:
            syft_path: Path to syft executable
            output_dir: Directory for SBOM output
        """
        self.syft_path = syft_path
        self.output_dir = Path(output_dir) if output_dir else Path(".")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Verify syft is available
        self._verify_syft()

    def _verify_syft(self):
        """Verify syft is installed and accessible."""
        try:
            result = subprocess.run(
                [self.syft_path, "version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                logger.debug(f"Syft version: {result.stdout.strip()}")
            else:
                raise RuntimeError(f"Syft error: {result.stderr}")
        except FileNotFoundError:
            raise RuntimeError(f"Syft not found at {self.syft_path}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("Syft version check timed out")

    def generate_sbom(
        self,
        model_metadata: dict,
        output_format: str = "cyclonedx-json",
    ) -> dict:
        """
        Generate SBOM for a model based on its metadata.

        Args:
            model_metadata: Model metadata from ModelFetcher
            output_format: Output format (cyclonedx-json, spdx-json)

        Returns:
            SBOM dictionary
        """
        model_id = model_metadata.get("model_id", "unknown")
        logger.info(f"Generating SBOM for {model_id}")

        # Create a temporary requirements.txt based on model info
        requirements = self._infer_requirements(model_metadata)

        # Create temp directory with requirements
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Write requirements.txt
            req_file = tmppath / "requirements.txt"
            req_file.write_text("\n".join(requirements))

            # Run syft
            sbom = self._run_syft(tmppath, output_format)

            if sbom:
                # Enrich SBOM with model-specific data
                sbom = self._enrich_sbom(sbom, model_metadata)

                # Save SBOM
                safe_name = model_metadata.get("model_id", "unknown").replace("/", "_")
                sbom_file = self.output_dir / f"{safe_name}_sbom.json"
                sbom_file.write_text(json.dumps(sbom, indent=2))
                logger.info(f"SBOM saved to {sbom_file}")

                return sbom

        logger.error(f"Failed to generate SBOM for {model_id}")
        return self._create_minimal_sbom(model_metadata, requirements)

    def _infer_requirements(self, model_metadata: dict) -> list[str]:
        """
        Infer Python requirements from model metadata.

        Args:
            model_metadata: Model metadata

        Returns:
            List of requirement strings
        """
        requirements = []

        # Get library name
        library = model_metadata.get("library_name", "transformers")

        # Add base library
        if library:
            requirements.append(library)

        # Add known dependencies for the library
        if library in ML_FRAMEWORK_DEPS:
            deps = ML_FRAMEWORK_DEPS[library]
            requirements.extend(deps.get("common", []))

            # Add a core framework (default to torch)
            core = deps.get("core", [])
            if core:
                requirements.append(core[0])  # Usually torch

        # Check config for additional hints
        config = model_metadata.get("model_config", {})

        # Check architecture type for additional deps
        arch = config.get("architectures", [])
        if arch:
            arch_name = arch[0].lower() if arch else ""

            # Vision models
            if "vit" in arch_name or "clip" in arch_name:
                requirements.append("pillow")
                requirements.append("torchvision")

            # Audio models
            if "whisper" in arch_name or "wav2vec" in arch_name:
                requirements.append("librosa")
                requirements.append("soundfile")

        # Check for tokenizer type
        tokenizer_class = config.get("tokenizer_class", "")
        if "sentencepiece" in tokenizer_class.lower():
            requirements.append("sentencepiece")

        # Check tags for additional hints
        tags = model_metadata.get("tags", [])
        if "onnx" in tags:
            requirements.append("onnx")
            requirements.append("onnxruntime")

        # Remove duplicates while preserving order
        seen = set()
        unique_reqs = []
        for req in requirements:
            if req.lower() not in seen:
                seen.add(req.lower())
                unique_reqs.append(req)

        logger.debug(f"Inferred {len(unique_reqs)} requirements for {model_metadata.get('model_id')}")
        return unique_reqs

    def _run_syft(self, target_dir: Path, output_format: str) -> Optional[dict]:
        """
        Run syft on a directory.

        Args:
            target_dir: Directory to scan
            output_format: Output format

        Returns:
            SBOM dictionary or None
        """
        try:
            result = subprocess.run(
                [
                    self.syft_path,
                    f"dir:{target_dir}",
                    "-o", output_format,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                logger.error(f"Syft error: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logger.error("Syft scan timed out")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse syft output: {e}")
            return None

    def _enrich_sbom(self, sbom: dict, model_metadata: dict) -> dict:
        """
        Enrich SBOM with model-specific metadata.

        Args:
            sbom: Base SBOM from syft
            model_metadata: Model metadata

        Returns:
            Enriched SBOM
        """
        # Add model metadata as a component
        model_component = {
            "type": "machine-learning-model",
            "name": model_metadata.get("model_id", "unknown"),
            "version": model_metadata.get("sha", "unknown")[:8] if model_metadata.get("sha") else "unknown",
            "description": f"HuggingFace model: {model_metadata.get('model_id')}",
            "properties": [
                {"name": "hf:model_id", "value": model_metadata.get("model_id", "")},
                {"name": "hf:author", "value": model_metadata.get("author", "")},
                {"name": "hf:downloads", "value": str(model_metadata.get("downloads", 0))},
                {"name": "hf:likes", "value": str(model_metadata.get("likes", 0))},
                {"name": "hf:library", "value": model_metadata.get("library_name", "")},
                {"name": "hf:pipeline_tag", "value": model_metadata.get("pipeline_tag", "")},
                {"name": "hf:has_safetensors", "value": str(model_metadata.get("has_safetensors", False))},
                {"name": "hf:has_pickle", "value": str(model_metadata.get("has_pickle", False))},
                {"name": "hf:total_size_gb", "value": str(model_metadata.get("total_size_gb", 0))},
            ],
        }

        # Add license if known
        if model_metadata.get("license"):
            model_component["licenses"] = [{"license": {"id": model_metadata["license"]}}]

        # Insert model as first component
        if "components" in sbom:
            sbom["components"].insert(0, model_component)
        else:
            sbom["components"] = [model_component]

        # Update metadata
        if "metadata" not in sbom:
            sbom["metadata"] = {}

        sbom["metadata"]["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Handle tools - can be list (old format) or dict with "components" (new format)
        tools = sbom["metadata"].get("tools")
        hugginghugh_tool = {
            "vendor": "HuggingHugh",
            "name": "hugginghugh-sbom-generator",
            "version": "0.1.0",
        }

        if tools is None:
            sbom["metadata"]["tools"] = [hugginghugh_tool]
        elif isinstance(tools, list):
            tools.append(hugginghugh_tool)
        elif isinstance(tools, dict):
            # CycloneDX 1.5+ format: tools: {components: [...]}
            if "components" in tools and isinstance(tools["components"], list):
                tools["components"].append(hugginghugh_tool)
            else:
                tools["components"] = [hugginghugh_tool]
        else:
            sbom["metadata"]["tools"] = [hugginghugh_tool]

        return sbom

    def _create_minimal_sbom(
        self,
        model_metadata: dict,
        requirements: list[str],
    ) -> dict:
        """
        Create a minimal SBOM when syft fails.

        Args:
            model_metadata: Model metadata
            requirements: Inferred requirements

        Returns:
            Minimal SBOM dictionary
        """
        components = []

        # Add model as component
        components.append({
            "type": "machine-learning-model",
            "name": model_metadata.get("model_id", "unknown"),
            "version": model_metadata.get("sha", "unknown")[:8] if model_metadata.get("sha") else "unknown",
            "properties": [
                {"name": "hf:model_id", "value": model_metadata.get("model_id", "")},
                {"name": "hf:author", "value": model_metadata.get("author", "")},
                {"name": "hf:library", "value": model_metadata.get("library_name", "")},
            ],
        })

        # Add inferred dependencies
        for req in requirements:
            components.append({
                "type": "library",
                "name": req,
                "version": "inferred",
                "purl": f"pkg:pypi/{req}",
            })

        return {
            "bomFormat": "CycloneDX",
            "specVersion": "1.5",
            "version": 1,
            "metadata": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "tools": [{
                    "vendor": "HuggingHugh",
                    "name": "hugginghugh-sbom-generator",
                    "version": "0.1.0",
                }],
            },
            "components": components,
        }
