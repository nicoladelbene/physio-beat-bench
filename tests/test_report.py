"""Report rules that protect what the headline table is allowed to claim."""

import pandas as pd

from physio_beat_bench.report import paired_difference, performance_table, reproduction_tiers


def summary():
    return pd.DataFrame(
        [
            {"detector": "exact-1", "kind": "entry-2014", "reproduced_records": 100,
             "archived_records": 100, "augmented_score": 90.0, "training_ran": 100},
            {"detector": "partial-1", "kind": "entry-2014", "reproduced_records": 60,
             "archived_records": 100, "augmented_score": 99.0, "training_ran": 100},
            {"detector": "none-1", "kind": "entry-2014", "reproduced_records": 0,
             "archived_records": 100, "augmented_score": 0.0, "training_ran": 0},
            {"detector": "library", "kind": "modern", "reproduced_records": None,
             "archived_records": None, "augmented_score": 80.0, "training_ran": 100},
        ]
    )  # fmt: skip


def test_entries_that_did_not_reproduce_are_left_out_of_the_performance_table():
    assert performance_table(summary()).detector.tolist() == ["exact-1", "library"]


def test_each_entry_falls_in_exactly_one_reproduction_tier():
    assert reproduction_tiers(summary()) == {
        "exact": 1, "near": 0, "partial": 1, "did_not_run": 1, "total": 3,
    }  # fmt: skip


def per_record(detector, values):
    return pd.DataFrame(
        [
            {
                "detector": detector,
                "set": "augmented",
                "record": str(i),
                "tp": tp,
                "fp": 0,
                "fn": 10 - tp,
            }
            for i, tp in enumerate(values)
        ]
    )


def test_identical_detectors_differ_by_exactly_zero():
    frame = pd.concat([per_record("a", [9, 8, 7]), per_record("b", [9, 8, 7])])
    assert paired_difference(frame, "a", "b") == (0.0, 0.0, 0.0)


def test_better_detector_has_a_positive_difference_and_interval():
    frame = pd.concat([per_record("a", [10, 10, 10, 10]), per_record("b", [8, 7, 8, 9])])
    difference, low, high = paired_difference(frame, "a", "b")
    assert difference > 0
    assert 0 < low <= difference <= high


def test_excluded_records_are_left_out_of_the_comparison():
    frame = pd.concat([per_record("a", [10, 10]), per_record("b", [10, 0])])
    assert paired_difference(frame, "a", "b", exclude=("1",)) == (0.0, 0.0, 0.0)
