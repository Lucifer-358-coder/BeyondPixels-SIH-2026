"""Low-cost invariant tests for the research comparison; no CIFAKE data needed."""
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest

PATH = Path(__file__).resolve().parents[1] / 'experiments' / 'compare_cifake_paired_models.py'
spec = importlib.util.spec_from_file_location('bp_compare_script', PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def test_grouped_split_has_no_exact_duplicate_leakage():
    y = np.array([0] * 50 + [1] * 50)
    hashes = np.array([f'group-{i}' for i in range(100)])
    hashes[1] = hashes[0]
    hashes[51] = hashes[50]
    train, valid = mod.paired_split(y, hashes)
    assert not set(hashes[train]).intersection(hashes[valid])
    assert sorted(list(train) + list(valid)) == list(range(100))
    assert set(y[train]) == {0, 1} and set(y[valid]) == {0, 1}


def test_metrics_confusion_and_rates():
    m = mod.metrics(np.array([0, 0, 1, 1]), np.array([0.1, 0.8, 0.3, 0.9]))
    assert m['confusion_at_fixed_0_5'] == {
        'true_real': 1, 'false_ai_flag': 1, 'missed_ai': 1, 'true_ai': 1,
    }
    assert m['false_positive_rate_at_fixed_0_5'] == 0.5
    assert m['false_negative_rate_at_fixed_0_5'] == 0.5


def test_verification_rejects_tampered_features(tmp_path):
    (tmp_path / 'research_metadata.json').write_text('''{
        "status": "research_only_not_validated_for_documents_or_deepfakes",
        "source_split": "CIFAKE TRAIN only; no TEST image read",
        "legacy_columns": ["grid_norm", "radial_norm", "kurtosis_norm", "vanishing_norm", "shadow_norm"],
        "new_columns": ["fine_residual_energy_ratio", "medium_residual_energy_ratio", "coarse_residual_energy_ratio", "mid_band_energy_fraction", "high_band_energy_fraction"],
        "generated_file_sha256": {"train_features_5_and_10.csv":"invalid", "train_image_manifest.csv":"invalid"}
    }''')
    (tmp_path / 'train_features_5_and_10.csv').write_text('tampered')
    with pytest.raises(RuntimeError, match='SHA-256 mismatch'):
        mod.load_verified_dataset(tmp_path)
