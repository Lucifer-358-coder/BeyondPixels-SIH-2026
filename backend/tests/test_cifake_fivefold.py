"""Regression tests for research-only near-duplicate grouping and paired folds."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest
from sklearn.model_selection import StratifiedGroupKFold

EXPERIMENTS = Path(__file__).resolve().parents[1] / 'experiments'
sys.path.insert(0, str(EXPERIMENTS))
spec = importlib.util.spec_from_file_location('cv_fivefold', EXPERIMENTS / 'crossvalidate_cifake_paired_models.py')
cv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cv)


def test_perceptual_hashes_deterministic():
    import cv2
    image = np.arange(32 * 32, dtype=np.uint8).reshape(32, 32)
    ok, buffer = cv2.imencode('.png', image)
    assert ok
    first = cv.perceptual_hashes(buffer.tobytes())
    assert first == cv.perceptual_hashes(buffer.tobytes())
    assert len(first) == 2 and all(0 <= value < 2**64 for value in first)


def test_near_duplicate_grouping_includes_mixed_labels_and_exact_bytes():
    hashes = ['a' * 64, 'b' * 64, 'c' * 64, 'a' * 64, 'd' * 64]
    p = [0, 1, 255 << 16, 2**40, 2**40]
    d = [0, 1, 255 << 16, 2**40, 2**40]
    labels = np.asarray([0, 0, 1, 0, 1])
    groups, report = cv.near_duplicate_groups(hashes, p, d, labels)
    assert groups[0] == groups[1] == groups[3] == groups[4]
    assert groups[2] != groups[0]
    assert report['flagged_cross_label_pairs'] >= 1
    assert report['mixed_label_groups'] >= 1


def test_pair_audit_does_not_group_dissimilar_hashes():
    hashes = [str(i) for i in range(3)]
    groups, report = cv.near_duplicate_groups(hashes, [0, 255, 255 << 16], [0, 255, 255 << 16],
                                              np.asarray([0, 0, 1]))
    assert len(set(groups)) == 3
    assert report['flagged_pairs'] == 0


def test_grouped_folds_cover_each_row_once():
    n = 100
    y = np.asarray([i % 2 for i in range(n)])
    sha = [f'{i // 2:064x}' for i in range(n)]
    p = [i // 2 * 100000000 for i in range(n)]
    d = [i // 2 * 20000000 for i in range(n)]
    groups, _ = cv.near_duplicate_groups(sha, p, d, y)
    folds = list(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=cv.SEED).split(
        np.zeros((n, 1)), y, groups=groups))
    seen = []
    for tr, val in folds:
        assert not set(groups[tr]) & set(groups[val])
        seen.extend(val.tolist())
    assert sorted(seen) == list(range(n))


def test_calibration_is_group_disjoint_on_synthetic_data():
    # Exercises shared research fit helper without loading any CIFAKE image or model.
    rng = np.random.default_rng(42)
    X = rng.normal(size=(60, 5))
    y = np.asarray([i % 2 for i in range(60)])
    groups = np.arange(60)
    model = cv.paired.fit_research_model(X, y, groups)
    scores = model.predict_proba(X[:6])
    assert scores.shape == (6, 2) and np.isfinite(scores).all()
