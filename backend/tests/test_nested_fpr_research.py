"""Isolated tests for training-only nested threshold selection and reporting."""
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / 'experiments'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('evaluate_nested_fpr_research', SCRIPTS / 'evaluate_nested_fpr_research.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_wilson_upper_bounds_and_validates():
    assert module.wilson_upper(0, 100) > 0
    assert module.wilson_upper(10, 100) > 0.10
    with pytest.raises(ValueError):
        module.wilson_upper(2, 1)


def test_training_only_threshold_ties_do_not_exceed_target():
    y = np.array([0] * 200 + [1] * 200)
    real = np.array([0.1] * 170 + [0.8] * 30)
    ai = np.array([0.6] * 100 + [0.9] * 100)
    result = module.select_alert_threshold(y, np.r_[real, ai])
    assert result['inner_real_flagged'] == 0
    assert result['inner_real_fpr_wilson_upper_one_sided_95'] <= .05
    assert result['inner_ai_flagged'] == 100


def test_train_only_selector_rejects_invalid_scores():
    with pytest.raises(ValueError):
        module.select_alert_threshold(np.array([0, 1]), np.array([0.1, np.nan]))
    with pytest.raises(ValueError):
        module.select_alert_threshold(np.array([0, 1]), np.array([0.1, 1.5]))


def test_unflagged_not_called_authentic_and_outer_stats():
    result = module.alert_metrics([0, 0, 1, 1], [.1, .9, .2, .95], .8)
    assert result['real_flagged'] == 1
    assert result['ai_flagged'] == 1
    assert result['real_unflagged_unresolved'] == 1
    assert result['ai_unflagged_unresolved'] == 1
    assert result['false_flag_rate_real'] == .5


def test_inner_oof_group_separation_and_coverage():
    from sklearn.model_selection import StratifiedGroupKFold
    X = np.linspace(0, 1, 120).reshape(60, 2)
    y = np.array([0, 1] * 30)
    groups = np.arange(60)
    folds = list(StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=12).split(X, y, groups))
    class Dummy:
        classes_ = [0, 1]
        def predict_proba(self, x):
            p = np.full(len(x), .4)
            return np.c_[1-p, p]
    observed = module.inner_oof(X, y, groups, folds, 2, lambda *args: Dummy())
    assert len(observed) == 60 and np.all(observed == .4)
    bad = [(np.arange(30), np.arange(30))]
    with pytest.raises(RuntimeError):
        module.inner_oof(X, y, groups, bad, 2, lambda *args: Dummy())
