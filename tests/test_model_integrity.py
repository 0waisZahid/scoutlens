import json

import pytest

from ml import train_and_tune as tt
from ml.model_integrity import (
    MANIFEST_NAME,
    verify_model_files,
    verify_prediction_round_trip,
    write_model_manifest,
)


def test_model_manifest_detects_modified_files_and_missing_entries(tmp_path):
    model = tmp_path / "model.json"
    model.write_text('{"tree": 1}', encoding="utf-8")
    write_model_manifest(tmp_path)
    verify_model_files(tmp_path)

    model.write_text('{"tree": 2}', encoding="utf-8")
    with pytest.raises(RuntimeError, match="integrity verification failed"):
        verify_model_files(tmp_path)

    write_model_manifest(tmp_path)
    (tmp_path / MANIFEST_NAME).write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="integrity verification failed"):
        verify_model_files(tmp_path)


def test_model_manifest_rejects_missing_manifest(tmp_path):
    with pytest.raises(RuntimeError, match="integrity verification failed"):
        verify_model_files(tmp_path)


def test_model_loader_rejects_tampering_before_deserialization(tmp_path, monkeypatch):
    model = tmp_path / "model.json"
    metadata = tmp_path / "meta.json"
    model.write_text('{"tree": 1}', encoding="utf-8")
    metadata.write_text("{}", encoding="utf-8")
    write_model_manifest(tmp_path)
    model.write_text('{"tree": 2}', encoding="utf-8")
    loaded = False

    def load_tampered_model(*_args):
        nonlocal loaded
        loaded = True

    monkeypatch.setattr(tt.XGBRegressor, "load_model", load_tampered_model)
    with pytest.raises(RuntimeError, match="integrity verification failed"):
        tt.load_bundle(model, metadata)
    assert not loaded


def test_prediction_round_trip_fails_even_with_optimized_python_semantics():
    verify_prediction_round_trip([1.0, 2.0], [1.0, 2.0], "predictions differ")
    with pytest.raises(RuntimeError, match="predictions differ"):
        verify_prediction_round_trip([1.0], [2.0], "predictions differ")
