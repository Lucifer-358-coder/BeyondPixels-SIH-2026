"""Research-only paired 5-versus-10 feature CIFAKE TRAIN comparison.

Reads ONLY the previously built paired CSV, manifest, metadata, and extractor code
hashes. Never reads CIFAKE TEST, overwrites a trained model, or changes API results.

    python experiments/compare_cifake_paired_models.py --audit
    python experiments/compare_cifake_paired_models.py --compare
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import tempfile

import numpy as np
import sklearn
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

BACKEND = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND / 'data' / 'research_cifake_train_10feature_v01'
OUTPUT_DIR = BACKEND / 'data' / 'research_cifake_paired_comparison_v01'
FEATURE_FILE = 'train_features_5_and_10.csv'
MANIFEST_FILE = 'train_image_manifest.csv'
BASE_COLUMNS = ('grid_norm', 'radial_norm', 'kurtosis_norm', 'vanishing_norm', 'shadow_norm')
EXTRA_COLUMNS = (
    'fine_residual_energy_ratio', 'medium_residual_energy_ratio',
    'coarse_residual_energy_ratio', 'mid_band_energy_fraction',
    'high_band_energy_fraction',
)
SEED = 20260919


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path, expected_columns: list[str]) -> list[dict[str, str]]:
    with path.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != expected_columns:
            raise RuntimeError(f'Unexpected columns in {path.name}: {reader.fieldnames}')
        return list(reader)


def load_verified_dataset(data_dir: Path, backend: Path = BACKEND):
    """Verify entire paired dataset without opening or reading source/test images."""
    meta_path = data_dir / 'research_metadata.json'
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    if meta.get('status') != 'research_only_not_validated_for_documents_or_deepfakes':
        raise RuntimeError('Unexpected research dataset status')
    if meta.get('source_split') != 'CIFAKE TRAIN only; no TEST image read':
        raise RuntimeError('Source partition is not verified TRAIN-only')
    expected_names = {'legacy_columns': list(BASE_COLUMNS), 'new_columns': list(EXTRA_COLUMNS)}
    for key, expected in expected_names.items():
        if meta.get(key) != expected:
            raise RuntimeError(f'Feature order changed: {key}')
    for name in (FEATURE_FILE, MANIFEST_FILE):
        expected_sha = meta.get('generated_file_sha256', {}).get(name)
        if not expected_sha or digest(data_dir / name) != expected_sha:
            raise RuntimeError(f'File SHA-256 mismatch: {name}')
    for name in ('stai_features.py', 'expanded_forensics.py'):
        expected_sha = meta.get('code_sha256', {}).get(name)
        if not expected_sha or digest(backend / name) != expected_sha:
            raise RuntimeError(f'Extractor implementation has changed since data build: {name}')
    features = read_csv(data_dir / FEATURE_FILE,
                        ['csv_row', 'label', *BASE_COLUMNS, *EXTRA_COLUMNS])
    manifest = read_csv(data_dir / MANIFEST_FILE,
                        ['csv_row', 'split', 'label', 'relative_path', 'sha256'])
    if len(features) != 5000 or len(manifest) != 5000 or meta.get('samples') != 5000:
        raise RuntimeError('Dataset does not contain exactly 5000 paired rows')
    X = np.empty((5000, 10), dtype=np.float64)
    y = np.empty(5000, dtype=np.int64)
    hashes = []
    paths = set()
    hash_labels = {}
    duplicate_count = 0
    for i, (feature, entry) in enumerate(zip(features, manifest)):
        row_id = str(i + 1)
        if feature['csv_row'] != row_id or entry['csv_row'] != row_id:
            raise RuntimeError(f'Misaligned CSV and manifest rows at {row_id}')
        if feature['label'] != entry['label'] or feature['label'] not in ('0', '1'):
            raise RuntimeError(f'Label disagreement at {row_id}')
        label = int(feature['label'])
        expected_prefix = 'TRAIN/REAL/' if label == 0 else 'TRAIN/FAKE/'
        path = entry['relative_path']
        if entry['split'] != 'TRAIN' or not path.startswith(expected_prefix) or path in paths:
            raise RuntimeError(f'Unexpected split, source path, or duplicate path at row {row_id}')
        paths.add(path)
        hexdigest = entry['sha256']
        if len(hexdigest) != 64 or any(c not in '0123456789abcdef' for c in hexdigest):
            raise RuntimeError(f'Invalid image SHA-256 at row {row_id}')
        if hexdigest in hash_labels:
            duplicate_count += 1
            if hash_labels[hexdigest] != label:
                raise RuntimeError(f'Conflicting labels for identical image bytes at row {row_id}')
        hash_labels[hexdigest] = label
        hashes.append(hexdigest)
        y[i] = label
        X[i] = [float(feature[k]) for k in (*BASE_COLUMNS, *EXTRA_COLUMNS)]
    if np.bincount(y, minlength=2).tolist() != [2500, 2500]:
        raise RuntimeError('Unexpected REAL/FAKE class counts')
    if not np.isfinite(X).all() or (X < 0).any() or (X[:, :5] > 1.00001).any():
        raise RuntimeError('Nonfinite or out-of-range feature measurements')
    if duplicate_count != meta.get('identical_image_duplicate_pairs_count'):
        raise RuntimeError('Image-hash duplicate count differs from metadata')
    return X, y, np.asarray(hashes), meta, duplicate_count


def paired_split(y: np.ndarray, hashes: np.ndarray):
    outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    train, valid = next(outer.split(np.zeros((len(y), 1)), y, groups=hashes))
    if set(hashes[train]) & set(hashes[valid]):
        raise RuntimeError('Identical-image hash leaked across TRAIN and validation')
    if min(np.bincount(y[train], minlength=2)) == 0 or min(np.bincount(y[valid], minlength=2)) == 0:
        raise RuntimeError('Missing class in training or validation')
    return train, valid


def fit_research_model(X_train, y_train, training_hashes):
    # Group-disjoint folds are used for BOTH fitting and sigmoid calibration.
    inner = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=SEED + 1)
    cv_splits = list(inner.split(X_train, y_train, groups=training_hashes))
    for subtrain, subval in cv_splits:
        if set(training_hashes[subtrain]) & set(training_hashes[subval]):
            raise RuntimeError('Identical-image hash leaked into calibration fold')
    base = Pipeline([
        ('scaler', StandardScaler()),
        ('svm', SVC(kernel='rbf', C=1.0, class_weight='balanced')),
    ])
    clf = CalibratedClassifierCV(estimator=base, method='sigmoid', cv=cv_splits)
    clf.fit(X_train, y_train)
    return clf


def metrics(y_actual, scores):
    # 0.5 is a fixed descriptive cutoff; NOT a selected deployment threshold.
    predicted = (scores >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_actual, predicted, labels=[0, 1]).ravel()
    return {
        'validation_samples': int(len(y_actual)),
        'roc_auc': float(roc_auc_score(y_actual, scores)),
        'brier_score': float(brier_score_loss(y_actual, scores)),
        'balanced_accuracy_at_fixed_0_5': float(balanced_accuracy_score(y_actual, predicted)),
        'confusion_at_fixed_0_5': {'true_real': int(tn), 'false_ai_flag': int(fp),
                                   'missed_ai': int(fn), 'true_ai': int(tp)},
        'false_positive_rate_at_fixed_0_5': float(fp / (tn + fp)),
        'false_negative_rate_at_fixed_0_5': float(fn / (tp + fn)),
    }


def compare(X, y, hashes, meta, duplicates, train, valid):
    scores = {}
    for name, n_features in (('five_recomputed', 5), ('ten_recomputed', 10)):
        print(f'Fitting {name} research classifier on {len(train)} TRAIN images...', flush=True)
        clf = fit_research_model(X[train, :n_features], y[train], hashes[train])
        probabilities = clf.predict_proba(X[valid, :n_features])[:, list(clf.classes_).index(1)]
        scores[name] = metrics(y[valid], probabilities)
        print(f'{name}: AUC={scores[name]["roc_auc"]:.4f}; '
              f'Brier={scores[name]["brier_score"]:.4f}; '
              f'balanced accuracy at 0.5={scores[name]["balanced_accuracy_at_fixed_0_5"]:.4f}',
              flush=True)
    results = {
        'status': 'experimental_internal_CIFAKE_TRAIN_validation_only',
        'no_production_model_updated': True,
        'no_CIFAKE_TEST_access': True,
        'dataset_metadata_sha256': digest(DATA_DIR / 'research_metadata.json'),
        'dataset_file_sha256': meta['generated_file_sha256'],
        'seed': SEED, 'scikit_learn': sklearn.__version__, 'python': platform.python_version(),
        'train_count': int(len(train)), 'validation_count': int(len(valid)),
        'train_labels': np.bincount(y[train], minlength=2).tolist(),
        'validation_labels': np.bincount(y[valid], minlength=2).tolist(),
        'identical_image_duplicate_pairs': duplicates,
        'split': 'first StratifiedGroupKFold 5-fold split, image SHA-256 groups, seed 20260919',
        'calibration': '3 StratifiedGroupKFold folds on training only; same folds, C=1 RBF SVC and StandardScaler for both',
        'models': scores,
        'limitations': [
            'Internal validation only from CIFAKE TRAIN (32x32 source domain); no document or deepfake evaluation',
            'Image SHA-256 grouping does not detect near-duplicates or source leakage',
            'Single split and same-dataset evaluation; observed metric difference is not proof of generalization',
            'Fixed 0.5 classification cutoff is descriptive, not a validated screening threshold',
            'No production deployment, model persistence, or CIFAKE TEST access',
        ],
    }
    return results


def publish(output_dir: Path, result: dict, hashes: np.ndarray, y: np.ndarray, train, valid):
    if output_dir.exists():
        raise RuntimeError(f'Refusing to overwrite research comparison folder: {output_dir}')
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.comparison_incomplete_', dir=output_dir.parent) as work:
        stage = Path(work)
        with (stage / 'locked_split_manifest.csv').open('w', newline='', encoding='utf-8') as handle:
            writer = csv.writer(handle)
            writer.writerow(('csv_row', 'split', 'label', 'sha256'))
            role = {int(i): 'train' for i in train}
            role.update({int(i): 'validation' for i in valid})
            if len(role) != len(y):
                raise RuntimeError('Not every dataset row received a split')
            for i in range(len(y)):
                writer.writerow((i + 1, role[i], int(y[i]), hashes[i]))
        result['locked_split_manifest_sha256'] = digest(stage / 'locked_split_manifest.csv')
        (stage / 'comparison_results.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        os.rename(stage, output_dir)
    print(f'SUCCESS: research-only comparison saved in {output_dir}', flush=True)
    print('No model saved; existing BeyondPixels predictions and CIFAKE TEST unchanged.', flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--audit', action='store_true', help='Verify dataset and grouped split; train nothing and write nothing')
    mode.add_argument('--compare', action='store_true', help='Run fair paired research comparison and save JSON + split manifest')
    parser.add_argument('--data-dir', type=Path, default=DATA_DIR)
    parser.add_argument('--output-dir', type=Path, default=OUTPUT_DIR)
    args = parser.parse_args(argv)
    X, y, hashes, meta, duplicates = load_verified_dataset(args.data_dir)
    train, valid = paired_split(y, hashes)
    print(f'AUDIT PASSED: {len(y)} paired CIFAKE TRAIN rows; 5 original + 5 new features;', flush=True)
    print(f'classes={np.bincount(y).tolist()}; exact duplicate pairs={duplicates}; '
          f'train={len(train)}; validation={len(valid)}', flush=True)
    print('No identical image bytes shared across train/validation; CIFAKE TEST not accessed.', flush=True)
    if args.compare:
        if args.output_dir.exists():
            raise RuntimeError(f'Output exists: {args.output_dir}; refusing to overwrite')
        result = compare(X, y, hashes, meta, duplicates, train, valid)
        publish(args.output_dir, result, hashes, y, train, valid)
    else:
        print('AUDIT ONLY: no classifier trained; no files written.', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
