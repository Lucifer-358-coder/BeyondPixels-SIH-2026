"""Build a versioned CIFAKE TRAIN-only paired 5/10-feature research dataset.

No model training or inference, no reads from CIFAKE test, no writes to source data.
Reconstruct the 5000-row sampling sequence of extract_cifake_5000_direct.py.
Four stable legacy columns must match the source CSV; shadow is deliberately
recomputed and its historical mismatch documented rather than silently reused.

Run from BeyondPixels/backend using its existing virtual environment:
  python experiments/build_cifake_ten_features.py --smoke
  python experiments/build_cifake_ten_features.py --full
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import shutil
import sys
import tempfile
import time

import cv2
import numpy as np
from PIL import __version__ as pillow_version
import scipy

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from stai_features import FEATURE_NAMES, extract_stai_features  # noqa: E402
from expanded_forensics import (  # noqa: E402
    DESCRIPTOR_VERSION,
    extract_exploratory_descriptors,
)

SOURCE_CSV = BACKEND / 'data' / 'cifake_training_data_5000_direct.csv'
EXPECTED_CSV_SHA256 = '0518034a29d2299eaeddf6998ae89447057992928d319414cfad771967edbc15'
DEFAULT_DATASET = Path(os.environ.get('CIFAKE_DATASET_DIR', BACKEND / 'data' / 'CIFAKE' / 'DATASET'))
OUTPUT_FOLDER = BACKEND / 'data' / 'research_cifake_train_10feature_v01'
EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
LEGACY_STABLE = FEATURE_NAMES[:4]
EXTRA_NAMES = (
    'fine_residual_energy_ratio',
    'medium_residual_energy_ratio',
    'coarse_residual_energy_ratio',
    'mid_band_energy_fraction',
    'high_band_energy_fraction',
)
SAMPLE_INDICES = (0, 625, 1250, 2499, 2500, 3125, 3750, 4999)
TOL = 0.00011  # CSV is rounded to four decimals.


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_rows(path: Path, expected_hash: str = EXPECTED_CSV_SHA256) -> list[dict]:
    if not path.is_file():
        raise RuntimeError(f'Source CSV not found: {path}')
    if sha256(path.read_bytes()) != expected_hash:
        raise RuntimeError('Source CSV SHA-256 differs from the audited 5000-row CSV; STOP.')
    with path.open(newline='', encoding='utf-8') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != [*FEATURE_NAMES, 'label']:
            raise RuntimeError('Unexpected source CSV column order; STOP.')
        rows = list(reader)
    if len(rows) != 5000 or [r['label'] for r in rows].count('0') != 2500 or [r['label'] for r in rows].count('1') != 2500:
        raise RuntimeError('Unexpected source CSV class distribution; STOP.')
    return rows


def reconstruct_selection(dataset: Path, rows: list[dict]) -> list[tuple[Path, int, str]]:
    """Match Python's original sorted(Path) + one shared seeded RNG."""
    if not dataset.is_dir():
        raise RuntimeError(f'CIFAKE dataset directory does not exist: {dataset}')
    rng = random.Random(20260918)
    selection = []
    for name, label in (('REAL', 0), ('FAKE', 1)):
        folder = dataset / 'TRAIN' / name
        if not folder.is_dir():
            raise RuntimeError(f'Missing CIFAKE TRAIN directory: {folder}')
        images = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONS)
        if len(images) < 2500:
            raise RuntimeError(f'Too few TRAIN images in {folder}: {len(images)}')
        chosen = rng.sample(images, 2500)
        selection.extend((p, label, p.relative_to(dataset).as_posix()) for p in chosen)
        print(f'{name}: reconstructed 2500 TRAIN images (available {len(images)})', flush=True)
    if len(selection) != len(rows):
        raise RuntimeError('Selection count does not match CSV')
    for i, (_, label, relative) in enumerate(selection):
        if str(label) != rows[i]['label'] or not relative.startswith(('TRAIN/REAL/', 'TRAIN/FAKE/')):
            raise RuntimeError(f'Class/path mismatch at row {i+1}')
    return selection


