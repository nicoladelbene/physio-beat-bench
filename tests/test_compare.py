"""Run-to-run comparison, on small hand-made results tables."""

import pandas as pd

from physio_beat_bench.compare import by_detector, classify


def table(rows):
    columns = ["detector", "kind", "set", "record", "status", "tp", "fp", "fn", "reproduced"]
    return pd.DataFrame(rows, columns=columns)


BASE = table([
    ("a", "entry-2014", "training", "100", "ok", 10, 0, 1, 1),
    ("a", "entry-2014", "training", "101", "ok", 10, 0, 1, 1),
    ("a", "entry-2014", "training", "102", "ok", 10, 0, 1, 1),
    ("b", "entry-2014", "training", "100", "ok", 5, 5, 5, 0),
])  # fmt: skip
CAND = table([
    ("a", "entry-2014", "training", "100", "ok", 10, 0, 1, 1),
    ("a", "entry-2014", "training", "101", "ok", 10, 1, 1, 0),
    ("a", "entry-2014", "training", "102", "timeout", 0, 1, 11, 0),
    ("c", "entry-2014", "training", "100", "ok", 1, 1, 1, 0),
])  # fmt: skip


def outcomes(rows):
    keys = rows["detector"] + "/" + rows["record"].astype(str)
    return dict(zip(keys, rows["outcome"], strict=True))


def test_each_row_gets_exactly_one_outcome():
    assert outcomes(classify(BASE, CAND)) == {
        "a/100": "identical",
        "a/101": "counts_differ",
        "a/102": "status_differ",
        "b/100": "only_in_baseline",
        "c/100": "only_in_candidate",
    }


def test_per_detector_totals_add_up_to_every_row():
    detectors = by_detector(classify(BASE, CAND)).set_index("detector")
    assert detectors.loc["a", ["identical", "counts_differ", "status_differ"]].tolist() == [1, 1, 1]
    assert detectors["rows"].sum() == 5
