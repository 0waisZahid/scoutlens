"""Integrity checks for the checked-in XGBoost model files."""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "models"
MANIFEST_NAME = "sha256-manifest.json"


def _model_hashes(model_dir: Path) -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(model_dir.glob("*.json"))
        if path.name != MANIFEST_NAME
    }


def write_model_manifest(model_dir: Path = MODEL_DIR) -> None:
    manifest_path = model_dir / MANIFEST_NAME
    temporary_path = manifest_path.with_suffix(".tmp")
    temporary_path.write_text(json.dumps(_model_hashes(model_dir), indent=2) + "\n", encoding="utf-8")
    temporary_path.replace(manifest_path)


def verify_model_files(model_dir: Path = MODEL_DIR) -> None:
    manifest_path = model_dir / MANIFEST_NAME
    try:
        expected = json.loads(manifest_path.read_text(encoding="utf-8"))
        actual = _model_hashes(model_dir)
        if not isinstance(expected, dict) or set(expected) != set(actual):
            raise ValueError
        if any(
            not isinstance(expected[name], str)
            or not hmac.compare_digest(expected[name], actual[name])
            for name in actual
        ):
            raise ValueError
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        raise RuntimeError("Model integrity verification failed.") from None


def verify_prediction_round_trip(actual, expected, message: str) -> None:
    if not np.allclose(actual, expected, rtol=1e-4):
        raise RuntimeError(message)
