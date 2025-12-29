"""
Pytest configuration and shared fixtures.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_model_info():
    """Sample model info from HuggingFace API."""
    return {
        "id": "test-org/test-model",
        "modelId": "test-org/test-model",
        "author": "test-org",
        "sha": "abc123def456",
        "lastModified": "2025-01-15T10:30:00.000Z",
        "private": False,
        "disabled": False,
        "gated": False,
        "pipeline_tag": "text-generation",
        "tags": ["pytorch", "transformers", "llama"],
        "downloads": 1500000,
        "likes": 250,
        "library_name": "transformers",
        "createdAt": "2024-06-01T00:00:00.000Z",
        "siblings": [
            {"rfilename": "config.json"},
            {"rfilename": "model.safetensors"},
            {"rfilename": "tokenizer.json"},
            {"rfilename": "README.md"},
        ],
        "spaces": [],
        "safetensors": {"total": 1, "parameters": {"F16": 7000000000}},
        "cardData": {
            "license": "apache-2.0",
            "language": ["en"],
            "tags": ["text-generation"],
        },
    }


@pytest.fixture
def sample_sbom():
    """Sample CycloneDX SBOM."""
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "timestamp": "2025-01-15T10:30:00Z",
            "tools": [{"name": "syft", "version": "1.0.0"}],
            "component": {
                "type": "application",
                "name": "test-org/test-model",
                "version": "1.0.0",
            },
        },
        "components": [
            {
                "type": "library",
                "name": "torch",
                "version": "2.1.0",
                "purl": "pkg:pypi/torch@2.1.0",
            },
            {
                "type": "library",
                "name": "transformers",
                "version": "4.35.0",
                "purl": "pkg:pypi/transformers@4.35.0",
            },
            {
                "type": "library",
                "name": "numpy",
                "version": "1.24.0",
                "purl": "pkg:pypi/numpy@1.24.0",
            },
        ],
    }


@pytest.fixture
def sample_vulnerabilities():
    """Sample Grype vulnerability scan results."""
    return {
        "matches": [
            {
                "vulnerability": {
                    "id": "CVE-2024-1234",
                    "severity": "High",
                    "description": "Test vulnerability in numpy",
                    "fix": {"versions": ["1.24.1"]},
                },
                "artifact": {
                    "name": "numpy",
                    "version": "1.24.0",
                    "type": "python",
                    "purl": "pkg:pypi/numpy@1.24.0",
                },
                "relatedVulnerabilities": [],
            },
            {
                "vulnerability": {
                    "id": "CVE-2024-5678",
                    "severity": "Medium",
                    "description": "Test vulnerability in torch",
                    "fix": {"versions": ["2.1.1"]},
                },
                "artifact": {
                    "name": "torch",
                    "version": "2.1.0",
                    "type": "python",
                    "purl": "pkg:pypi/torch@2.1.0",
                },
                "relatedVulnerabilities": [],
            },
        ],
        "source": {"type": "sbom"},
    }


@pytest.fixture
def sample_trust_factors():
    """Sample trust factors for testing."""
    return {
        "has_model_card": True,
        "has_license": True,
        "license_type": "permissive",
        "has_safetensors": True,
        "vulnerability_count": 0,
        "critical_vulns": 0,
        "high_vulns": 0,
        "downloads": 1500000,
        "likes": 250,
        "is_gated": False,
        "author_verified": True,
        "has_spaces": False,
    }


@pytest.fixture
def mock_hf_client():
    """Mock HuggingFace client."""
    client = MagicMock()
    client.get_model_info = MagicMock(
        return_value={
            "id": "test-org/test-model",
            "downloads": 1000000,
            "likes": 100,
        }
    )
    return client