def calculate(data: bytes) -> tuple[dict[str, float], dict[str, float]]:
    vector, _observations = extract_stai_features(data)
    if vector.shape != (1, 5) or not np.isfinite(vector).all():
        raise RuntimeError('Five-feature extractor returned invalid data')
    legacy = {key: round(float(v), 4) for key, v in zip(FEATURE_NAMES, vector[0])}
    extra = extract_exploratory_descriptors(data)
    if extra.get('status') != 'completed' or extra.get('version') != DESCRIPTOR_VERSION:
        raise RuntimeError(f'Five-feature research extraction unavailable: {extra.get("status")}')
    values = extra.get('descriptors', {})
    if set(values) != set(EXTRA_NAMES) or not all(np.isfinite(values[k]) and values[k] >= 0 for k in EXTRA_NAMES):
        raise RuntimeError('Unexpected/nonfinite research descriptor values')
    return legacy, {key: float(values[key]) for key in EXTRA_NAMES}


def stable_mismatches(current: dict[str, float], original: dict) -> dict[str, float]:
    return {key: abs(current[key] - float(original[key])) for key in LEGACY_STABLE
            if abs(current[key] - float(original[key])) > TOL}


def smoke(selection: list[tuple[Path, int, str]], rows: list[dict]) -> dict:
    print('\n=== EIGHT-IMAGE PREFLIGHT (TRAIN only; no outputs written) ===', flush=True)
    old_shadow_differences = []
    for index in SAMPLE_INDICES:
        path, label, relative = selection[index]
        data = path.read_bytes()
        legacy, extra = calculate(data)
        mismatches = stable_mismatches(legacy, rows[index])
        shadow_diff = abs(legacy['shadow_norm'] - float(rows[index]['shadow_norm']))
        old_shadow_differences.append(shadow_diff)
        print(f'Row {index+1}: {relative} | stable-column differences={mismatches} | '
              f'old-shadow difference={shadow_diff:.4f} | 5 new values computed', flush=True)
        if mismatches:
            raise RuntimeError(f'Stable legacy columns mismatch at row {index+1}; no files written.')
    print('SMOKE PASSED: 8 TRAIN images; four stable columns match; shadow differences documented.', flush=True)
    return {'checked': len(SAMPLE_INDICES), 'shadow_differences': old_shadow_differences}


