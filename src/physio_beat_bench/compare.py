"""Compare two runs of the bench record by record, for example macOS against Linux.

A row is the same detector, record set and record in both runs. Every row is classified, so the
totals always add up and nothing drops out silently:

- identical: same status and the same TP, FP and FN counts
- counts_differ: both ran (status ok), but the scores differ
- status_differ: e.g. ok on one platform, timeout or no_output on the other
- only_in_baseline / only_in_candidate: the row exists in one run only
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

KEY = ["detector", "set", "record"]
SCORES = ["tp", "fp", "fn"]
CLASSES = ["identical", "counts_differ", "status_differ", "only_in_baseline", "only_in_candidate"]


def classify(baseline: pd.DataFrame, candidate: pd.DataFrame) -> pd.DataFrame:
    columns = [*KEY, "kind", "status", *SCORES, "reproduced"]
    merged = baseline[columns].merge(
        candidate[columns], on=KEY, how="outer", suffixes=("_base", "_cand"), indicator=True
    )
    merged["kind"] = merged["kind_base"].fillna(merged["kind_cand"])

    def label(row) -> str:
        if row["_merge"] == "left_only":
            return "only_in_baseline"
        if row["_merge"] == "right_only":
            return "only_in_candidate"
        if row["status_base"] != row["status_cand"]:
            return "status_differ"
        same = all(row[f"{name}_base"] == row[f"{name}_cand"] for name in SCORES)
        return "identical" if same else "counts_differ"

    merged["outcome"] = merged.apply(label, axis=1)
    return merged.drop(columns=["_merge", "kind_base", "kind_cand"])


def by_detector(rows: pd.DataFrame) -> pd.DataFrame:
    table = rows.pivot_table(
        index=["kind", "detector"], columns="outcome", values="record", aggfunc="count",
        fill_value=0,
    )  # fmt: skip
    for name in CLASSES:
        if name not in table.columns:
            table[name] = 0
    table = table[CLASSES]
    table["rows"] = table.sum(axis=1)
    return table.reset_index().sort_values(["identical", "detector"], ascending=[True, True])


def compare_runs(baseline: Path, candidate: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare every results CSV present in both folders (entries.csv, modern.csv)."""
    frames = []
    for name in ("entries.csv", "modern.csv"):
        if (baseline / name).exists() and (candidate / name).exists():
            frames.append(classify(pd.read_csv(baseline / name), pd.read_csv(candidate / name)))
    if not frames:
        raise FileNotFoundError("no results CSV present in both folders")
    rows = pd.concat(frames, ignore_index=True)
    return rows, by_detector(rows)
