"""
SBOM Generator for ML Models

Generates Software Bill of Materials using Syft, with special handling
for ML model dependencies. Fetches real package versions from PyPI for
accurate vulnerability scanning.
"""
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

# Cache for PyPI package versions (to avoid repeated API calls)
_pypi_version_cache = {}

# Known minimum safe versions for common ML packages (based on CVE data)
# Format: package_name -> (min_safe_version, cve_id, severity, description)
KNOWN_MINIMUM_VERSIONS = {
    "torch": ("2.6.0", "CVE-2025-32434", "CRITICAL",
              "RCE via torch.load() even with weights_only=True"),
    "transformers": ("4.48.0", "GHSA-torch", "HIGH",
                     "Requires torch>=2.6.0 for safe model loading"),
    "pillow": ("10.0.1", "CVE-2023-4863", "HIGH",
               "WebP heap buffer overflow"),
    "requests": ("2.32.0", "CVE-2024-35195", "MEDIUM",
                 "Certificate verification bypass"),
    "numpy": ("1.22.0", "CVE-2021-41495", "HIGH",
              "NULL pointer dereference"),
    "scipy": ("1.10.0", "CVE-2023-25399", "MEDIUM",
              "Memory corruption in sparse arrays"),
}

# Known ML framework dependencies - expanded for better detection
ML_FRAMEWORK_DEPS = {
    "transformers": {
        "core": ["torch"],
        "common": [
            "tokenizers",
            "safetensors",
            "huggingface-hub",
            "accelerate",
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
            "opencv-python",
        ],
    },
    "sentence-transformers": {
        "core": ["torch"],
        "common": ["transformers", "huggingface-hub", "scipy", "numpy", "scikit-learn"],
    },
    "peft": {
        "core": ["torch"],
        "common": ["transformers", "accelerate", "huggingface-hub", "safetensors"],
    },
    "timm": {
        "core": ["torch"],
        "common": ["huggingface-hub", "safetensors", "pillow", "numpy", "torchvision"],
    },
    "keras": {
        "core": ["tensorflow"],
        "common": ["numpy", "pillow", "h5py", "huggingface-hub"],
    },
    "tensorflow": {
        "core": ["tensorflow"],
        "common": ["numpy", "protobuf", "h5py", "keras", "pillow"],
    },
    "jax": {
        "core": ["jax", "jaxlib"],
        "common": ["flax", "optax", "numpy", "huggingface-hub", "orbax-checkpoint"],
    },
    "flax": {
        "core": ["jax", "jaxlib", "flax"],
        "common": ["optax", "numpy", "huggingface-hub", "orbax-checkpoint", "transformers"],
    },
    "mlx": {
        "core": ["mlx"],
        "common": ["numpy", "huggingface-hub", "safetensors", "transformers"],
    },
    "mlx-lm": {
        "core": ["mlx"],
        "common": ["numpy", "huggingface-hub", "safetensors", "transformers", "sentencepiece"],
    },
    "onnx": {
        "core": ["onnx", "onnxruntime"],
        "common": ["numpy", "protobuf", "huggingface-hub"],
    },
    "optimum": {
        "core": ["torch"],
        "common": ["transformers", "onnx", "onnxruntime", "huggingface-hub", "accelerate"],
    },
    "trl": {
        "core": ["torch"],
        "common": ["transformers", "accelerate", "peft", "datasets", "huggingface-hub"],
    },
    "unsloth": {
        "core": ["torch"],
        "common": ["transformers", "accelerate", "peft", "bitsandbytes", "xformers", "triton"],
    },
    "vllm": {
        "core": ["torch"],
        "common": ["transformers", "ray", "numpy", "huggingface-hub", "xformers"],
    },
    "llama-cpp-python": {
        "core": ["llama-cpp-python"],
        "common": ["numpy", "huggingface-hub"],
    },
    "ctransformers": {
        "core": ["ctransformers"],
        "common": ["huggingface-hub", "numpy"],
    },
    "auto-gptq": {
        "core": ["torch"],
        "common": ["transformers", "accelerate", "auto-gptq", "huggingface-hub", "safetensors"],
    },
    "bitsandbytes": {
        "core": ["torch"],
        "common": ["transformers", "accelerate", "bitsandbytes", "huggingface-hub"],
    },
    "setfit": {
        "core": ["torch"],
        "common": ["sentence-transformers", "transformers", "huggingface-hub", "scikit-learn"],
    },
    "span-marker": {
        "core": ["torch"],
        "common": ["transformers", "huggingface-hub", "datasets"],
    },
    "adapter-transformers": {
        "core": ["torch"],
        "common": ["transformers", "huggingface-hub"],
    },
    "speechbrain": {
        "core": ["torch"],
        "common": ["transformers", "huggingface-hub", "torchaudio", "soundfile", "librosa"],
    },
    "espnet": {
        "core": ["torch"],
        "common": ["torchaudio", "soundfile", "librosa", "numpy", "scipy"],
    },
    "fairseq": {
        "core": ["torch"],
        "common": ["numpy", "torchaudio", "sacrebleu", "sentencepiece"],
    },
    "spacy": {
        "core": ["spacy"],
        "common": ["numpy", "thinc", "huggingface-hub"],
    },
    "stanza": {
        "core": ["torch"],
        "common": ["numpy", "protobuf", "requests"],
    },
    "flair": {
        "core": ["torch"],
        "common": ["transformers", "huggingface-hub", "gensim", "numpy"],
    },
    "paddlenlp": {
        "core": ["paddlepaddle"],
        "common": ["numpy", "huggingface-hub"],
    },
    "paddlepaddle": {
        "core": ["paddlepaddle"],
        "common": ["numpy", "pillow", "protobuf"],
    },
    "mindspore": {
        "core": ["mindspore"],
        "common": ["numpy", "pillow", "protobuf"],
    },
    "open_clip": {
        "core": ["torch"],
        "common": ["torchvision", "pillow", "numpy", "huggingface-hub", "timm"],
    },
    "ultralytics": {
        "core": ["torch"],
        "common": ["torchvision", "opencv-python", "pillow", "numpy", "huggingface-hub"],
    },
    "depth-anything": {
        "core": ["torch"],
        "common": ["torchvision", "opencv-python", "pillow", "numpy", "huggingface-hub"],
    },
    "sam": {
        "core": ["torch"],
        "common": ["torchvision", "opencv-python", "pillow", "numpy", "huggingface-hub"],
    },
    "stable-baselines3": {
        "core": ["torch"],
        "common": ["gymnasium", "numpy", "huggingface-hub"],
    },
    "cleanrl": {
        "core": ["torch"],
        "common": ["gymnasium", "numpy", "wandb", "tensorboard"],
    },
    "nemo": {
        "core": ["torch"],
        "common": ["transformers", "huggingface-hub", "pytorch-lightning", "hydra-core"],
    },
    "whisper": {
        "core": ["torch"],
        "common": ["transformers", "torchaudio", "librosa", "soundfile", "numpy"],
    },
    "openai-whisper": {
        "core": ["torch"],
        "common": ["torchaudio", "tiktoken", "numpy", "ffmpeg-python"],
    },
    "gliner": {
        "core": ["torch"],
        "common": ["transformers", "huggingface-hub", "numpy"],
    },
    "colpali": {
        "core": ["torch"],
        "common": ["transformers", "huggingface-hub", "pillow", "numpy"],
    },
}