def build(dataset: Path, rows: list[dict], selection: list[tuple[Path, int, str]], output: Path) -> None:
    if output.exists():
        raise RuntimeError(f'Research output already exists; refusing to overwrite: {output}')
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix='.ten_feature_incomplete_', dir=str(output.parent)))
    first_shadow_mismatches = []
    seen = {}
    duplicates = []
    count_shadow = 0
    max_shadow_delta = 0.0
    start = time.monotonic()
    try:
        with (temp_dir / 'train_features_5_and_10.csv').open('w', newline='', encoding='utf-8') as feature_file, \
             (temp_dir / 'train_image_manifest.csv').open('w', newline='', encoding='utf-8') as manifest_file:
            feature_writer = csv.DictWriter(feature_file, fieldnames=['csv_row', 'label', *FEATURE_NAMES, *EXTRA_NAMES])
            manifest_writer = csv.DictWriter(manifest_file, fieldnames=['csv_row', 'split', 'label', 'relative_path', 'sha256'])
            feature_writer.writeheader()
            manifest_writer.writeheader()
            for idx, (image, label, relative) in enumerate(selection, 1):
                image_data = image.read_bytes()
                digest = sha256(image_data)
                if digest in seen:
                    duplicates.append({'first_row': seen[digest][0], 'duplicate_row': idx,
                                       'cross_class': seen[digest][1] != label})
                    if seen[digest][1] != label:
                        raise RuntimeError(f'Identical image bytes across classes at rows {seen[digest][0]} and {idx}; no dataset published.')
                else:
                    seen[digest] = (idx, label)
                legacy, extra = calculate(image_data)
                mismatch = stable_mismatches(legacy, rows[idx-1])
                if mismatch:
                    raise RuntimeError(f'Legacy stable-column mismatch at row {idx}: {mismatch}. No dataset published.')
                shadow_delta = abs(legacy['shadow_norm'] - float(rows[idx-1]['shadow_norm']))
                if shadow_delta > TOL:
                    count_shadow += 1
                    max_shadow_delta = max(max_shadow_delta, shadow_delta)
                    if len(first_shadow_mismatches) < 10:
                        first_shadow_mismatches.append({'row': idx, 'saved': float(rows[idx-1]['shadow_norm']),
                                                        'recomputed': legacy['shadow_norm'], 'difference': round(shadow_delta, 6)})
                feature_writer.writerow({'csv_row': idx, 'label': label, **legacy, **extra})
                manifest_writer.writerow({'csv_row': idx, 'split': 'TRAIN', 'label': label,
                                          'relative_path': relative, 'sha256': digest})
                if idx % 100 == 0:
                    print(f'Processed {idx}/5000 TRAIN images ({time.monotonic()-start:.1f}s elapsed)', flush=True)
        if sha256(SOURCE_CSV.read_bytes()) != EXPECTED_CSV_SHA256:
            raise RuntimeError('Source CSV changed during extraction; no dataset published.')
        metadata = {
            'status': 'research_only_not_validated_for_documents_or_deepfakes',
            'name': 'cifake-train-paired-five-vs-ten-feature-v0.1',
            'source_split': 'CIFAKE TRAIN only; no TEST image read',
            'samples': len(selection), 'label_counts': {'REAL_0': 2500, 'FAKE_1': 2500},
            'source_csv_sha256': EXPECTED_CSV_SHA256,
            'selection': 'sorted Path filenames; shared random.Random(20260918); sample 2500 REAL then 2500 FAKE',
            'legacy_columns': list(FEATURE_NAMES), 'new_columns': list(EXTRA_NAMES),
            'new_descriptor_version': DESCRIPTOR_VERSION,
            'legacy_source_column_verification': 'first four columns checked against archived CSV, tolerance 0.00011; fifth shadow recomputed for both models',
            'historical_shadow_difference_count': count_shadow,
            'historical_shadow_max_difference': round(max_shadow_delta, 6),
            'historical_shadow_difference_examples': first_shadow_mismatches,
            'identical_image_duplicate_pairs': duplicates,
            'identical_image_duplicate_pairs_count': len(duplicates),
            'train_validation_split': 'NOT YET ASSIGNED: group byte-hash duplicates when splitting; keep TEST separate',
            'model_training': 'NONE; production model unchanged',
            'limitations': ['CIFAKE 32x32 image domain; not identity-document or face-deepfake validation',
                            'Shadow contour orientation is not physical shadow direction',
                            'Image hashes reveal exact duplicate bytes only, not near duplicates or source contamination'],
            'environment': {'python': platform.python_version(), 'opencv': cv2.__version__,
                            'numpy': np.__version__, 'scipy': scipy.__version__, 'pillow': pillow_version},
            'code_sha256': {'stai_features.py': sha256((BACKEND/'stai_features.py').read_bytes()),
                            'expanded_forensics.py': sha256((BACKEND/'expanded_forensics.py').read_bytes())},
            'generated_file_sha256': {
                name: sha256((temp_dir / name).read_bytes())
                for name in ('train_features_5_and_10.csv', 'train_image_manifest.csv')
            },
        }
        (temp_dir / 'research_metadata.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
        if output.exists():
            raise RuntimeError('Destination appeared while processing; refusing overwrite.')
        os.replace(temp_dir, output)
        print(f'\nSUCCESS: 5000 paired TRAIN rows published: {output}', flush=True)
        print(f'Historical shadow differences: {count_shadow}; maximum={max_shadow_delta:.6f}', flush=True)
        print(f'Identical-image duplicate pairs: {len(duplicates)} (must group during split)', flush=True)
        print('CIFAKE TEST and all production models untouched. No classifier trained.', flush=True)
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--smoke', action='store_true', help='Read eight TRAIN images; write nothing')
    mode.add_argument('--full', action='store_true', help='Build separate, versioned 5000-row paired dataset')
    parser.add_argument('--dataset', type=Path, default=DEFAULT_DATASET)
    parser.add_argument('--output', type=Path, default=OUTPUT_FOLDER)
    args = parser.parse_args(argv)
    if not SOURCE_CSV.is_file():
        raise RuntimeError(f'Missing source training CSV: {SOURCE_CSV}')
    rows = load_rows(SOURCE_CSV)
    selection = reconstruct_selection(args.dataset, rows)
    smoke(selection, rows)
    if args.full:
        build(args.dataset, rows, selection, args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
