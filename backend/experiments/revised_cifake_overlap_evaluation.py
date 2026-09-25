"""Revision v02: CIFAKE TEST study after v01 stopped on TRAIN/TEST exact overlap.

--audit: verify v01 TRAIN and frozen protocol only; does not read TEST.
--freeze: create distinct, immutable-by-policy v02 protocol; does not read TEST.
--evaluate: inventory ALL TEST bytes first; fail closed unless observed overlap and
           duplication match predeclared counts; exclude TRAIN-identical TEST
           hashes from analysis without modifying images; report BOTH retained
           file-level and exact-hash-deduplicated sensitivity metrics.

Research only. Earlier STAI used CIFAKE TEST; overlap counts were inspected after
v01 abort. This is a REVISED EXPLORATORY evaluation, never a pristine holdout.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

import numpy as np
from sklearn.model_selection import StratifiedGroupKFold

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import frozen_cifake_evaluation as frozen

BACKEND = frozen.BACKEND
PROTOCOL_DIR = BACKEND / 'data' / 'research_cifake_revised_protocol_v02'
RESULT_DIR = BACKEND / 'data' / 'research_cifake_test_revised_v02'
EXPECTED_OVERLAP = {'REAL': 0, 'FAKE': 20}
EXPECTED_TEST_DUPLICATE_PAIRS = 38
EXPECTED_TEST_CROSS_LABEL_DUPLICATES = 0


def load_train_hash_labels(path: Path):
    with path.open(newline='', encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 5000:
        raise RuntimeError('TRAIN manifest row count changed')
    mapping = {}
    for row in rows:
        digest, label = row['sha256'], int(row['label'])
        if len(digest) != 64 or label not in (0, 1):
            raise RuntimeError('Invalid TRAIN manifest entry')
        if digest in mapping and mapping[digest] != label:
            raise RuntimeError('Conflicting TRAIN labels on identical bytes')
        mapping[digest] = label
    return mapping


def make_plan(v01_sha: str, source_hashes: dict, versions: dict):
    return {
        'protocol_version': 'beyondpixels-cifake-overlap-revision-v02',
        'status': 'FROZEN_REVISED_EXPLORATORY_PLAN_TEST_PREVIOUSLY_INSPECTED',
        'supersedes_for_analysis_only': 'v01 aborted on test/FAKE/126 (3).jpg due to identical TRAIN bytes; preserve v01 folder',
        'original_protocol_sha256': v01_sha,
        'reason': 'Read-only post-abort inventory found 20 identical TRAIN/TEST FAKE images and 38 within-TEST exact-byte duplicate pairs; no cross-label duplicates.',
        'expected_test_inventory': {'REAL': 10000, 'FAKE': 10000},
        'predeclared_exclusion': 'Exclude EVERY TEST image whose byte SHA256 is present among selected 5000 TRAIN; no filename or model-score exclusions; never delete originals.',
        'expected_train_test_exact_overlap_by_class': EXPECTED_OVERLAP,
        'expected_within_test_additional_duplicate_images': EXPECTED_TEST_DUPLICATE_PAIRS,
        'expected_cross_label_exact_duplicate_groups': EXPECTED_TEST_CROSS_LABEL_DUPLICATES,
        'primary_population': 'All remaining TEST file entries, including TEST-to-TEST repeats: expected REAL=10000, FAKE=9980, total=19980.',
        'sensitivity_population': 'One retained TEST file per unique SHA256 after overlap exclusions, keeping first filename in original REAL-then-FAKE sorted order; expected total=19942.',
        'model_and_training': 'IDENTICAL to frozen v01: five/ten features; 5000 TRAIN images; grouped sigmoid-calibrated StandardScaler + RBF SVC C=1; three training-only OOF threshold folds seed 20260920.',
        'research_alert_rule': 'IDENTICAL to frozen v01: most permissive model-specific >= score threshold meeting inner TRAIN OOF one-sided 95% Wilson upper REAL FPR bound <= 0.05.',
        'metrics': ['ROC AUC', 'Brier score', 'fixed 0.5 confusion and balanced accuracy', 'research alert REAL false-flag rate and AI alert recall', 'one-sided Wilson upper REAL false-flag bound'],
        'interpretation': 'Not a clean untouched test; only CIFAKE 32x32; alert is a prompt for review; unflagged is unresolved, not genuine.',
        'no_test_feedback': 'No threshold, model, feature, calibration, subgroup or exclusion changes using observed TEST scores. Do not rerun after reports to optimize metrics.',
        'deployment': 'none; no model files saved; production API and thresholds unchanged',
        'source_sha256': source_hashes,
        'environment': versions,
    }


def verify_original(locked: dict, versions: dict) -> str:
    path = frozen.PROTOCOL_DIR / 'protocol.json'
    frozen.verify_frozen_plan(path, locked, versions)
    return frozen.checksum(path)


def verify_revision(path: Path, expected: dict):
    if not path.is_file():
        raise RuntimeError('v02 protocol missing: run --freeze before --evaluate')
    actual = json.loads(path.read_text(encoding='utf-8'))
    if actual != expected:
        raise RuntimeError('v02 protocol source, environment, or plan changed: STOP')
    return frozen.checksum(path)


def inventory_test(paths, train_hash_labels: dict, dataset: Path):
    """Inspect TEST image bytes only; check integrity BEFORE any feature/model fit.

    Returns retained (path,label) rows, aligned SHA256s, excluded manifest and
    descriptive audit. Exactly reproduces counts known from prior read-only audit.
    """
    seen = defaultdict(list)
    ordered_hashes = []
    retained = []
    retained_hashes = []
    excluded = []
    overlap_counts = Counter()
    for path, label in paths:
        digest = frozen.checksum(path)
        ordered_hashes.append(digest)
        relative = path.relative_to(dataset).as_posix()
        seen[digest].append((label, relative))
        if digest in train_hash_labels:
            if train_hash_labels[digest] != label:
                raise RuntimeError('Cross-label TRAIN/TEST exact overlap: STOP')
            overlap_counts['REAL' if label == 0 else 'FAKE'] += 1
            excluded.append({'relative_path': relative, 'label': label, 'sha256': digest,
                             'reason': 'identical_sha256_to_selected_TRAIN'})
        else:
            retained.append((path, label))
            retained_hashes.append(digest)
    dup_groups = {h: entries for h, entries in seen.items() if len(entries) > 1}
    conflicting = sum(len({lab for lab, _ in entries}) > 1 for entries in dup_groups.values())
    repeats = sum(len(entries) - 1 for entries in dup_groups.values())
    expected_total = 2 * frozen.EXPECTED_TEST_PER_CLASS
    expected_retained = expected_total - sum(EXPECTED_OVERLAP.values())
    expected_unique = expected_retained - EXPECTED_TEST_DUPLICATE_PAIRS
    if (any(overlap_counts[name] != value for name, value in EXPECTED_OVERLAP.items())
            or len(excluded) != sum(EXPECTED_OVERLAP.values())
            or len({r['sha256'] for r in excluded}) != len(excluded)
            or repeats != EXPECTED_TEST_DUPLICATE_PAIRS
            or len(dup_groups) != EXPECTED_TEST_DUPLICATE_PAIRS
            or conflicting != EXPECTED_TEST_CROSS_LABEL_DUPLICATES
            or len(paths) != expected_total or len(retained) != expected_retained
            or len(set(retained_hashes)) != expected_unique):
        raise RuntimeError('TEST image integrity inventory differs from predeclared v02 expectations: STOP')
    unique_index = []
    visited = set()
    for idx, digest in enumerate(retained_hashes):
        if digest not in visited:
            visited.add(digest)
            unique_index.append(idx)
    if len(unique_index) != expected_unique:
        raise RuntimeError("Unexpected deduplicated retained count: STOP")
    summary = {
        'test_inventory': len(paths),
        'test_distinct_sha256': len(seen),
        'overlap_excluded_by_class': dict(EXPECTED_OVERLAP),
        'overlap_excluded_total': len(excluded),
        'within_test_exact_duplicate_groups': len(dup_groups),
        'within_test_extra_repeated_files': repeats,
        'within_test_cross_label_duplicate_groups': conflicting,
        'retained_file_entries': len(retained),
        'retained_distinct_sha256': len(unique_index),
        'retained_real': sum(label == 0 for _, label in retained),
        'retained_fake': sum(label == 1 for _, label in retained),
        'full_test_ordered_hashes_sha256': hashlib.sha256('\n'.join(ordered_hashes).encode('ascii')).hexdigest(),
    }
    print(f'V02 INVENTORY PASSED: {len(paths)} TEST entries; excluded {len(excluded)} TRAIN-identical; '
          f'retained {len(retained)} files / {len(unique_index)} unique hashes; {repeats} repeated TEST entries.', flush=True)
    return retained, retained_hashes, unique_index, excluded, summary


def research_scores(X, y, groups, Xt, yt, unique_index):
    inner_folds = list(StratifiedGroupKFold(n_splits=3, shuffle=True,
                        random_state=frozen.INNER_SEED).split(X, y, groups=groups))
    all_scores = {}
    metrics = {}
    for name, width in frozen.nested.CONFIGS:
        print(f'v02: {name}: fitting three TRAIN-only inner-OOF models...', flush=True)
        inner_scores = frozen.nested.inner_oof(
            X, y, groups, inner_folds, width, frozen.paired.fit_research_model)
        selected = frozen.nested.select_alert_threshold(y, inner_scores, frozen.TARGET_FPR)
        print(f'v02: {name}: fitting one full TRAIN-only classifier...', flush=True)
        model = frozen.paired.fit_research_model(X[:, :width], y, groups)
        scores = model.predict_proba(Xt[:, :width])[:, list(model.classes_).index(1)]
        if not np.isfinite(scores).all():
            raise RuntimeError('Non-finite TEST scores')
        unique_idx = np.asarray(unique_index, dtype=int)
        metrics[name] = {
            'training_only_threshold': selected,
            'primary_retained_files': {
                'alert_vs_unresolved': frozen.nested.alert_metrics(yt, scores, selected['threshold']),
                'fixed_0_5_descriptive': frozen.paired.metrics(yt, scores),
            },
            'sensitivity_unique_test_sha256': {
                'alert_vs_unresolved': frozen.nested.alert_metrics(
                    yt[unique_idx], scores[unique_idx], selected['threshold']),
                'fixed_0_5_descriptive': frozen.paired.metrics(yt[unique_idx], scores[unique_idx]),
            },
        }
        all_scores[name] = scores
        print(f'  primary TEST FPR={metrics[name]["primary_retained_files"]["alert_vs_unresolved"]["false_flag_rate_real"]:.3%}; '
              f'AI alert recall={metrics[name]["primary_retained_files"]["alert_vs_unresolved"]["ai_alert_recall"]:.3%}', flush=True)
    return metrics, all_scores


def write_results(output: Path, report: dict, excluded: list[dict], retained, hashes, scores, dataset: Path):
    if output.exists():
        raise RuntimeError('Revised results already exist: refusing to overwrite')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.revised_test_incomplete_', dir=output.parent) as temp:
        stage = Path(temp)
        (stage / 'revised_test_results.json').write_text(
            json.dumps(report, indent=2) + '\n', encoding='utf-8')
        with (stage / 'excluded_exact_overlap.csv').open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=['relative_path', 'label', 'sha256', 'reason'])
            writer.writeheader()
            writer.writerows(excluded)
        with (stage / 'paired_test_scores.csv').open('w', newline='', encoding='utf-8') as stream:
            columns = ['relative_path', 'label', 'sha256', 'five_recomputed_score', 'ten_recomputed_score']
            writer = csv.writer(stream)
            writer.writerow(columns)
            for i, ((path, label), digest) in enumerate(zip(retained, hashes)):
                writer.writerow([path.relative_to(dataset).as_posix(), label, digest,
                                 format(float(scores['five_recomputed'][i]), '.17g'),
                                 format(float(scores['ten_recomputed'][i]), '.17g')])
        if output.exists():
            raise RuntimeError('Revised output appeared during evaluation: STOP')
        os.rename(stage, output)
    print(f'SUCCESS: revised exploratory TEST report saved: {output}', flush=True)
    print('Original v01 frozen protocol preserved; no classifier saved or deployed.', flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--audit', action='store_true', help='TRAIN/v01 audit only; no TEST read or writes')
    mode.add_argument('--freeze', action='store_true', help='Freeze v02 amendment, no TEST read or scoring')
    mode.add_argument('--evaluate', action='store_true', help='One revised exploratory TEST evaluation')
    parser.add_argument('--dataset', type=Path, default=frozen.DATASET)
    args = parser.parse_args(argv)
    if args.evaluate and RESULT_DIR.exists():
        raise RuntimeError('Revised test report already exists: refusing to rerun')
    X, y, hashes, groups, locked, versions = frozen.verify_train_sources(args.dataset)
    v01_sha = verify_original(locked, versions)
    source_hashes = dict(locked)
    source_hashes['experiments/revised_cifake_overlap_evaluation.py'] = frozen.checksum(Path(__file__))
    expected = make_plan(v01_sha, source_hashes, versions)
    plan_path = PROTOCOL_DIR / 'protocol.json'
    if args.audit:
        print(f'V02 TRAIN AUDIT PASSED: v01 protocol SHA256={v01_sha}; '
              'no TEST read, no models fit, no files written.', flush=True)
        return 0
    if args.freeze:
        if PROTOCOL_DIR.exists():
            raise RuntimeError('v02 protocol already exists: preserve, do not overwrite')
        PROTOCOL_DIR.mkdir(parents=True)
        with plan_path.open('x', encoding='utf-8') as out:
            json.dump(expected, out, indent=2)
            out.write('\n')
        print(f'V02 FROZEN: {plan_path}', flush=True)
        print(f'V02 PROTOCOL SHA256: {frozen.checksum(plan_path)}', flush=True)
        print('Historical test overlap previously inspected; no TEST accessed by this freeze.', flush=True)
        return 0
    plan_sha = verify_revision(plan_path, expected)
    print(f'V02 FROZEN PROTOCOL VERIFIED: {plan_sha}', flush=True)
    paths = frozen.test_paths(args.dataset)
    train_hash_labels = load_train_hash_labels(
        BACKEND / 'data/research_cifake_train_10feature_v01/train_image_manifest.csv')
    if set(map(str, hashes)) != set(train_hash_labels):
        raise RuntimeError('TRAIN source hashes differ from manifest: STOP')
    retained, retained_hashes, unique_idx, excluded, audit = inventory_test(
        paths, train_hash_labels, args.dataset)
    Xt, yt, repeats, extracted_hashes = frozen.test_features(retained, hashes, args.dataset)
    if extracted_hashes != retained_hashes or repeats != 38:
        raise RuntimeError('TEST image bytes changed between inventory and extraction: STOP')
    if np.bincount(yt, minlength=2).tolist() != [10000, 9980]:
        raise RuntimeError('TEST label counts differ after integrity checks')
    metrics, scores = research_scores(X, y, groups, Xt, yt, unique_idx)
    report = {
        'status': 'REVISED_EXPLORATORY_CIFAKE_TEST_AFTER_DOCUMENTED_OVERLAP_NOT_INDEPENDENT',
        'v01_abort_preserved': True,
        'v01_protocol_sha256': v01_sha,
        'revised_protocol_sha256': plan_sha,
        'dataset_scope': 'CIFAKE 32x32 TEST previously accessed by historical STAI and overlap audit; not independent',
        'predeclared_overlap_policy': 'exclude exact TRAIN byte duplicates only; no score filtering; preserve duplicates for primary file-level metrics',
        'predeclared_duplicate_sensitivity': 'once per distinct retained SHA256; first filename by sorted order',
        'inventory': audit,
        'models': metrics,
        'interpretation': 'AI alert vs unresolved; unflagged is NOT authentic; flagged is NOT fraud proof',
        'limitations': [
            'Revised TEST analysis after v01 abort and overlap inspection, not a fresh independent evaluation',
            'Only exact overlap excluded; transformed/semantic and same-source leakage remain possible',
            'Within-TEST duplicated file entries affect primary metrics; unique-byte sensitivity separately reported',
            'CIFAKE low-resolution natural/synthetic images are not document or face deepfake benchmarks',
            'Wilson bound on TRAIN inner OOF scores does not guarantee TEST FPR',
            'Balanced CIFAKE test prevalence not representative of document-screening prevalence',
            'Models never saved, deployed, or used for automated identity decisions',
        ],
    }
    write_results(RESULT_DIR, report, excluded, retained, retained_hashes, scores, args.dataset)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