# Pipeline tag to additional dependencies mapping
PIPELINE_DEPS = {
    "text-generation": ["transformers", "accelerate"],
    "text2text-generation": ["transformers", "sentencepiece"],
    "fill-mask": ["transformers"],
    "token-classification": ["transformers", "seqeval"],
    "question-answering": ["transformers"],
    "summarization": ["transformers"],
    "translation": ["transformers", "sentencepiece", "sacremoses"],
    "text-classification": ["transformers", "scikit-learn"],
    "feature-extraction": ["transformers"],
    "sentence-similarity": ["sentence-transformers", "scipy"],
    "zero-shot-classification": ["transformers"],
    "conversational": ["transformers"],
    "table-question-answering": ["transformers", "pandas"],
    "image-classification": ["transformers", "pillow", "torchvision"],
    "image-segmentation": ["transformers", "pillow", "opencv-python"],
    "object-detection": ["transformers", "pillow", "opencv-python", "torchvision"],
    "image-to-text": ["transformers", "pillow"],
    "visual-question-answering": ["transformers", "pillow"],
    "document-question-answering": ["transformers", "pillow", "pdf2image", "pytesseract"],
    "image-to-image": ["diffusers", "pillow", "opencv-python"],
    "depth-estimation": ["transformers", "pillow", "opencv-python"],
    "video-classification": ["transformers", "decord", "opencv-python"],
    "automatic-speech-recognition": ["transformers", "torchaudio", "librosa", "soundfile"],
    "audio-classification": ["transformers", "torchaudio", "librosa"],
    "text-to-speech": ["transformers", "torchaudio", "soundfile"],
    "text-to-audio": ["transformers", "torchaudio", "soundfile"],
    "audio-to-audio": ["transformers", "torchaudio", "soundfile"],
    "voice-activity-detection": ["transformers", "torchaudio", "pyannote-audio"],
    "text-to-image": ["diffusers", "pillow", "accelerate"],
    "text-to-video": ["diffusers", "pillow", "opencv-python", "imageio"],
    "image-text-to-text": ["transformers", "pillow"],
    "unconditional-image-generation": ["diffusers", "pillow"],
    "image-feature-extraction": ["transformers", "pillow", "timm"],
    "mask-generation": ["transformers", "pillow", "opencv-python"],
    "reinforcement-learning": ["stable-baselines3", "gymnasium"],
    "robotics": ["gymnasium", "numpy"],
    "graph-ml": ["torch-geometric", "networkx"],
    "time-series-forecasting": ["transformers", "pandas", "numpy"],
    "tabular-classification": ["transformers", "pandas", "scikit-learn"],
    "tabular-regression": ["transformers", "pandas", "scikit-learn"],
}

