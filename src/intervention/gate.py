"""Training and out-of-fold evaluation of the learned intervention model.

The split unit is the scenario *family* (all four matched variations stay
together), so a model is never tested on a variation of a task it trained on.
A stricter split holds out whole *templates* (task types) to test transfer to
unseen kinds of task.
"""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

from .features import FeatureBuilder
from .labels import LABELS

MODEL_SPECS = {
    # name: (use_lookups, use_text, estimator factory)
    "logreg_full": (True, True, lambda: LogisticRegression(C=2.0, max_iter=5000, class_weight="balanced")),
    "logreg_text_only": (False, True, lambda: LogisticRegression(C=2.0, max_iter=5000, class_weight="balanced")),
    "gbt_full": (True, True, lambda: HistGradientBoostingClassifier(max_depth=3, learning_rate=0.08, max_iter=200,
                                                                     class_weight="balanced", random_state=0)),
}


def fit(rows, spec="logreg_full"):
    use_lookups, use_text, make = MODEL_SPECS[spec]
    fb = FeatureBuilder(use_lookups, use_text).fit(rows)
    X = fb.transform(rows)
    y = np.array([LABELS.index(r["ground_truth_action"]) for r in rows])
    est = make()
    est.fit(X.toarray() if spec.startswith("gbt") else X, y)
    return fb, est


def predict_proba(model, rows, spec="logreg_full"):
    fb, est = model
    X = fb.transform(rows)
    P = est.predict_proba(X.toarray() if spec.startswith("gbt") else X)
    out = np.zeros((len(rows), len(LABELS)))
    out[:, est.classes_] = P
    return out


def out_of_fold(rows, spec="logreg_full", group_key="family_id", n_splits=5):
    groups = np.array([r[group_key] for r in rows])
    proba = np.zeros((len(rows), len(LABELS)))
    fold = np.zeros(len(rows), dtype=int)
    for i, (tr, te) in enumerate(GroupKFold(n_splits=n_splits).split(rows, groups=groups)):
        model = fit([rows[j] for j in tr], spec)
        proba[te] = predict_proba(model, [rows[j] for j in te], spec)
        fold[te] = i
    return proba, fold


def top_coefficients(model, k=8):
    """Most influential features per class for the logistic model."""
    fb, est = model
    names = np.array(fb.feature_names())
    out = {}
    for ci, c in enumerate(est.classes_):
        w = est.coef_[ci]
        idx = np.argsort(w)[::-1][:k]
        out[LABELS[c]] = [(names[i], round(float(w[i]), 3)) for i in idx]
    return out
