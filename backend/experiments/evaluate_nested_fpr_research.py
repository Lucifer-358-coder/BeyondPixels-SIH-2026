"""Research-only paired nested threshold evaluation on CIFAKE TRAIN.

python experiments/evaluate_nested_fpr_research.py --audit
python experiments/evaluate_nested_fpr_research.py --evaluate

Predeclared exploratory rule: choose the most permissive alert threshold whose
one-sided 95% Wilson upper bound on training-only inner-OOF REAL false-flag
rate is <= 0.05. Score >= threshold means experimental AI alert; all other
images remain UNFLAGGED/UNRESOLVED, not "authentic". The existing outer folds
were examined previously, hence this is NOT a new untouched holdout test.
No CIFAKE TEST access, model files, app changes, or threshold deployment.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import tempfile

import numpy as np
from sklearn.model_selection import StratifiedGroupKFold
import sklearn

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_cifake_paired_models as paired
import crossvalidate_cifake_paired_models as fivefold

SOURCE_RESULTS = paired.BACKEND / 'data' / 'research_cifake_fivefold_v01'
OUTPUT_DIR = paired.BACKEND / 'data' / 'research_cifake_nested_fpr_v01'
TARGET_FPR = 0.05  # predeclared research example; NOT an operational risk policy
Z_ONE_SIDED_95 = 1.6448536269514722
INNER_SPLIT_SEED = 20260920
CONFIGS = (('five_recomputed', 5), ('ten_recomputed', 10))


def wilson_upper(positives: int, total: int, z: float = Z_ONE_SIDED_95) -> float:
    """One-sided Wilson binomial upper bound (descriptive, iid assumption)."""
    if not (0 <= positives <= total) or total < 1:
        raise ValueError('Invalid successes or sample size')
    if not (math.isfinite(z) and z > 0):
        raise ValueError('z must be finite and positive')
    p = positives / total
    z2 = z * z
    return min(1.0, (p + z2 / (2 * total) + z * math.sqrt(
        p * (1 - p) / total + z2 / (4 * total * total))) / (1 + z2 / total))


def select_alert_threshold(training_labels, inner_oof_scores, max_fpr=TARGET_FPR):
    """Use training-only inner OOF real scores; never inspect outer labels/scores.

    Threshold is immediately above the largest REAL score that must be
    excluded to satisfy the Wilson bound. Ties are excluded together.
    """
    y = np.asarray(training_labels, dtype=int)
    scores = np.asarray(inner_oof_scores, dtype=float)
    if y.shape != scores.shape or y.ndim != 1 or not np.isfinite(scores).all():
        raise ValueError('Invalid paired training labels and scores')
    if np.any((scores < 0) | (scores > 1)) or not np.isin(y, (0, 1)).all():
        raise ValueError('Scores or labels outside expected range')
    if not (0 < max_fpr < 1):
        raise ValueError('max_fpr must be between zero and one')
    real = np.sort(scores[y == 0])
    if len(real) == 0 or not np.any(y == 1):
        raise ValueError('Both classes required')
    n_real = len(real)
    allowed = max(k for k in range(n_real + 1)
                  if wilson_upper(k, n_real) <= max_fpr)
    # If k < n, excluding the (k+1)th largest real score guarantees <=k
    # inner REAL alerts even when floating-point scores are tied.
    threshold = (float(np.nextafter(real[n_real - allowed - 1], np.inf))
                 if allowed < n_real else 0.0)
    if threshold > 1.0:
        threshold = float(np.nextafter(1.0, np.inf))
    flagged_real = int(np.sum(real >= threshold))
    if flagged_real > allowed or wilson_upper(flagged_real, n_real) > max_fpr + 1e-12:
        raise RuntimeError('Threshold selection violates inner training-only FPR target')
    inner_ai = scores[y == 1]
    return {
        'threshold': threshold,
        'inner_real_count': n_real,
        'inner_ai_count': int(len(inner_ai)),
        'inner_real_flagged': flagged_real,
        'inner_real_fpr': flagged_real / n_real,
        'inner_real_fpr_wilson_upper_one_sided_95': wilson_upper(flagged_real, n_real),
        'inner_ai_flagged': int(np.sum(inner_ai >= threshold)),
        'inner_ai_recall': float(np.mean(inner_ai >= threshold)),
        'max_allowed_real_flags_by_wilson_rule': allowed,
    }


def alert_metrics(labels, scores, threshold):
    y = np.asarray(labels, dtype=int)
    s = np.asarray(scores, dtype=float)
    if y.shape != s.shape or y.ndim != 1 or not np.isfinite(s).all():
        raise ValueError('Invalid outer validation arrays')
    alerts = s >= threshold
    nr, na = int(np.sum(y == 0)), int(np.sum(y == 1))
    if nr == 0 or na == 0:
        raise ValueError('Both labels required in outer validation')
    fp = int(np.sum(alerts & (y == 0)))
    tp = int(np.sum(alerts & (y == 1)))
    return {
        'real_count': nr, 'ai_count': na, 'real_flagged': fp,
        'real_unflagged_unresolved': nr - fp,
        'ai_flagged': tp, 'ai_unflagged_unresolved': na - tp,
        'false_flag_rate_real': fp / nr,
        'ai_alert_recall': tp / na,
        'ai_not_flagged_rate': (na - tp) / na,
        'alert_precision_at_balanced_CIFAKE_prevalence': tp / (tp + fp) if tp + fp else None,
        'alert_coverage_all_images': (tp + fp) / len(y),
        'real_false_flag_wilson_upper_one_sided_95': wilson_upper(fp, nr),
    }


def verify_existing_folds(result_dir: Path, labels: np.ndarray, groups: np.ndarray, folds):
    """Verify previously published fold assignment and result hashes; OOF scores
    are only hashed, never loaded or used for threshold selection.
    """
    report_file = result_dir / 'crossvalidation_results.json'
    report = json.loads(report_file.read_text(encoding='utf-8'))
    if report.get('status') != 'experimental_fivefold_CIFAKE_TRAIN_internal_only' or not report.get('no_CIFAKE_TEST_access'):
        raise RuntimeError('Existing fivefold report missing expected research-only metadata')
    names = {'fold_assignments.csv': 'fold_assignments_sha256',
             'out_of_fold_scores.csv': 'out_of_fold_scores_sha256'}
    for name, field in names.items():
        if paired.digest(result_dir / name) != report.get(field):
            raise RuntimeError(f'Existing fivefold file checksum differs: {name}')
    rows = paired.read_csv(result_dir / 'fold_assignments.csv',
                           ['csv_row', 'label', 'validation_fold', 'near_group_id'])
    if len(rows) != len(labels):
        raise RuntimeError('Different fold assignment row count')
    assigned = np.zeros(len(labels), dtype=int)
    for fold_id, (_, valid) in enumerate(folds, 1):
        assigned[valid] = fold_id
    for i, row in enumerate(rows):
        if (int(row['csv_row']) != i + 1 or int(row['label']) != int(labels[i])
                or int(row['validation_fold']) != assigned[i]
                or int(row['near_group_id']) != int(groups[i])):
            raise RuntimeError(f'Saved fold assignment differs at row {i + 1}')
    return {'source_results_sha256': paired.digest(report_file),
            'source_fold_assignments_sha256': report['fold_assignments_sha256'],
            'source_oof_scores_sha256': report['out_of_fold_scores_sha256']}


def inner_oof(X_train, y_train, groups_train, folds_inner, n_features, fit_model):
    """Generate score for every OUTER TRAIN row from models trained without it."""
    scores = np.full(len(y_train), np.nan, dtype=float)
    visited = np.zeros(len(y_train), dtype=int)
    for subtrain, subval in folds_inner:
        if set(groups_train[subtrain]) & set(groups_train[subval]):
            raise RuntimeError('Group leakage between inner train and threshold holdout')
        model = fit_model(X_train[subtrain, :n_features], y_train[subtrain], groups_train[subtrain])
        class_one_index = list(model.classes_).index(1)
        scores[subval] = model.predict_proba(X_train[subval, :n_features])[:, class_one_index]
        visited[subval] += 1
    if not np.all(visited == 1) or not np.isfinite(scores).all():
        raise RuntimeError('Inner OOF scores missing or repeatedly assigned')
    return scores


def run_nested(X, y, groups, folds, fit_model=paired.fit_research_model):
    all_results = []
    outer_prediction_rows = []
    for fold_id, (train, valid) in enumerate(folds, 1):
        if set(groups[train]) & set(groups[valid]):
            raise RuntimeError('Group leakage between outer training and validation')
        inner_splitter = StratifiedGroupKFold(n_splits=3, shuffle=True,
                                             random_state=INNER_SPLIT_SEED)
        inner_folds = list(inner_splitter.split(X[train], y[train], groups[train]))
        fold_result = {'fold': fold_id, 'outer_train': len(train),
                       'outer_validation': len(valid), 'models': {}}
        score_by_name = {}
        flags_by_name = {}
        for name, cols in CONFIGS:
            print(f'Fold {fold_id}/5: {name}, 3 inner OOF fits + 1 outer fit...', flush=True)
            training_scores = inner_oof(X[train], y[train], groups[train],
                                        inner_folds, cols, fit_model)
            selected = select_alert_threshold(y[train], training_scores)
            # Outer validation was never used in threshold selection or model fitting.
            model = fit_model(X[train, :cols], y[train], groups[train])
            outer_scores = model.predict_proba(X[valid, :cols])[:, list(model.classes_).index(1)]
            measured = alert_metrics(y[valid], outer_scores, selected['threshold'])
            fold_result['models'][name] = {'training_only_threshold': selected,
                                          'outer_validation': measured}
            score_by_name[name] = outer_scores
            flags_by_name[name] = outer_scores >= selected['threshold']
            print(f'  inner threshold={selected["threshold"]:.6g}; outer REAL false-flag rate='
                  f'{measured["false_flag_rate_real"]:.3%}; AI alert recall='
                  f'{measured["ai_alert_recall"]:.3%}', flush=True)
        for pos, idx in enumerate(valid):
            outer_prediction_rows.append((int(idx) + 1, int(y[idx]), fold_id,
                                          *[float(score_by_name[k][pos]) for k, _ in CONFIGS],
                                          *[int(flags_by_name[k][pos]) for k, _ in CONFIGS]))
        all_results.append(fold_result)
    if len(outer_prediction_rows) != len(y) or len({r[0] for r in outer_prediction_rows}) != len(y):
        raise RuntimeError('Outer prediction rows are missing or duplicated')
    pooled = {}
    for pos, (name, _) in enumerate(CONFIGS):
        fp = sum(r['models'][name]['outer_validation']['real_flagged'] for r in all_results)
        tp = sum(r['models'][name]['outer_validation']['ai_flagged'] for r in all_results)
        nr = sum(r['models'][name]['outer_validation']['real_count'] for r in all_results)
        na = sum(r['models'][name]['outer_validation']['ai_count'] for r in all_results)
        pooled[name] = {
            'real_count': nr, 'ai_count': na, 'real_flagged': fp,
            'ai_flagged': tp, 'ai_not_flagged_unresolved': na - tp,
            'pooled_real_false_flag_rate': fp / nr,
            'pooled_ai_alert_recall': tp / na,
            'pooled_alert_precision_at_balanced_CIFAKE_prevalence': tp / (tp + fp) if tp + fp else None,
            'fold_real_false_flag_rates': [r['models'][name]['outer_validation']['false_flag_rate_real'] for r in all_results],
            'fold_ai_alert_recalls': [r['models'][name]['outer_validation']['ai_alert_recall'] for r in all_results],
        }
    return all_results, pooled, sorted(outer_prediction_rows)


def publish(output_dir: Path, report: dict, prediction_rows):
    if output_dir.exists():
        raise RuntimeError(f'Refusing to overwrite existing research folder: {output_dir}')
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.nested_fpr_incomplete_', dir=output_dir.parent) as work:
        stage = Path(work)
        file = stage / 'nested_outer_alerts.csv'
        with file.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.writer(stream)
            writer.writerow(('csv_row', 'label', 'validation_fold', 'five_score',
                             'ten_score', 'five_alert', 'ten_alert'))
            writer.writerows(prediction_rows)
        report['nested_outer_alerts_sha256'] = paired.digest(file)
        (stage / 'nested_threshold_results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        if output_dir.exists():
            raise RuntimeError(f'Output appeared while publishing: {output_dir}')
        os.rename(stage, output_dir)
    print(f'SUCCESS: research-only nested threshold study saved: {output_dir}', flush=True)
    print('No model saved or deployed. CIFAKE TEST not accessed.', flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--audit', action='store_true', help='Verify dataset and fold integrity; no training/writes')
    mode.add_argument('--evaluate', action='store_true', help='Nested training-only threshold study')
    parser.add_argument('--dataset', type=Path, default=fivefold.DEFAULT_DATASET)
    parser.add_argument('--data-dir', type=Path, default=paired.DATA_DIR)
    parser.add_argument('--source-results', type=Path, default=SOURCE_RESULTS)
    parser.add_argument('--output-dir', type=Path, default=OUTPUT_DIR)
    args = parser.parse_args(argv)
    if args.evaluate and args.output_dir.exists():
        raise RuntimeError(f'Output already exists: {args.output_dir}')
    X, y, hashes, meta, groups, folds, near_info, fold_info = fivefold.load_and_audit(args.data_dir, args.dataset)
    source = verify_existing_folds(args.source_results, y, groups, folds)
    print(f'NESTED AUDIT PASSED: {len(y)} CIFAKE TRAIN images, '
          f'{near_info["groups"]} heuristic groups, five unchanged outer folds.', flush=True)
    print('Research rule: one-sided 95% Wilson upper bound on inner OOF REAL false-flag rate '
          '<= 5%; AI alert only, remaining images unresolved.', flush=True)
    print('CIFAKE TEST untouched. Existing outer folds already reviewed, so not a fresh holdout.', flush=True)
    if args.audit:
        print('AUDIT ONLY: no models trained; no files written.', flush=True)
        return 0
    per_fold, pooled, rows = run_nested(X, y, groups, folds)
    report = {
        'status': 'EXPLORATORY_NESTED_CIFAKE_TRAIN_STUDY_NOT_DEPLOYABLE',
        'no_CIFAKE_TEST_access': True,
        'no_production_model_updated': True,
        'no_model_saved': True,
        'research_fpr_target': TARGET_FPR,
        'target_interpretation': 'Exploratory 5% Wilson-upper-bound training-only target, NOT border control requirement',
        'threshold_selection': 'Inner 3-fold OOF scores from outer TRAIN only; one-sided Wilson upper bound; threshold transferred to outer-trained model',
        'model_fitting': 'Same 3-fold group-separated sigmoid-calibrated RBF SVM as previous research',
        'outer_validation_status': 'Existing five outer folds have already been analyzed in previous experiments; not untouched independent evaluation',
        'dataset_metadata_sha256': paired.digest(args.data_dir / 'research_metadata.json'),
        'source': source, 'groups': near_info['groups'],
        'python': platform.python_version(), 'sklearn': sklearn.__version__,
        'per_fold': per_fold, 'pooled': pooled,
        'limitations': [
            'CIFAKE TRAIN 32x32 only; not documents, passports, or deepfakes',
            'Outer folds repeatedly inspected during research; performance is exploratory and possibly optimistically selected',
            'Near-duplicate heuristic is incomplete; no image-source-level independence established',
            'Wilson formula assumes independent Bernoulli observations, which may not hold for CIFAKE',
            'Inner threshold scores derive from smaller fitted models than outer scoring model; score distributions may shift',
            'A training-only 5% bound is not a guarantee about outer-fold or future real-world FPR',
            'Unflagged does NOT mean authentic; alert is not evidence of fraud',
        ],
    }
    publish(args.output_dir, report, rows)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