# Architecture patterns to dependencies
ARCHITECTURE_DEPS = {
    # Vision architectures
    "vit": ["pillow", "torchvision"],
    "clip": ["pillow", "torchvision", "open-clip-torch"],
    "siglip": ["pillow", "torchvision"],
    "deit": ["pillow", "torchvision", "timm"],
    "beit": ["pillow", "torchvision", "timm"],
    "swin": ["pillow", "torchvision", "timm"],
    "convnext": ["pillow", "torchvision", "timm"],
    "resnet": ["pillow", "torchvision", "timm"],
    "efficientnet": ["pillow", "torchvision", "timm"],
    "dinov2": ["pillow", "torchvision"],
    "sam": ["pillow", "opencv-python"],
    "detr": ["pillow", "torchvision", "scipy"],
    "yolos": ["pillow", "torchvision"],
    "segformer": ["pillow", "opencv-python"],
    # Audio architectures
    "whisper": ["torchaudio", "librosa", "soundfile"],
    "wav2vec": ["torchaudio", "librosa", "soundfile"],
    "hubert": ["torchaudio", "librosa", "soundfile"],
    "speecht5": ["torchaudio", "soundfile"],
    "bark": ["torchaudio", "soundfile", "scipy"],
    "musicgen": ["torchaudio", "soundfile"],
    "encodec": ["torchaudio", "soundfile"],
    "seamless": ["torchaudio", "soundfile"],
    # Multimodal architectures
    "llava": ["pillow", "accelerate"],
    "blip": ["pillow"],
    "git": ["pillow"],
    "pix2struct": ["pillow"],
    "fuyu": ["pillow"],
    "idefics": ["pillow", "accelerate"],
    "kosmos": ["pillow"],
    "paligemma": ["pillow"],
    "qwen2_vl": ["pillow", "torchvision"],
    "internvl": ["pillow", "torchvision"],
    "florence": ["pillow", "torchvision"],
    # Language model architectures
    "llama": ["accelerate", "sentencepiece"],
    "mistral": ["accelerate"],
    "mixtral": ["accelerate"],
    "qwen": ["accelerate", "tiktoken"],
    "qwen2": ["accelerate"],
    "gemma": ["accelerate"],
    "phi": ["accelerate"],
    "falcon": ["accelerate"],
    "mpt": ["accelerate", "einops"],
    "starcoder": ["accelerate"],
    "codellama": ["accelerate", "sentencepiece"],
    "deepseek": ["accelerate"],
    "yi": ["accelerate"],
    "internlm": ["accelerate"],
    "baichuan": ["accelerate"],
    "chatglm": ["accelerate"],
    "bloom": ["accelerate"],
    "opt": ["accelerate"],
    "gpt_neox": ["accelerate"],
    "gptj": ["accelerate"],
    "rwkv": ["rwkv"],
    "mamba": ["mamba-ssm", "causal-conv1d"],
    # Encoder-only
    "bert": [],
    "roberta": [],
    "albert": [],
    "electra": [],
    "deberta": [],
    "xlm": ["sentencepiece"],
    "camembert": ["sentencepiece"],
    # Encoder-decoder
    "t5": ["sentencepiece"],
    "mt5": ["sentencepiece"],
    "bart": [],
    "mbart": ["sentencepiece"],
    "pegasus": ["sentencepiece"],
    "flan": ["sentencepiece"],
    "longt5": ["sentencepiece"],
    # Specialized
    "layoutlm": ["pillow", "pytesseract"],
    "donut": ["pillow"],
    "trocr": ["pillow"],
    "nougat": ["pillow"],
}

