"""Freeze a predeclared CIFAKE TEST study; evaluate test only after freeze.

  python experiments/frozen_cifake_evaluation.py --audit   # TRAIN only; no writes
  python experiments/frozen_cifake_evaluation.py --freeze  # TRAIN only; write immutable-by-policy plan
  python experiments/frozen_cifake_evaluation.py --evaluate # FIRST test access; one report

Research only; this partition appeared in older STAI evaluation scripts, so do not
call it a never-before-accessed or fully independent holdout. No deployment.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import time

import cv2
import numpy as np
import scipy
import sklearn
from PIL import __version__ as pillow_version
from sklearn.metrics import roc_auc_score, brier_score_loss, balanced_accuracy_score
from sklearn.model_selection import StratifiedGroupKFold

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_cifake_paired_models as paired  # noqa: E402
import crossvalidate_cifake_paired_models as fivefold  # noqa: E402
import evaluate_nested_fpr_research as nested  # noqa: E402
from stai_features import extract_stai_features  # noqa: E402
from expanded_forensics import extract_exploratory_descriptors, DESCRIPTOR_VERSION  # noqa: E402

DATASET = fivefold.DEFAULT_DATASET
PROTOCOL_DIR = BACKEND / 'data' / 'research_cifake_frozen_test_protocol_v01'
RESULT_DIR = BACKEND / 'data' / 'research_cifake_test_frozen_v01'
FIVEFOLD_DIR = BACKEND / 'data' / 'research_cifake_fivefold_v01'
NESTED_DIR = BACKEND / 'data' / 'research_cifake_nested_fpr_v01'
# A protocol or software revision requires a NEW protocol version and new decision
# on whether test data can be used again; do not overwrite v01 or tune on results.
LOCK_FILES = (
    'data/research_cifake_train_10feature_v01/research_metadata.json',
    'data/research_cifake_train_10feature_v01/train_features_5_and_10.csv',
    'data/research_cifake_train_10feature_v01/train_image_manifest.csv',
    'data/research_cifake_fivefold_v01/crossvalidation_results.json',
    'data/research_cifake_fivefold_v01/fold_assignments.csv',
    'data/research_cifake_fivefold_v01/out_of_fold_scores.csv',
    'data/research_cifake_nested_fpr_v01/nested_threshold_results.json',
    'data/research_cifake_nested_fpr_v01/nested_outer_alerts.csv',
    'experiments/compare_cifake_paired_models.py',
    'experiments/crossvalidate_cifake_paired_models.py',
    'experiments/evaluate_nested_fpr_research.py',
    'experiments/frozen_cifake_evaluation.py',
    'stai_features.py', 'expanded_forensics.py',
    'models/beyondpixels_cifake_baseline.pkl',
    'models/beyondpixels_cifake_baseline.json',
    'image_detector.py',
)
TARGET_FPR = 0.05
INNER_SEED = 20260920
EXPECTED_TEST_PER_CLASS = 10000


def checksum(path: Path) -> str:
    with path.open('rb') as stream:
        h = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def env_versions():
    return dict(python=platform.python_version(), numpy=np.__version__,
                opencv=cv2.__version__, scipy=scipy.__version__,
                sklearn=sklearn.__version__, pillow=pillow_version)


def verify_train_sources(dataset: Path = DATASET):
    X, y, hashes, metadata, groups, folds, near, compositions = fivefold.load_and_audit(paired.DATA_DIR, dataset)
    duplicates = metadata.get("identical_image_duplicate_pairs_count")
    nested.verify_existing_folds(FIVEFOLD_DIR, y, groups, folds)
    if near.get("groups") != 4997 or near.get("flagged_pairs") != 3 or near.get("mixed_label_groups"):
        raise RuntimeError("Previously audited perceptual groups changed; STOP")
    if X.shape != (5000, 10) or np.bincount(y, minlength=2).tolist() != [2500, 2500]:
        raise RuntimeError('Unexpected TRAIN dataset structure')
    if duplicates != 3 or metadata.get('historical_shadow_difference_count') != 389:
        raise RuntimeError('TRAIN extraction provenance changed; STOP')
    old_cv = json.loads((FIVEFOLD_DIR / 'crossvalidation_results.json').read_text(encoding='utf-8'))
    old_nested = json.loads((NESTED_DIR / 'nested_threshold_results.json').read_text(encoding='utf-8'))
    if old_cv.get('status') != 'experimental_fivefold_CIFAKE_TRAIN_internal_only':
        raise RuntimeError('Fivefold experiment provenance unavailable')
    if old_nested.get('status') != 'EXPLORATORY_NESTED_CIFAKE_TRAIN_STUDY_NOT_DEPLOYABLE':
        raise RuntimeError('Nested experiment provenance unavailable')
    if not old_cv.get('no_CIFAKE_TEST_access') or not old_nested.get('no_CIFAKE_TEST_access'):
        raise RuntimeError('Research experiments unexpectedly accessed TEST')
    if not old_nested.get('no_production_model_updated') or not old_nested.get('no_model_saved'):
        raise RuntimeError('Nested experiment changed production or saved model')
    for filename, field in [('fold_assignments.csv', 'fold_assignments_sha256'),
                            ('out_of_fold_scores.csv', 'out_of_fold_scores_sha256')]:
        if checksum(FIVEFOLD_DIR / filename) != old_cv.get(field):
            raise RuntimeError(f'Corrupt fivefold source: {filename}')
    if checksum(NESTED_DIR / 'nested_outer_alerts.csv') != old_nested.get('nested_outer_alerts_sha256'):
        raise RuntimeError('Corrupt nested outer alerts file')
    source = old_nested.get('source', {})
    if source.get('source_results_sha256') != checksum(FIVEFOLD_DIR / 'crossvalidation_results.json'):
        raise RuntimeError('Nested study refers to different fivefold report')
    if source.get('source_fold_assignments_sha256') != old_cv.get('fold_assignments_sha256'):
        raise RuntimeError('Nested study refers to different fold assignments')
    if source.get('source_oof_scores_sha256') != old_cv.get('out_of_fold_scores_sha256'):
        raise RuntimeError('Nested study refers to different OOF scores')
    if abs(float(old_nested.get('research_fpr_target', -1)) - TARGET_FPR) > 1e-12:
        raise RuntimeError('Nested research target differs from frozen protocol')
    recorded = metadata.get('environment', {})
    current = env_versions()
    for key in ('python', 'numpy', 'opencv', 'scipy', 'pillow'):
        if recorded.get(key) != current[key]:
            raise RuntimeError(f'Extractor environment changed: {key}: '
                               f'{recorded.get(key)} -> {current[key]}')
    if old_nested.get('sklearn') != current['sklearn']:
        raise RuntimeError('SVM environment changed since nested research')
    locked = {name: checksum(BACKEND / name) for name in LOCK_FILES}
    print('TRAIN AUDIT PASSED: paired 5000, same source data/code and nested results; '
          'no CIFAKE TEST files read.', flush=True)
    print('Historical caveat: older STAI scripts previously evaluated CIFAKE TEST; '
          'this is a separate-partition study, not a pristine holdout.', flush=True)
    return X, y, hashes, groups, locked, current


def make_plan(locked: dict, versions: dict):
    return {
        'protocol_version': 'beyondpixels-cifake-frozen-test-v01',
        'status': 'FROZEN_RESEARCH_PLAN_NO_TEST_ACCESS',
        'scientific_scope': 'AI-vs-real CIFAKE 32x32 only; not passports, forgery, identity or face deepfakes',
        'test_history': 'Earlier STAI experiments referenced and evaluated CIFAKE test. Separate from these research models but NOT pristine or never-used.',
        'training_data': 'Exactly 5000 paired CIFAKE TRAIN images; recompute 5 base features including shadow in current fixed environment; paired extra 5 already computed',
        'feature_configurations': {'five_recomputed': list(paired.BASE_COLUMNS),
                                   'ten_recomputed': list(paired.BASE_COLUMNS + paired.EXTRA_COLUMNS)},
        'model': 'StandardScaler + RBF SVC C=1 class_weight=balanced; CalibratedClassifierCV sigmoid, three StratifiedGroupKFold calibration splits seed 20260920',
        'training': 'Fit once per model on all 5000 CIFAKE TRAIN image rows; no test-based training, fitting or calibration',
        'threshold': {'target_fpr': TARGET_FPR,
                      'method': 'Per-model 3-fold grouped TRAIN-only inner OOF; most permissive score >= threshold meeting one-sided 95% Wilson upper bound for REAL false alerts <= 0.05',
                      'inner_seed': INNER_SEED,
                      'not_a_safety_requirement_or_fpr_guarantee': True},
        'test_sampling': {'split': 'test', 'labels': {'REAL': 0, 'FAKE': 1},
                          'selection': 'ALL images in both class directories, filenames sorted; no score-based exclusions',
                          'expected_per_class': EXPECTED_TEST_PER_CLASS,
                          'extensions': sorted({'.jpg', '.jpeg', '.png', '.webp'})},
        'test_integrity': 'Before scoring, abort if TEST contains any image byte-identical to the 5000 TRAIN images; heuristic perceptual overlap remains an unverified risk',
        'evaluation': ['ROC AUC', 'Brier score', '0.5 cutoff descriptive confusion and balanced accuracy',
                       'FPR and AI alert recall at frozen training-only threshold',
                       'one-sided 95% Wilson upper bound for REAL false flag rate',
                       'paired comparison on exactly the same test images'],
        'abstention': 'Score below alert threshold = UNRESOLVED, never authentic; alert = evidence for human review, never fraud proof',
        'no_test_feedback_changes': 'Do not tune features, calibration, thresholds, models or report subsets using TEST results. Subsequent attempts are exploratory and need a separately sourced dataset.',
        'deployment': 'none; existing BeyondPixels models and endpoints remain unchanged',
        'source_file_sha256': locked,
        'environment': versions,
    }


def verify_frozen_plan(plan_path: Path, actual_locked, actual_versions):
    if not plan_path.is_file():
        raise RuntimeError('No frozen plan. Run --freeze before --evaluate.')
    content = json.loads(plan_path.read_text(encoding='utf-8'))
    expected = make_plan(actual_locked, actual_versions)
    if content != expected:
        raise RuntimeError('Frozen plan does not match current data/code/environment or protocol; STOP.')
    return content


def test_paths(dataset: Path):
    # Only called after existing frozen protocol has been verified.
    extension = {'.jpg', '.jpeg', '.png', '.webp'}
    files = []
    for name, label in (('REAL', 0), ('FAKE', 1)):
        folder = dataset / 'test' / name
        if not folder.is_dir():
            raise RuntimeError(f'CIFAKE test class folder missing: {folder}')
        images = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in extension)
        if len(images) != EXPECTED_TEST_PER_CLASS:
            raise RuntimeError(f'Unexpected CIFAKE test count in {name}: {len(images)}')
        files.extend((p, label) for p in images)
        print(f'Frozen TEST inventory: {name}={len(images)}', flush=True)
    return files


def test_features(paths, train_hashes, dataset: Path):
    train_hashes = set(str(h) for h in train_hashes)
    X = np.empty((len(paths), 10), dtype=np.float64)
    y = np.empty(len(paths), dtype=np.int64)
    seen_test_hashes = set()
    repeated_test_bytes = 0
    hashes = []
    start = time.monotonic()
    for i, (path, label) in enumerate(paths):
        blob = path.read_bytes()
        digest = hashlib.sha256(blob).hexdigest()
        if digest in train_hashes:
            raise RuntimeError('STOP: CIFAKE TRAIN/TEST contain identical image bytes; no TEST results produced. '
                               f'One overlap at {path.relative_to(dataset).as_posix()}')
        if digest in seen_test_hashes:
            repeated_test_bytes += 1
        seen_test_hashes.add(digest)
        feature_vec, _ = extract_stai_features(blob)
        extra = extract_exploratory_descriptors(blob)
        if feature_vec.shape != (1, 5) or extra.get('status') != 'completed' or extra.get('version') != DESCRIPTOR_VERSION:
            raise RuntimeError('TEST extraction schema/status differs from locked TRAIN extraction')
        additional = extra.get('descriptors') or {}
        if set(additional) != set(paired.EXTRA_COLUMNS):
            raise RuntimeError('TEST descriptor names differ from frozen feature list')
        X[i, :5] = [round(float(v), 4) for v in feature_vec[0]]
        X[i, 5:] = [float(additional[key]) for key in paired.EXTRA_COLUMNS]
        y[i] = label
        hashes.append(digest)
        if (i+1) % 1000 == 0:
            print(f'Extracted frozen CIFAKE TEST features {i+1}/{len(paths)} '
                  f'({time.monotonic()-start:.1f}s)', flush=True)
    if not np.isfinite(X).all() or not np.all((X[:, :5] >= 0) & (X[:, :5] <= 1.00001)):
        raise RuntimeError('Invalid TEST feature values')
    return X, y, repeated_test_bytes, hashes


def run_experiment(X, y, groups, Xt, yt):
    inner = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=INNER_SEED)
    inner_folds = list(inner.split(X, y, groups=groups))
    report = {}
    for name, width in nested.CONFIGS:
        print(f'Frozen protocol: fitting 3 TRAIN-only OOF models for {name}...', flush=True)
        in_scores = nested.inner_oof(X, y, groups, inner_folds, width, paired.fit_research_model)
        chosen = nested.select_alert_threshold(y, in_scores, TARGET_FPR)
        print(f'Frozen protocol: fitting full 5000-TRAIN model for {name}...', flush=True)
        model = paired.fit_research_model(X[:, :width], y, groups)
        scores = model.predict_proba(Xt[:, :width])[:, list(model.classes_).index(1)]
        measured = nested.alert_metrics(yt, scores, chosen['threshold'])
        report[name] = {'training_only_threshold': chosen,
                        'test_metrics_alert_vs_unresolved': measured,
                        'test_metrics_fixed_0_5_descriptive': paired.metrics(yt, scores)}
        print(f'{name}: outer TEST FPR={measured["false_flag_rate_real"]:.3%}, '
              f'AI alert recall={measured["ai_alert_recall"]:.3%}', flush=True)
    return report


def write_report(output_dir: Path, report):
    if output_dir.exists():
        raise RuntimeError(f'Refusing to overwrite prior TEST result: {output_dir}')
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.frozen_test_incomplete_', dir=output_dir.parent) as work:
        stage = Path(work)
        (stage / 'frozen_test_results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        if output_dir.exists():
            raise RuntimeError('TEST result directory appeared before publishing; STOP')
        os.rename(stage, output_dir)
    print(f'SUCCESS: frozen CIFAKE TEST research evaluation saved: {output_dir}', flush=True)
    print('No research classifier persisted or deployed. Existing BeyondPixels production untouched.', flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument('--audit', action='store_true', help='Check TRAIN research sources only; no writes or TEST access')
    actions.add_argument('--freeze', action='store_true', help='Record fixed protocol, no TEST access or model training')
    actions.add_argument('--evaluate', action='store_true', help='One separately reported evaluation of entire TEST partition')
    parser.add_argument('--dataset', type=Path, default=DATASET, help='CIFAKE dataset root; must contain TRAIN and test')
    args = parser.parse_args(argv)
    if args.evaluate and RESULT_DIR.exists():
        raise RuntimeError(f'TEST report already exists, refusing to rerun/overwrite: {RESULT_DIR}')
    X, y, hashes, groups, locked, versions = verify_train_sources(args.dataset)
    protocol_file = PROTOCOL_DIR / 'protocol.json'
    if args.audit:
        print('AUDIT ONLY: no files written, no models fit, no CIFAKE TEST files accessed.', flush=True)
        return 0
    if args.freeze:
        if PROTOCOL_DIR.exists():
            raise RuntimeError('Protocol folder already exists; refusing to overwrite locked research plan')
        protocol = make_plan(locked, versions)
        PROTOCOL_DIR.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation, no previously frozen plan can be replaced.
        PROTOCOL_DIR.mkdir()
        with protocol_file.open('x', encoding='utf-8') as stream:
            json.dump(protocol, stream, indent=2)
            stream.write('\n')
        print(f'FROZEN: research protocol saved to {protocol_file}', flush=True)
        print(f'Protocol SHA256: {checksum(protocol_file)}', flush=True)
        print('CIFAKE TEST not accessed; models and predictions unchanged.', flush=True)
        return 0
    verify_frozen_plan(protocol_file, locked, versions)
    print(f'FROZEN PROTOCOL VERIFIED: {checksum(protocol_file)}', flush=True)
    paths = test_paths(args.dataset)
    Xt, yt, repeated, test_hashes = test_features(paths, hashes, args.dataset)
    findings = run_experiment(X, y, groups, Xt, yt)
    report = {
        'status': 'SEPARATE_PARTITION_CIFAKE_TEST_RESEARCH_NOT_DEPLOYABLE',
        'protocol_sha256': checksum(protocol_file),
        'dataset_scope': 'CIFAKE test 32x32 (previously referenced by older STAI experiments; not a pristine independent holdout)',
        'test_samples': len(yt),
        'test_label_counts': np.bincount(yt, minlength=2).tolist(),
        'test_identical_bytes_with_selected_train': 0,
        'test_repeated_exact_bytes_within_test': repeated,
        'test_manifest_sha256': hashlib.sha256('\n'.join(test_hashes).encode('ascii')).hexdigest(),
        'models': findings,
        'interpretation': 'AI alert versus unresolved only; unflagged does not establish authenticity; alert is not proof of fraud',
        'limitations': [
            'Previously used CIFAKE test partition in older STAI experiments, not a fully untouched independent benchmark',
            'Same-dataset CIFAKE 32x32 images do not establish passport, photo, forgery, face deepfake, or new-generator performance',
            'Perceptual/semantic TRAIN-TEST overlap not ruled out: only exact bytes checked',
            'Training-only Wilson FPR bound is not a guaranteed TEST FPR or safety certification',
            'Test precision uses balanced CIFAKE prevalence, not prevalence among real travel documents',
            'No model persistence, deployment, screening threshold update, or automatic identity decision',
        ],
    }
    write_report(RESULT_DIR, report)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
