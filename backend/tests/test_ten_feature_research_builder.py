"""Pure/synthetic regression checks; do not touch the user's CIFAKE dataset."""
import importlib.util
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'experiments' / 'build_cifake_ten_features.py'
spec = importlib.util.spec_from_file_location('build_cifake_ten_features', SCRIPT)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_new_five_descriptors_are_finite_and_legacy_order_matches():
    import io
    buffer = io.BytesIO()
    Image.fromarray(np.full((32, 32, 3), 90, dtype=np.uint8)).save(buffer, format='PNG')
    old, additional = builder.calculate(buffer.getvalue())
    assert tuple(old) == builder.FEATURE_NAMES
    assert tuple(additional) == builder.EXTRA_NAMES
    assert all(np.isfinite(x) and x >= 0 for x in additional.values())
    assert all(np.isfinite(x) and 0 <= x <= 1 for x in old.values())


def test_shadow_difference_is_not_treated_as_stable_column_mismatch():
    reference = dict.fromkeys(builder.FEATURE_NAMES, '0.5')
    observed = dict.fromkeys(builder.FEATURE_NAMES, 0.5)
    observed['shadow_norm'] = 0.9
    assert builder.stable_mismatches(observed, reference) == {}
    observed['radial_norm'] = 0.6
    assert 'radial_norm' in builder.stable_mismatches(observed, reference)


def test_selection_uses_train_only_in_source_row_order(tmp_path):
    import random
    dataset = tmp_path / 'DATASET'
    for label in ('REAL', 'FAKE'):
        folder = dataset / 'TRAIN' / label
        folder.mkdir(parents=True)
        for i in range(2500):
            (folder / f'{i:05d}.jpg').touch()
    rows = [{'label': '0'} for _ in range(2500)] + [{'label': '1'} for _ in range(2500)]
    selected = builder.reconstruct_selection(dataset, rows)
    assert len(selected) == 5000
    assert selected[0][2].startswith('TRAIN/REAL/')
    assert selected[2500][2].startswith('TRAIN/FAKE/')
    expected = random.Random(20260918).sample(sorted((dataset/'TRAIN'/'REAL').iterdir()), 2500)
    assert [v[0] for v in selected[:2500]] == expected
    assert not (dataset/'test').exists()


def test_output_refuses_to_overwrite_existing_dir(tmp_path):
    with pytest.raises(RuntimeError, match='refusing to overwrite'):
        builder.build(tmp_path, [], [], tmp_path)