# Tag-based additional dependencies
TAG_DEPS = {
    "gguf": ["llama-cpp-python"],
    "ggml": ["ctransformers"],
    "gptq": ["auto-gptq", "optimum"],
    "awq": ["autoawq"],
    "exl2": ["exllamav2"],
    "4bit": ["bitsandbytes"],
    "8bit": ["bitsandbytes"],
    "lora": ["peft"],
    "qlora": ["peft", "bitsandbytes"],
    "adapter": ["peft"],
    "onnx": ["onnx", "onnxruntime"],
    "openvino": ["openvino", "optimum-intel"],
    "tensorrt": ["tensorrt"],
    "coreml": ["coremltools"],
    "tflite": ["tensorflow"],
    "safetensors": ["safetensors"],
    "mlx": ["mlx"],
    "triton": ["triton"],
    "flash-attention": ["flash-attn"],
    "flash-attn": ["flash-attn"],
    "xformers": ["xformers"],
    "deepspeed": ["deepspeed"],
    "fsdp": ["accelerate"],
    "megatron": ["megatron-lm"],
    "fp16": ["accelerate"],
    "bf16": ["accelerate"],
    "fp8": ["accelerate", "transformer-engine"],
    "int8": ["bitsandbytes"],
    "int4": ["bitsandbytes"],
}


def check_version_safety(package_name: str, version: str) -> Optional[dict]:
    """
    Check if a package version meets minimum safe version requirements.

    Args:
        package_name: Name of the package
        version: Installed version

    Returns:
        Dict with warning info if version is unsafe, None if safe
    """
    pkg_lower = package_name.lower().replace("-", "_").replace("_", "-")
    # Normalize for lookup
    for known_pkg, (min_ver, cve_id, severity, desc) in KNOWN_MINIMUM_VERSIONS.items():
        known_lower = known_pkg.lower().replace("-", "_").replace("_", "-")
        if pkg_lower == known_lower or package_name.lower() == known_pkg.lower():
            try:
                from packaging import version as pkg_version
                if pkg_version.parse(version) < pkg_version.parse(min_ver):
                    return {
                        "package": package_name,
                        "installed_version": version,
                        "minimum_safe_version": min_ver,
                        "cve_id": cve_id,
                        "severity": severity,
                        "description": desc,
                    }
            except Exception:
                pass
    return None


def get_security_recommendations(requirements: list[str]) -> list[dict]:
    """
    Get security recommendations for a list of requirements.

    Args:
        requirements: List of versioned requirements (e.g., ["torch==2.5.0"])

    Returns:
        List of security recommendations
    """
    recommendations = []

    for req in requirements:
        if "==" in req:
            parts = req.split("==")
            if len(parts) == 2:
                pkg_name, version = parts
                warning = check_version_safety(pkg_name, version)
                if warning:
                    recommendations.append(warning)

    return recommendations


