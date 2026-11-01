"""Turn per-record results into summary tables with record-level uncertainty."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .scoring import Counts, challenge_score


def score_counts(frame: pd.DataFrame, columns=("tp", "fp", "fn")) -> float:
    a, b, c = columns
    return challenge_score(
        Counts(int(x), int(y), int(z)) for x, y, z in zip(frame[a], frame[b], frame[c])
    ).score


def bootstrap_ci(
    frame: pd.DataFrame, iterations: int = 2000, seed: int = 2014
) -> tuple[float, float]:
    """95% percentile interval, resampling whole records."""
    rng = np.random.default_rng(seed)
    tp, fp, fn = (frame[c].to_numpy(dtype=float) for c in ("tp", "fp", "fn"))
    n = len(frame)
    picks = rng.integers(0, n, size=(iterations, n))
    t, f, m = tp[picks], fp[picks], fn[picks]
    with np.errstate(divide="ignore", invalid="ignore"):
        gross_se = t.sum(1) / (t.sum(1) + m.sum(1))
        gross_ppv = t.sum(1) / (t.sum(1) + f.sum(1))
        mean_se = np.nan_to_num(t / (t + m)).mean(1)
        mean_ppv = np.nan_to_num(t / (t + f)).mean(1)
    scores = 100 * (gross_se + gross_ppv + mean_se + mean_ppv) / 4
    low, high = np.percentile(scores, [2.5, 97.5])
    return float(low), float(high)


def summarise(results: pd.DataFrame) -> pd.DataFrame:
    """One row per detector with score, interval and reproduction status for each set."""
    rows = []
    for detector, group in results.groupby("detector"):
        row = {"detector": detector, "kind": group["kind"].iloc[0]}
        for set_name, subset in group.groupby("set"):
            low, high = bootstrap_ci(subset)
            row[f"{set_name}_score"] = round(score_counts(subset), 2)
            row[f"{set_name}_low"] = round(low, 2)
            row[f"{set_name}_high"] = round(high, 2)
            row[f"{set_name}_ran"] = int((subset["status"] == "ok").sum())
            row[f"{set_name}_records"] = len(subset)
            if set_name == "training":
                archived = subset.dropna(subset=["archived_tp"])
                if len(archived):
                    row["archived_training_score"] = round(
                        score_counts(archived, ("archived_tp", "archived_fp", "archived_fn")), 2
                    )
                    row["reproduced_records"] = int(archived["reproduced"].fillna(0).sum())
                    row["archived_records"] = len(archived)
        rows.append(row)
    return pd.DataFrame(rows).sort_values("augmented_score", ascending=False)
