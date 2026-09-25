"""Read-only audit of paired 5-feature vs 10-feature CIFAKE TRAIN out-of-fold errors.

Does NOT train models, select thresholds, access CIFAKE TEST, or write files.
The 0.5 cutoff is the experiment's fixed descriptive cutoff, NOT an operating policy.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_SCORE_COLUMNS = ('csv_row', 'label', 'validation_fold', 'five_score', 'ten_score')
REQUIRED_FOLD_COLUMNS = ('csv_row', 'label', 'validation_fold', 'near_group_id')


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_table(path: Path, required: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open(newline='', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or set(required) - set(reader.fieldnames):
            raise ValueError(f'{path.name}: expected columns {required}, got {reader.fieldnames}')
        return list(reader)


def audit(folder: Path) -> dict:
    results_path = folder / 'crossvalidation_results.json'
    scores_path = folder / 'out_of_fold_scores.csv'
    folds_path = folder / 'fold_assignments.csv'
    report = json.loads(results_path.read_text(encoding='utf-8'))
    if report.get('status') != 'experimental_fivefold_CIFAKE_TRAIN_internal_only':
        raise ValueError('Unrecognized research report status')
    if any(report.get(key) is not True for key in
           ('no_production_model_updated', 'no_CIFAKE_TEST_access', 'no_classifier_saved')):
        raise ValueError('Research safety flags not all true')
    for path, field in ((scores_path, 'out_of_fold_scores_sha256'),
                        (folds_path, 'fold_assignments_sha256')):
        actual = digest(path)
        if actual != report.get(field):
            raise ValueError(f'{path.name}: SHA-256 mismatch; aborting without analysis')

    score_rows = load_table(scores_path, REQUIRED_SCORE_COLUMNS)
    fold_rows = load_table(folds_path, REQUIRED_FOLD_COLUMNS)
    if len(score_rows) != 5000 or len(fold_rows) != 5000:
        raise ValueError('Expected exactly 5,000 score and fold rows')
    groups: dict[int, int] = {}
    counts: dict[tuple[int, int, str], Counter] = defaultdict(Counter)
    observed: dict[str, Counter] = {'five_recomputed': Counter(), 'ten_recomputed': Counter()}
    seen = set()
    labels = Counter()
    folds = Counter()
    for expected_row, (s, f) in enumerate(zip(score_rows, fold_rows), start=1):
        row_id = int(s['csv_row'])
        label = int(s['label'])
        fold = int(s['validation_fold'])
        group = int(f['near_group_id'])
        if (row_id, label, fold) != (int(f['csv_row']), int(f['label']),
                                    int(f['validation_fold'])):
            raise ValueError(f'Score/fold mismatch at row {expected_row}')
        if row_id != expected_row or row_id in seen or label not in (0, 1) or fold not in (1, 2, 3, 4, 5):
            raise ValueError(f'Unexpected row id, class or fold: row {expected_row}')
        seen.add(row_id)
        labels[label] += 1
        folds[(fold, label)] += 1
        if group in groups and groups[group] != fold:
            raise ValueError(f'Near-duplicate group {group} crosses validation folds')
        groups[group] = fold
        scores = {key: float(s[col]) for key, col in
                  (('five_recomputed', 'five_score'), ('ten_recomputed', 'ten_score'))}
        if any(not math.isfinite(score) or not 0.0 <= score <= 1.0 for score in scores.values()):
            raise ValueError(f'Invalid probability-like score at row {row_id}')
        pred5 = int(scores['five_recomputed'] >= 0.5)
        pred10 = int(scores['ten_recomputed'] >= 0.5)
        # The models' classifications must be paired on the SAME held-out image.
        if label == 0:
            kind = 'false_ai_flags'
            correct5, correct10 = pred5 == 0, pred10 == 0
        else:
            kind = 'missed_ai_images'
            correct5, correct10 = pred5 == 1, pred10 == 1
        if correct5 and correct10:
            transition = 'both_correct'
        elif correct5:
            transition = 'five_only_correct'
        elif correct10:
            transition = 'ten_only_correct'
        else:
            transition = 'both_wrong'
        counts[(0, label, kind)][transition] += 1
        counts[(fold, label, kind)][transition] += 1
        for key, prediction in (('five_recomputed', pred5), ('ten_recomputed', pred10)):
            if label == 0 and prediction == 1:
                observed[key]['false_ai_flag'] += 1
            if label == 1 and prediction == 0:
                observed[key]['missed_ai'] += 1

    if labels != Counter({0: 2500, 1: 2500}):
        raise ValueError(f'Class balance mismatch: {labels}')
    if any(folds[(fold, label)] != 500 for fold in range(1, 6) for label in (0, 1)):
        raise ValueError('Validation fold class balance mismatch')
    if len(groups) != report['near_duplicate_audit']['groups']:
        raise ValueError('Near-duplicate group count does not match report')
    for model, totals in observed.items():
        expected = report['aggregated_metrics'][model]['pooled_out_of_fold']['confusion_at_fixed_0_5']
        for name in ('false_ai_flag', 'missed_ai'):
            if totals[name] != expected[name]:
                raise ValueError(f'{model} {name}: recomputed {totals[name]} != report {expected[name]}')

    def view(c: Counter) -> dict[str, int]:
        return {name: c[name] for name in
                ('both_correct', 'five_only_correct', 'ten_only_correct', 'both_wrong')}
    real = counts[(0, 0, 'false_ai_flags')]
    fake = counts[(0, 1, 'missed_ai_images')]
    return {
        'status': 'READ_ONLY_AUDIT_PASSED',
        'sample_count': len(score_rows),
        'fold_count': 5,
        'groups': len(groups),
        'fixed_cutoff': 0.5,
        'real_image_transitions': view(real),
        'ai_image_transitions': view(fake),
        'false_ai_flags': {key: observed[key]['false_ai_flag'] for key in observed},
        'missed_ai_images': {key: observed[key]['missed_ai'] for key in observed},
        'fold_transitions': [
            {'fold': fold, 'real': view(counts[(fold, 0, 'false_ai_flags')]),
             'ai': view(counts[(fold, 1, 'missed_ai_images')])}
            for fold in range(1, 6)
        ],
        'interpretation': ('Descriptive paired out-of-fold errors at the PREEXISTING 0.5 cutoff only. '
                           'Do not tune thresholds on these scores and report the same scores as unbiased validation.'),
        'limitations': ('CIFAKE TRAIN 32x32 source domain; possible residual near-duplicate/source leakage; '
                        'not evaluated on identity documents or face deepfakes.'),
        'no_files_written': True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path,
                        default=DEFAULT_ROOT / 'data' / 'research_cifake_fivefold_v01')
    args = parser.parse_args()
    print(json.dumps(audit(args.folder), indent=2))


if __name__ == '__main__':
    main()