def get_pypi_version(package_name: str) -> Optional[str]:
    """
    Fetch the latest version of a package from PyPI.

    Args:
        package_name: Name of the PyPI package

    Returns:
        Latest version string or None if not found
    """
    # Check cache first
    if package_name in _pypi_version_cache:
        return _pypi_version_cache[package_name]

    try:
        # Normalize package name (PyPI uses lowercase with hyphens)
        normalized = package_name.lower().replace("_", "-")
        resp = requests.get(
            f"https://pypi.org/pypi/{normalized}/json",
            timeout=10
        )
        if resp.status_code == 200:
            version = resp.json().get("info", {}).get("version")
            _pypi_version_cache[package_name] = version
            return version
    except Exception as e:
        logger.debug(f"Failed to fetch PyPI version for {package_name}: {e}")

    _pypi_version_cache[package_name] = None
    return None


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

        Uses multiple signals: library_name, pipeline_tag, architectures, tags,
        and file extensions to build a comprehensive dependency list.

        Args:
            model_metadata: Model metadata

        Returns:
            List of requirement strings with versions
        """
        requirements = set()  # Use set for automatic deduplication

        # 1. Get library name - primary signal
        library = model_metadata.get("library_name", "")
        if library:
            requirements.add(library)
            # Add known dependencies for the library
            if library in ML_FRAMEWORK_DEPS:
                deps = ML_FRAMEWORK_DEPS[library]
                requirements.update(deps.get("common", []))
                # Add core framework(s)
                core = deps.get("core", [])
                requirements.update(core)

        # 2. Pipeline tag - indicates task type
        pipeline_tag = model_metadata.get("pipeline_tag", "")
        if pipeline_tag and pipeline_tag in PIPELINE_DEPS:
            requirements.update(PIPELINE_DEPS[pipeline_tag])

        # 3. Architecture analysis - very specific signals
        config = model_metadata.get("model_config", {})
        architectures = config.get("architectures", [])
        for arch in architectures:
            arch_lower = arch.lower()
            # Check each architecture pattern
            for pattern, deps in ARCHITECTURE_DEPS.items():
                if pattern in arch_lower:
                    requirements.update(deps)

        # 4. Tokenizer hints
        tokenizer_class = config.get("tokenizer_class", "")
        if tokenizer_class:
            tok_lower = tokenizer_class.lower()
            if "sentencepiece" in tok_lower:
                requirements.add("sentencepiece")
            if "tiktoken" in tok_lower:
                requirements.add("tiktoken")
            if "bpe" in tok_lower:
                requirements.add("tokenizers")

        # 5. Tag-based detection - quantization, format, optimization
        tags = model_metadata.get("tags", [])
        tags_lower = [t.lower() for t in tags]
        for tag_pattern, deps in TAG_DEPS.items():
            if tag_pattern in tags_lower:
                requirements.update(deps)

        # 6. Model ID hints (some repos include framework in name)
        model_id = model_metadata.get("model_id", "").lower()
        if "gguf" in model_id:
            requirements.update(TAG_DEPS.get("gguf", []))
        if "gptq" in model_id:
            requirements.update(TAG_DEPS.get("gptq", []))
        if "awq" in model_id:
            requirements.update(TAG_DEPS.get("awq", []))
        if "mlx" in model_id:
            requirements.add("mlx")
            requirements.update(ML_FRAMEWORK_DEPS.get("mlx", {}).get("common", []))

        # 7. File-based detection from siblings
        siblings = model_metadata.get("siblings", [])
        file_names = [s.get("rfilename", "") for s in siblings if isinstance(s, dict)]

        has_safetensors = any(f.endswith(".safetensors") for f in file_names)
        has_gguf = any(f.endswith(".gguf") for f in file_names)
        has_onnx = any(f.endswith(".onnx") for f in file_names)
        has_pt = any(f.endswith(".pt") or f.endswith(".pth") or f.endswith(".bin") for f in file_names)
        has_tf = any(f.endswith(".h5") or f.endswith(".keras") or "tf_model" in f for f in file_names)
        has_flax = any("flax" in f.lower() for f in file_names)
        has_mlx = any("mlx" in f.lower() for f in file_names)
        has_coreml = any(f.endswith(".mlmodel") or f.endswith(".mlpackage") for f in file_names)

        if has_safetensors:
            requirements.add("safetensors")
        if has_gguf:
            requirements.add("llama-cpp-python")
        if has_onnx:
            requirements.add("onnx")
            requirements.add("onnxruntime")
        if has_pt and not library:
            requirements.add("torch")
        if has_tf:
            requirements.add("tensorflow")
            requirements.add("h5py")
        if has_flax:
            requirements.add("flax")
            requirements.add("jax")
            requirements.add("jaxlib")
        if has_mlx:
            requirements.add("mlx")
        if has_coreml:
            requirements.add("coremltools")

        # 8. Check for quantization config
        quant_config = config.get("quantization_config", {})
        if quant_config:
            quant_method = quant_config.get("quant_method", "")
            if "gptq" in quant_method.lower():
                requirements.add("auto-gptq")
                requirements.add("optimum")
            if "awq" in quant_method.lower():
                requirements.add("autoawq")
            if "bitsandbytes" in quant_method.lower() or quant_config.get("load_in_8bit") or quant_config.get("load_in_4bit"):
                requirements.add("bitsandbytes")

        # 9. Default fallback if we found nothing
        if not requirements:
            requirements.add("transformers")
            requirements.add("torch")
            requirements.add("huggingface-hub")

        # Always ensure huggingface-hub is included (needed for downloading)
        requirements.add("huggingface-hub")

        # Convert to sorted list for consistent output
        unique_reqs = sorted(requirements)

        # Fetch actual versions from PyPI for vulnerability scanning
        versioned_reqs = []
        for req in unique_reqs:
            version = get_pypi_version(req)
            if version:
                versioned_reqs.append(f"{req}=={version}")
            else:
                versioned_reqs.append(req)

        logger.info(f"Inferred {len(versioned_reqs)} dependencies for {model_metadata.get('model_id')}")
        return versioned_reqs

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
