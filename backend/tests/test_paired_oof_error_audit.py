"""Fast, standard-library-only regression tests for the read-only OOF audit."""
import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / 'experiments' / 'audit_paired_oof_errors.py'
spec = importlib.util.spec_from_file_location('audit_paired_oof_errors', SOURCE)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def make_sample(folder, *, cross_fold_group=False, corrupt_score=False):
    folder.mkdir()
    scores = folder / 'out_of_fold_scores.csv'
    assignments = folder / 'fold_assignments.csv'
    # 500 class 0 and 500 class 1 on each of five folds.
    with scores.open('w', newline='') as s, assignments.open('w', newline='') as a:
        sw, aw = csv.writer(s), csv.writer(a)
        sw.writerow(module.REQUIRED_SCORE_COLUMNS)
        aw.writerow(module.REQUIRED_FOLD_COLUMNS)
        for fold in range(1, 6):
            for label in (0, 1):
                for j in range(500):
                    row_id = (fold - 1) * 1000 + label * 500 + j + 1
                    p5, p10 = ((.7, .3) if label == 0 and j == 0 else
                               (.3, .7) if label == 1 and j == 0 else
                               (.2, .1) if label == 0 else (.8, .9))
                    sw.writerow((row_id, label, fold, p5, p10))
                    aw.writerow((row_id, label, fold,
                                 1 if cross_fold_group and row_id in (1, 1001) else row_id + 10000))
    report = {
        'status': 'experimental_fivefold_CIFAKE_TRAIN_internal_only',
        'no_production_model_updated': True,
        'no_CIFAKE_TEST_access': True,
        'no_classifier_saved': True,
        'out_of_fold_scores_sha256': module.digest(scores),
        'fold_assignments_sha256': module.digest(assignments),
        'near_duplicate_audit': {'groups': 4999 if cross_fold_group else 5000},
        'aggregated_metrics': {
            'five_recomputed': {'pooled_out_of_fold': {'confusion_at_fixed_0_5': {
                'false_ai_flag': 5, 'missed_ai': 5}}},
            'ten_recomputed': {'pooled_out_of_fold': {'confusion_at_fixed_0_5': {
                'false_ai_flag': 0, 'missed_ai': 0}}},
        },
    }
    (folder / 'crossvalidation_results.json').write_text(json.dumps(report))
    if corrupt_score:
        scores.write_text(scores.read_text() + '\n')
    return folder


def test_paired_transitions(tmp_path):
    result = module.audit(make_sample(tmp_path / 'research'))
    assert result['status'] == 'READ_ONLY_AUDIT_PASSED'
    assert result['real_image_transitions']['ten_only_correct'] == 5
    assert result['ai_image_transitions']['ten_only_correct'] == 5
    assert result['false_ai_flags']['five_recomputed'] == 5
    assert result['missed_ai_images']['ten_recomputed'] == 0
    assert result['no_files_written'] is True


def test_checksum_tampering_rejected(tmp_path):
    folder = make_sample(tmp_path / 'research', corrupt_score=True)
    with pytest.raises(ValueError, match='SHA-256 mismatch'):
        module.audit(folder)


def test_group_leakage_rejected(tmp_path):
    folder = make_sample(tmp_path / 'research', cross_fold_group=True)
    with pytest.raises(ValueError, match='crosses validation folds'):
        module.audit(folder)


def test_digest_is_sha256(tmp_path):
    p = tmp_path / 'f'
    p.write_bytes(b'test')
    assert module.digest(p) == hashlib.sha256(b'test').hexdigest()
