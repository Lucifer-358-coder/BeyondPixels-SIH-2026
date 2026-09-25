"""Synthetic-only v02 tests; never read CIFAKE TRAIN/TEST."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
import revised_cifake_overlap_evaluation as v02


def _fixture(tmp_path):
    # Three REAL, three FAKE. One duplicated REAL pair and one FAKE TRAIN overlap.
    root = tmp_path / 'dataset'
    inputs = [('REAL', b'A'), ('REAL', b'A'), ('REAL', b'B'),
              ('FAKE', b'C'), ('FAKE', b'D'), ('FAKE', b'E')]
    paths = []
    for idx, (name, blob) in enumerate(inputs):
        folder = root / 'test' / name
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f'{idx}.jpg'
        path.write_bytes(blob)
        paths.append((path, 0 if name == 'REAL' else 1))
    return root, paths, hashlib.sha256(b'C').hexdigest()


def test_plan_declares_revision_and_preserves_v01():
    plan = v02.make_plan('a'*64, {'prior': 'b'*64}, {'python': 'synthetic'})
    assert plan['protocol_version'].endswith('v02')
    assert plan['expected_train_test_exact_overlap_by_class'] == {'REAL': 0, 'FAKE': 20}
    assert plan['expected_within_test_additional_duplicate_images'] == 38
    assert 'unresolved' in plan['interpretation'].lower()
    assert 'v01' in plan['supersedes_for_analysis_only']


def test_revision_freeze_rejects_source_mutation(tmp_path):
    plan = v02.make_plan('a'*64, {'prior': 'b'*64}, {'python': 'synthetic'})
    file = tmp_path / 'protocol.json'
    file.write_text(json.dumps(plan))
    assert len(v02.verify_revision(file, plan)) == 64
    with pytest.raises(RuntimeError, match='changed'):
        v02.verify_revision(file, {**plan, 'original_protocol_sha256':'c'*64})
    with pytest.raises(RuntimeError, match='missing'):
        v02.verify_revision(tmp_path / 'missing.json', plan)


def test_inventory_excludes_train_overlap_and_deduplicates_only_in_sensitivity(tmp_path, monkeypatch):
    root, paths, train_hash = _fixture(tmp_path)
    monkeypatch.setattr(v02.frozen, 'EXPECTED_TEST_PER_CLASS', 3)
    monkeypatch.setattr(v02, 'EXPECTED_OVERLAP', {'REAL': 0, 'FAKE': 1})
    monkeypatch.setattr(v02, 'EXPECTED_TEST_DUPLICATE_PAIRS', 1)
    retained, hashes, unique_idx, excluded, audit = v02.inventory_test(paths, {train_hash: 1}, root)
    assert len(retained) == 5 and len(hashes) == 5 and len(unique_idx) == 4
    assert len(excluded) == 1 and excluded[0]['label'] == 1
    assert audit['retained_real'] == 3 and audit['retained_fake'] == 2
    assert audit['within_test_extra_repeated_files'] == 1
    assert hashes[unique_idx[0]] == hashes[0]
    assert len(set(hashes[i] for i in unique_idx)) == 4


def test_inventory_fails_on_unexpected_overlap_count(tmp_path, monkeypatch):
    root, paths, train_hash = _fixture(tmp_path)
    monkeypatch.setattr(v02.frozen, 'EXPECTED_TEST_PER_CLASS', 3)
    monkeypatch.setattr(v02, 'EXPECTED_OVERLAP', {'REAL': 0, 'FAKE': 0})
    monkeypatch.setattr(v02, 'EXPECTED_TEST_DUPLICATE_PAIRS', 1)
    with pytest.raises(RuntimeError, match='differs'):
        v02.inventory_test(paths, {train_hash: 1}, root)


def test_inventory_fails_on_cross_label_overlap(tmp_path, monkeypatch):
    root, paths, train_hash = _fixture(tmp_path)
    monkeypatch.setattr(v02.frozen, 'EXPECTED_TEST_PER_CLASS', 3)
    with pytest.raises(RuntimeError, match='Cross-label'):
        v02.inventory_test(paths, {train_hash: 0}, root)


def test_inventory_fails_on_cross_label_duplicate(tmp_path, monkeypatch):
    root, paths, train_hash = _fixture(tmp_path)
    paths[-1][0].write_bytes(b'A')
    monkeypatch.setattr(v02.frozen, 'EXPECTED_TEST_PER_CLASS', 3)
    with pytest.raises(RuntimeError, match='differs'):
        v02.inventory_test(paths, {train_hash: 1}, root)


def test_result_write_and_no_overwrite(tmp_path):
    root, paths, train_hash = _fixture(tmp_path)
    output = tmp_path / 'out'
    labels = [('REAL', 0), ('FAKE', 1)]
    retained = [(paths[0][0], 0), (paths[3][0], 1)]
    hashes = [v02.frozen.checksum(p) for p, _ in retained]
    scores = {'five_recomputed': np.array([0.1, 0.8]),
              'ten_recomputed': np.array([0.2, 0.9])}
    v02.write_results(output, {'status': 'synthetic'}, [], retained, hashes, scores, root)
    assert json.loads((output / 'revised_test_results.json').read_text())['status'] == 'synthetic'
    assert len((output / 'paired_test_scores.csv').read_text().splitlines()) == 3
    with pytest.raises(RuntimeError, match='overwrite'):
        v02.write_results(output, {}, [], retained, hashes, scores, root)


def test_audit_freeze_never_reads_test(tmp_path, monkeypatch):
    monkeypatch.setattr(v02, 'PROTOCOL_DIR', tmp_path / 'protocol')
    monkeypatch.setattr(v02, 'RESULT_DIR', tmp_path / 'results')
    monkeypatch.setattr(v02.frozen, 'verify_train_sources', lambda path: (
        np.empty((2, 10)), np.array([0, 1]), np.array(['a', 'b']),
        np.array([0, 1]), {'stai_features.py': '0'*64}, {'python': 'synthetic'}))
    monkeypatch.setattr(v02, 'verify_original', lambda locked, versions: '1'*64)
    monkeypatch.setattr(v02.frozen, 'test_paths', lambda path: pytest.fail('TEST accessed during freeze'))
    assert v02.main(['--audit']) == 0
    assert not v02.PROTOCOL_DIR.exists()
    assert v02.main(['--freeze']) == 0
    with pytest.raises(RuntimeError, match='already exists'):
        v02.main(['--freeze'])
    assert v02.RESULT_DIR.exists() is False
