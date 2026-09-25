"""Research-only, paired 5-fold CIFAKE TRAIN cross-validation with heuristic near-duplicate grouping.

    python experiments/crossvalidate_cifake_paired_models.py --audit
    python experiments/crossvalidate_cifake_paired_models.py --compare

Reads the existing, immutable paired TRAIN CSV/manifest and source TRAIN images.
Never opens CIFAKE test, serializes a classifier, or changes deployed predictions.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
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
import sklearn
from sklearn.model_selection import StratifiedGroupKFold

# Reuse the audited feature schema, dataset-integrity checks, identical learning
# procedure, calibration folds, and fixed-0.5 metrics from the first comparison.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_cifake_paired_models as paired  # noqa: E402

DEFAULT_DATASET = Path(os.environ.get('CIFAKE_DATASET_DIR', paired.BACKEND / 'data' / 'CIFAKE' / 'DATASET'))
OUTPUT_DIR = paired.BACKEND / 'data' / 'research_cifake_fivefold_v01'
SEED = paired.SEED
# HEURISTIC ONLY: pHash <=3 AND dHash <=5 on tiny CIFAKE images. The heuristic
# can miss near copies and mistakenly link distinct images; group candidates
# conservatively rather than claim image/source-level deduplication is complete.
PHASH_MAX = 3
DHASH_MAX = 5


def perceptual_hashes(blob: bytes) -> tuple[int, int]:
    image = cv2.imdecode(np.frombuffer(blob, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if image is None or min(image.shape) < 8:
        raise RuntimeError('Could not decode image or image smaller than 8 pixels')
    # dHash: horizontal adjacent-pixel differences on 9x8 grayscale patch.
    gradient = cv2.resize(image, (9, 8), interpolation=cv2.INTER_AREA)
    dhash = 0
    for bit in (gradient[:, 1:] > gradient[:, :-1]).flat:
        dhash = (dhash << 1) | int(bit)
    # pHash: low spatial frequencies on a 32x32 grayscale patch.
    block = cv2.resize(image, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    coeff = cv2.dct(block)[:8, :8].reshape(-1)
    median = float(np.median(coeff[1:]))
    phash = 0
    for value in coeff:
        phash = (phash << 1) | int(value > median)
    return phash, dhash


def near_duplicate_groups(sha: list[str], phashes: list[int], dhashes: list[int], labels: np.ndarray):
    """Union all candidate pairs, including cross-class matches, to prevent pair leakage.

    Four independent 16-bit pHash blocks give candidate completeness for
    pHash Hamming distance <=3 (pigeonhole principle); dHash then filters.
    """
    n = len(sha)
    if not (len(phashes) == len(dhashes) == len(labels) == n):
        raise ValueError('Hash and label lengths differ')
    parent = list(range(n))
    rank = [0] * n

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        a, b = find(a), find(b)
        if a == b:
            return
        if rank[a] < rank[b]:
            a, b = b, a
        parent[b] = a
        if rank[a] == rank[b]:
            rank[a] += 1

    # Deduplicate pHash-block candidates without storing an O(N^2) list.
    buckets = defaultdict(list)
    for i, value in enumerate(phashes):
        for block in range(4):
            buckets[(block, (value >> (16 * block)) & 0xffff)].append(i)
    candidate_pairs_compared = 0
    flagged_pairs = 0
    cross_label_pairs = 0
    examples = []
    for (block, _), indices in buckets.items():
        for pos, i in enumerate(indices):
            for next_pos in range(pos + 1, len(indices)):
                j = indices[next_pos]
                # Process each pair once: its earliest matching block owns it.
                if any(((phashes[i] >> (16 * earlier)) & 0xffff) ==
                       ((phashes[j] >> (16 * earlier)) & 0xffff)
                       for earlier in range(block)):
                    continue
                candidate_pairs_compared += 1
                if (phashes[i] ^ phashes[j]).bit_count() > PHASH_MAX:
                    continue
                if (dhashes[i] ^ dhashes[j]).bit_count() > DHASH_MAX:
                    continue
                flagged_pairs += 1
                cross_label_pairs += int(labels[i] != labels[j])
                union(i, j)
                if len(examples) < 20:
                    examples.append({
                        'first_row': i + 1, 'second_row': j + 1,
                        'first_label': int(labels[i]), 'second_label': int(labels[j]),
                        'p_hamming': (phashes[i] ^ phashes[j]).bit_count(),
                        'd_hamming': (dhashes[i] ^ dhashes[j]).bit_count(),
                        'identical_bytes': sha[i] == sha[j],
                    })
    # Enforce exact-byte duplication even if perceptual transforms ever change.
    by_sha = {}
    for i, value in enumerate(sha):
        if value in by_sha:
            union(i, by_sha[value])
        else:
            by_sha[value] = i
    groups = np.asarray([find(i) for i in range(n)], dtype=np.int64)
    members = Counter(groups.tolist())
    mixed = set()
    component_labels = defaultdict(set)
    for group, label in zip(groups, labels):
        component_labels[int(group)].add(int(label))
    mixed.update(g for g, values in component_labels.items() if len(values) > 1)
    info = {
        'method': f'pHash64 Hamming <= {PHASH_MAX} AND dHash64 Hamming <= {DHASH_MAX}; plus exact SHA-256',
        'candidate_filter_is_heuristic': True,
        'limitations': '32x32 source images; perceptual hashes can produce false matches and miss transformed/semantic duplicates; no source-identity audit',
        'candidate_pairs_compared': candidate_pairs_compared,
        'flagged_pairs': flagged_pairs,
        'flagged_cross_label_pairs': cross_label_pairs,
        'flagged_pair_examples': examples,
        'groups': len(members),
        'groups_with_multiple_images': sum(size > 1 for size in members.values()),
        'largest_group_size': max(members.values(), default=0),
        'mixed_label_groups': len(mixed),
        'mixed_label_group_sizes': sorted((members[g] for g in mixed), reverse=True)[:10],
    }
    return groups, info


def load_and_audit(data_dir: Path, dataset: Path):
    X, y, hashes, meta, duplicate_count = paired.load_verified_dataset(data_dir)
    manifest = paired.read_csv(
        data_dir / paired.MANIFEST_FILE,
        ['csv_row', 'split', 'label', 'relative_path', 'sha256'],
    )
    root = (dataset / 'TRAIN').resolve(strict=True)
    sha, phashes, dhashes = [], [], []
    start = time.monotonic()
    for i, row in enumerate(manifest):
        path = (dataset / row['relative_path']).resolve(strict=True)
        if not path.is_relative_to(root):
            raise RuntimeError(f'Image path escaped CIFAKE TRAIN at row {i + 1}')
        blob = path.read_bytes()
        actual_sha = hashlib.sha256(blob).hexdigest()
        if actual_sha != row['sha256'] or actual_sha != hashes[i]:
            raise RuntimeError(f'Source image SHA-256 mismatch at row {i + 1}; aborting')
        p_hash, d_hash = perceptual_hashes(blob)
        sha.append(actual_sha)
        phashes.append(p_hash)
        dhashes.append(d_hash)
        if (i + 1) % 1000 == 0:
            print(f'Verified + perceptually hashed {i + 1}/{len(manifest)} CIFAKE TRAIN images '
                  f'({time.monotonic() - start:.1f}s)', flush=True)
    groups, near_info = near_duplicate_groups(sha, phashes, dhashes, y)
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    folds = list(splitter.split(X, y, groups=groups))
    valid_seen = set()
    fold_info = []
    for fold, (train, valid) in enumerate(folds, start=1):
        if set(groups[train]) & set(groups[valid]):
            raise RuntimeError(f'Perceptual/identical group leakage in fold {fold}')
        if valid_seen.intersection(valid.tolist()):
            raise RuntimeError(f'Validation row used twice: fold {fold}')
        valid_seen.update(valid.tolist())
        training_classes = np.bincount(y[train], minlength=2)
        validation_classes = np.bincount(y[valid], minlength=2)
        if min(training_classes) < 50 or min(validation_classes) < 50:
            raise RuntimeError(f'Fold {fold} insufficient class balance; inspect groups')
        fold_info.append({
            'fold': fold, 'train_count': len(train), 'validation_count': len(valid),
            'train_labels': training_classes.tolist(), 'validation_labels': validation_classes.tolist(),
            'train_groups': len(set(groups[train])), 'validation_groups': len(set(groups[valid])),
        })
    if len(valid_seen) != len(y):
        raise RuntimeError('Not all rows assigned to one validation fold')
    print(f'AUDIT PASSED: {len(y)} verified TRAIN images; exact duplicate pairs={duplicate_count}; '
          f'heuristic flagged pairs={near_info["flagged_pairs"]}; '
          f'cross-label pairs={near_info["flagged_cross_label_pairs"]}; '
          f'groups={near_info["groups"]}; largest group={near_info["largest_group_size"]}.', flush=True)
    print('Every heuristic candidate pair and every identical-byte pair is grouped within folds.', flush=True)
    for info in fold_info:
        print(f'Fold {info["fold"]}: train={info["train_count"]} labels={info["train_labels"]}; '
              f'validation={info["validation_count"]} labels={info["validation_labels"]}', flush=True)
    print('HEURISTIC LIMITATION: perceptual grouping is not proof of no near-duplicate/source leakage.', flush=True)
    print('CIFAKE TEST not accessed; existing BeyondPixels predictions unaffected.', flush=True)
    return X, y, hashes, meta, groups, folds, near_info, fold_info


def metric_mean_std(items: list[dict], key: str):
    values = np.asarray([item[key] for item in items], dtype=float)
    return {'mean': float(np.mean(values)), 'std_across_folds_ddof_1': float(np.std(values, ddof=1)),
            'per_fold': values.tolist()}


def compare(X, y, hashes, meta, groups, folds, near_info, fold_info, data_dir):
    metric_keys = ('roc_auc', 'brier_score', 'balanced_accuracy_at_fixed_0_5',
                   'false_positive_rate_at_fixed_0_5', 'false_negative_rate_at_fixed_0_5')
    oof = {'five_recomputed': np.full(len(y), np.nan),
           'ten_recomputed': np.full(len(y), np.nan)}
    per_fold = []
    for fold_id, (train, valid) in enumerate(folds, 1):
        fold_results = {'fold': fold_id, 'n_train': len(train), 'n_validation': len(valid), 'models': {}}
        for name, n_columns in (('five_recomputed', 5), ('ten_recomputed', 10)):
            print(f'Fold {fold_id}/5: fitting {name} on {len(train)} TRAIN-partition images...', flush=True)
            # Calibration is fitted ONLY inside this fold's training data, using
            # group-disjoint inner folds from the existing audited helper.
            model = paired.fit_research_model(X[train, :n_columns], y[train], groups[train])
            scores = model.predict_proba(X[valid, :n_columns])[:, list(model.classes_).index(1)]
            oof[name][valid] = scores
            fold_results['models'][name] = paired.metrics(y[valid], scores)
            print(f'  {name}: AUC={fold_results["models"][name]["roc_auc"]:.4f}; '
                  f'Brier={fold_results["models"][name]["brier_score"]:.4f}; '
                  f'FPR={fold_results["models"][name]["false_positive_rate_at_fixed_0_5"]:.4f}; '
                  f'FNR={fold_results["models"][name]["false_negative_rate_at_fixed_0_5"]:.4f}', flush=True)
        per_fold.append(fold_results)
    if not all(np.isfinite(scores).all() for scores in oof.values()):
        raise RuntimeError('Missing or nonfinite out-of-fold predictions')
    aggregate = {}
    for name, scores in oof.items():
        results = [f['models'][name] for f in per_fold]
        aggregate[name] = {
            'pooled_out_of_fold': paired.metrics(y, scores),
            'per_fold_summary': {metric: metric_mean_std(results, metric) for metric in metric_keys},
        }
    differences = {}
    for metric in metric_keys:
        differences[metric] = metric_mean_std(
            [{metric: f['models']['ten_recomputed'][metric] - f['models']['five_recomputed'][metric]}
             for f in per_fold], metric)
    return {
        'status': 'experimental_fivefold_CIFAKE_TRAIN_internal_only',
        'no_production_model_updated': True,
        'no_CIFAKE_TEST_access': True,
        'no_classifier_saved': True,
        'dataset_metadata_sha256': paired.digest(data_dir / 'research_metadata.json'),
        'dataset_file_sha256': meta['generated_file_sha256'],
        'seed': SEED, 'python': platform.python_version(), 'opencv': cv2.__version__,
        'scikit_learn': sklearn.__version__,
        'split': 'five-fold StratifiedGroupKFold by transitive exact-image + heuristic near-duplicate groups',
        'calibration': 'three StratifiedGroupKFold splits entirely within each outer training fold; identical folds/model configuration for paired models',
        'near_duplicate_audit': near_info,
        'fold_composition': fold_info,
        'per_fold_metrics': per_fold,
        'aggregated_metrics': aggregate,
        'paired_fold_difference_ten_minus_five': differences,
        'limitations': [
            'CIFAKE TRAIN 32x32 images only: not identity documents, unseen generators, or face deepfakes',
            'Heuristic pHash/dHash grouping may miss near-duplicates and may group unrelated images',
            'No source-identity independence or cross-dataset generalization established',
            'Five correlated CV folds do not imply a statistical confidence interval or certified improvement',
            'Fixed 0.5 cutoff is descriptive only and not a validated screening threshold',
            'Neither model deployed, and CIFAKE TEST untouched',
        ],
    }, oof


def publish(output: Path, results: dict, y: np.ndarray, groups: np.ndarray, folds, oof):
    if output.exists():
        raise RuntimeError(f'Refusing to overwrite existing research output: {output}')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.fivefold_incomplete_', dir=output.parent) as work:
        stage = Path(work)
        roles = np.zeros(len(y), dtype=np.int64)
        for fold_id, (_, valid) in enumerate(folds, 1):
            roles[valid] = fold_id
        if np.any(roles == 0):
            raise RuntimeError('Missing fold assignment')
        manifest = stage / 'fold_assignments.csv'
        with manifest.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.writer(stream)
            writer.writerow(('csv_row', 'label', 'validation_fold', 'near_group_id'))
            for index in range(len(y)):
                writer.writerow((index + 1, int(y[index]), int(roles[index]), int(groups[index])))
        results['fold_assignments_sha256'] = paired.digest(manifest)
        # Saved scores are out-of-fold only, not a model or deployment artifact.
        score_file = stage / 'out_of_fold_scores.csv'
        with score_file.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.writer(stream)
            writer.writerow(('csv_row', 'label', 'validation_fold', 'five_score', 'ten_score'))
            for index in range(len(y)):
                writer.writerow((index + 1, int(y[index]), int(roles[index]),
                                 format(oof['five_recomputed'][index], '.12g'),
                                 format(oof['ten_recomputed'][index], '.12g')))
        results['out_of_fold_scores_sha256'] = paired.digest(score_file)
        (stage / 'crossvalidation_results.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
        if output.exists():
            raise RuntimeError(f'Output appeared during analysis: {output}')
        os.rename(stage, output)
    print(f'SUCCESS: five-fold research comparison saved in {output}', flush=True)
    print('No model saved; CIFAKE TEST and existing BeyondPixels predictions unchanged.', flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--audit', action='store_true', help='Read and verify only; train nothing, write nothing')
    action.add_argument('--compare', action='store_true', help='Run paired five-fold research comparison')
    parser.add_argument('--data-dir', type=Path, default=paired.DATA_DIR)
    parser.add_argument('--dataset', type=Path, default=DEFAULT_DATASET)
    parser.add_argument('--output-dir', type=Path, default=OUTPUT_DIR)
    args = parser.parse_args(argv)
    if args.compare and args.output_dir.exists():
        raise RuntimeError(f'Output directory exists; refusing to overwrite: {args.output_dir}')
    X, y, hashes, meta, groups, folds, near_info, fold_info = load_and_audit(args.data_dir, args.dataset)
    if args.audit:
        print('AUDIT ONLY: no classifier trained; no files written.', flush=True)
        return 0
    results, oof = compare(X, y, hashes, meta, groups, folds, near_info, fold_info, args.data_dir)
    publish(args.output_dir, results, y, groups, folds, oof)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
