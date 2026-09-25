"""Fast, synthetic-only tests: never touch CIFAKE TRAIN/TEST or live models."""
import json
import sys
from pathlib import Path
from io import BytesIO

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
import frozen_cifake_evaluation as frozen


def test_plan_locks_train_files_and_test_scope():
    plan = frozen.make_plan({'stai_features.py': '0' * 64}, {'python': 'example'})
    assert plan['status'] == 'FROZEN_RESEARCH_PLAN_NO_TEST_ACCESS'
    assert plan['test_sampling']['expected_per_class'] == 10000
    assert plan['threshold']['not_a_safety_requirement_or_fpr_guarantee'] is True
    assert len(plan['feature_configurations']['five_recomputed']) == 5
    assert len(plan['feature_configurations']['ten_recomputed']) == 10
    assert 'TEST' in plan['no_test_feedback_changes']


def test_frozen_plan_rejects_changed_inputs(tmp_path):
    path = tmp_path / 'protocol.json'
    locked, version = {'key': 'a' * 64}, {'python': 'example'}
    path.write_text(json.dumps(frozen.make_plan(locked, version)), encoding='utf-8')
    assert frozen.verify_frozen_plan(path, locked, version)['protocol_version'].endswith('v01')
    with pytest.raises(RuntimeError, match='Frozen plan'):
        frozen.verify_frozen_plan(path, {'key': 'b' * 64}, version)
    with pytest.raises(RuntimeError, match='Frozen plan'):
        frozen.verify_frozen_plan(path, locked, {'python': 'changed'})


def test_frozen_plan_required(tmp_path):
    with pytest.raises(RuntimeError, match='No frozen plan'):
        frozen.verify_frozen_plan(tmp_path / 'missing.json', {}, {})


def test_test_inventory_counts_enforced(tmp_path, monkeypatch):
    monkeypatch.setattr(frozen, 'EXPECTED_TEST_PER_CLASS', 2)
    for kind in ('REAL', 'FAKE'):
        folder = tmp_path / 'test' / kind
        folder.mkdir(parents=True)
        for i in range(2):
            (folder / f'{i}.jpg').write_bytes(b'synthetic only')
    rows = frozen.test_paths(tmp_path)
    assert len(rows) == 4
    assert [r[1] for r in rows] == [0, 0, 1, 1]
    (tmp_path / 'test' / 'FAKE' / '1.jpg').unlink()
    with pytest.raises(RuntimeError, match='Unexpected CIFAKE test count'):
        frozen.test_paths(tmp_path)


def _fake_png():
    stream = BytesIO()
    Image.fromarray(np.full((32, 32, 3), 120, dtype=np.uint8), mode='RGB').save(stream, 'PNG')
    return stream.getvalue()


def test_identical_train_test_bytes_rejected_before_model_scoring(tmp_path):
    folder = tmp_path / 'test' / 'REAL'
    folder.mkdir(parents=True)
    path = folder / 'sample.png'
    blob = _fake_png()
    path.write_bytes(blob)
    with pytest.raises(RuntimeError, match='identical image bytes'):
        frozen.test_features([(path, 0)], {frozen.hashlib.sha256(blob).hexdigest()}, tmp_path)


def test_test_extraction_same_schema_and_order(tmp_path, monkeypatch):
    folder = tmp_path / 'test' / 'FAKE'
    folder.mkdir(parents=True)
    path = folder / 'synthetic.png'
    path.write_bytes(_fake_png())
    monkeypatch.setattr(frozen, 'extract_stai_features', lambda blob: (np.array([[.1, .2, .3, .4, .5]]), {}))
    monkeypatch.setattr(frozen, 'extract_exploratory_descriptors', lambda blob: {
        'status': 'completed', 'version': frozen.DESCRIPTOR_VERSION,
        'descriptors': dict.fromkeys(frozen.paired.EXTRA_COLUMNS, .6),
    })
    features, labels, repeats, image_hashes = frozen.test_features([(path, 1)], set(), tmp_path)
    assert features.shape == (1, 10)
    assert features[0].tolist() == pytest.approx([.1, .2, .3, .4, .5] + [.6] * 5)
    assert labels.tolist() == [1] and repeats == 0 and len(image_hashes) == 1


def test_test_extraction_fails_closed_on_missing_descriptor(tmp_path, monkeypatch):
    folder = tmp_path / 'test' / 'FAKE'
    folder.mkdir(parents=True)
    path = folder / 'synthetic.png'
    path.write_bytes(_fake_png())
    monkeypatch.setattr(frozen, 'extract_stai_features', lambda blob: (np.zeros((1, 5)), {}))
    monkeypatch.setattr(frozen, 'extract_exploratory_descriptors', lambda blob: {
        'status': 'unavailable', 'descriptors': {}, 'version': frozen.DESCRIPTOR_VERSION,
    })
    with pytest.raises(RuntimeError, match='TEST extraction schema'):
        frozen.test_features([(path, 1)], set(), tmp_path)


def test_test_report_never_overwrites(tmp_path):
    output = tmp_path / 'report'
    frozen.write_report(output, {'status': 'SYNTHETIC_TEST_ONLY'})
    assert json.loads((output / 'frozen_test_results.json').read_text())['status'] == 'SYNTHETIC_TEST_ONLY'
    with pytest.raises(RuntimeError, match='Refusing to overwrite'):
        frozen.write_report(output, {})


def test_audit_and_freeze_do_not_touch_test_images(monkeypatch, tmp_path):
    monkeypatch.setattr(frozen, 'PROTOCOL_DIR', tmp_path / 'locked')
    monkeypatch.setattr(frozen, 'RESULT_DIR', tmp_path / 'results')
    stub = (np.empty((1, 10)), np.array([0]), np.array(['fake-hash']),
            np.array([0]), {'training-data': '0' * 64}, {'python': 'example'})
    monkeypatch.setattr(frozen, 'verify_train_sources', lambda dataset: stub)
    monkeypatch.setattr(frozen, 'test_paths', lambda dataset: pytest.fail('TEST accessed before freeze'))
    assert frozen.main(['--audit']) == 0
    assert not frozen.PROTOCOL_DIR.exists()
    assert frozen.main(['--freeze']) == 0
    assert frozen.verify_frozen_plan(frozen.PROTOCOL_DIR / 'protocol.json', stub[4], stub[5])
    with pytest.raises(RuntimeError, match='refusing to overwrite'):
        frozen.main(['--freeze'])


def test_evaluate_fails_closed_if_no_frozen_protocol(monkeypatch, tmp_path):
    monkeypatch.setattr(frozen, 'PROTOCOL_DIR', tmp_path / 'missing')
    monkeypatch.setattr(frozen, 'RESULT_DIR', tmp_path / 'results')
    stub = (np.empty((1, 10)), np.array([0]), np.array(['fake-hash']),
            np.array([0]), {'training-data': '0' * 64}, {'python': 'example'})
    monkeypatch.setattr(frozen, 'verify_train_sources', lambda dataset: stub)
    monkeypatch.setattr(frozen, 'test_paths', lambda dataset: pytest.fail('TEST accessed without frozen protocol'))
    with pytest.raises(RuntimeError, match='No frozen plan'):
        frozen.main(['--evaluate'])
