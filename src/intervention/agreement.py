"""Inter-annotator agreement: Cohen's kappa (two raters) and Krippendorff's
alpha for nominal data (any number of raters, missing values allowed).

Usage once annotations exist:
    python -m intervention.agreement data/annotation/annotations_filled.csv
The CSV needs columns scenario_id, annotator_1, annotator_2[, annotator_3...].
"""
from __future__ import annotations

import sys
from collections import Counter
from itertools import permutations

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score


def krippendorff_alpha_nominal(units: list[list]) -> float:
    """units: one list of ratings per item (None/NaN = missing)."""
    units = [[v for v in u if v is not None and v == v] for u in units]
    units = [u for u in units if len(u) >= 2]
    coinc = Counter()
    for u in units:
        m = len(u)
        for a, b in permutations(range(m), 2):
            coinc[(u[a], u[b])] += 1 / (m - 1)
    cats = sorted({c for pair in coinc for c in pair})
    n_c = {c: sum(v for (a, _), v in coinc.items() if a == c) for c in cats}
    n = sum(n_c.values())
    d_o = sum(v for (a, b), v in coinc.items() if a != b)
    d_e = sum(n_c[a] * n_c[b] for a in cats for b in cats if a != b) / (n - 1)
    return 1.0 - d_o / d_e if d_e else float("nan")


def report(df: pd.DataFrame) -> dict:
    cols = [c for c in df.columns if c.startswith("annotator_")]
    out = {"n_items": int(df[cols].notna().sum(axis=1).ge(2).sum()), "raters": cols}
    if len(cols) >= 2:
        both = df[cols[:2]].dropna()
        out["cohen_kappa_1v2"] = float(cohen_kappa_score(both[cols[0]], both[cols[1]]))
        out["raw_agreement_1v2"] = float((both[cols[0]] == both[cols[1]]).mean())
    out["krippendorff_alpha"] = krippendorff_alpha_nominal(df[cols].where(df[cols].notna(), None).values.tolist())
    disagreements = df[df[cols].nunique(axis=1) > 1]
    out["n_disagreements"] = int(len(disagreements))
    return out


if __name__ == "__main__":
    print(report(pd.read_csv(sys.argv[1])))
