"""Turn per-record results into summary tables with record-level uncertainty."""

from __future__ import annotations

from pathlib import Path

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


def performance_table(summary: pd.DataFrame) -> pd.DataFrame:
    """Entries with exact reproduction, plus modern detectors.

    A score from an entry that did not reproduce is a score of our revival, not of the entry.
    """
    entries = summary["kind"] == "entry-2014"
    exact = summary["reproduced_records"] == summary["archived_records"]
    table = summary[~entries | exact]
    return table.sort_values("augmented_score", ascending=False)


def reproduction_tiers(summary: pd.DataFrame) -> dict[str, int]:
    """exact: every record. near: at least 95. partial: runs but differs. did_not_run: no output."""
    entries = summary[summary["kind"] == "entry-2014"]
    fraction = entries["reproduced_records"] / entries["archived_records"]
    ran = entries["training_ran"] > 0
    exact = int((fraction == 1).sum())
    near = int(((fraction >= 0.95) & (fraction < 1)).sum())
    did_not_run = int((~ran).sum())
    return {
        "exact": exact,
        "near": near,
        "partial": len(entries) - exact - near - did_not_run,
        "did_not_run": did_not_run,
        "total": len(entries),
    }


def add_official_scores(summary: pd.DataFrame, rankings: Path) -> pd.DataFrame:
    """Attach each entry's official hidden-test score from the published 2015 rankings."""
    official = {}
    for line in rankings.read_text().splitlines():
        parts = line.split()
        if len(parts) >= 2:
            official[" ".join(parts[:-1])] = float(parts[-1])
    names = summary["detector"].str.replace(r"-\d+$", "", regex=True)
    return summary.assign(official_hidden_score=names.map(official))


def figure(summary: pd.DataFrame, path: Path) -> None:
    """Dot-and-interval chart of the performance table on the augmented set."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    surface, ink, muted, grid = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e0"
    entry_color, modern_color = "#2a78d6", "#eb6834"
    table = performance_table(summary).iloc[::-1]
    table = table[table["augmented_ran"] >= 90]
    y = np.arange(len(table))

    fig, ax = plt.subplots(figsize=(9, 0.34 * len(table) + 2.0), dpi=200)
    fig.patch.set_facecolor(surface)
    ax.set_facecolor(surface)
    for position, (_, row) in zip(y, table.iterrows(), strict=True):
        color = entry_color if row["kind"] == "entry-2014" else modern_color
        ax.plot(
            [row["augmented_low"], row["augmented_high"]], [position, position],
            color=color, lw=2, solid_capstyle="round", zorder=2,
        )  # fmt: skip
        ax.scatter(row["augmented_score"], position, s=52, color=color, zorder=3,
                   edgecolor=surface, linewidth=1.2)  # fmt: skip
        if pd.notna(row.get("official_hidden_score")):
            ax.scatter(row["official_hidden_score"], position, s=38, marker="D",
                       facecolor=surface, edgecolor=ink, linewidth=1.1, zorder=4)  # fmt: skip

    ax.set_yticks(y, table["detector"].str.replace(r"-\d+$", "", regex=True), color=ink, fontsize=9)
    ax.set_xlabel("Challenge score on the 100-record augmented set (higher is better)",
                  color=muted, fontsize=9)  # fmt: skip
    ax.tick_params(axis="x", colors=muted, labelsize=9, length=0)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=grid, lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    handles = [
        plt.Line2D([], [], color=entry_color, marker="o", lw=2,
                   label="2014 entry, reproduces its archive exactly, re-run in 2026"),
        plt.Line2D([], [], color=modern_color, marker="o", lw=2,
                   label="Current library, default settings, one ECG channel"),
        plt.Line2D([], [], color=ink, marker="D", lw=0, markerfacecolor=surface,
                   label="Same entry's official score on the hidden test set (2015)"),
    ]  # fmt: skip
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(-0.02, 1.0), frameon=False,
              fontsize=8.5, labelcolor=muted)  # fmt: skip
    fig.text(0.01, 0.005, "Lines: 95% bootstrap interval over records. Some entries were developed "
             "with this set available, so their scores here may be optimistic.",
             color=muted, fontsize=7.5)  # fmt: skip
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=surface)
    plt.close(fig)
