"""Report rules that protect what the headline table is allowed to claim."""

import pandas as pd
import pytest

from physio_beat_bench.report import (
    healthy_looking_mismatches,
    held_out_selection,
    paired_difference,
    performance_table,
    reproduction_tiers,
)


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


def test_mismatches_with_healthy_scores_are_counted():
    rows = [
        {"kind": "entry-2014", "reproduced_records": 60, "archived_records": 100,
         "training_score": 99.5},
        {"kind": "entry-2014", "reproduced_records": 60, "archived_records": 100,
         "training_score": 40.0},
        {"kind": "entry-2014", "reproduced_records": 100, "archived_records": 100,
         "training_score": 99.5},
    ]  # fmt: skip
    assert healthy_looking_mismatches(pd.DataFrame(rows)) == 1


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


def _records(detector, values, set_name="augmented"):
    return [
        {"detector": detector, "set": set_name, "record": str(i), "tp": tp, "fp": 0, "fn": 10 - tp}
        for i, tp in enumerate(values)
    ]


def test_selection_is_judged_only_on_records_it_did_not_see():
    # Half the records favour one method, half the other, so a chooser that sees only one half
    # must pick wrongly for the other half and gain nothing, however good its best half looked.
    half = 20
    frame = pd.DataFrame(
        _records("first", [10] * half + [5] * half) + _records("second", [5] * half + [10] * half)
    )
    result = held_out_selection(frame, ["first", "second"], baseline="second", splits=200)
    assert result["held_out_gain"] <= 0


def test_a_truly_better_method_keeps_its_gain_out_of_sample():
    frame = pd.DataFrame(_records("good", [10] * 40) + _records("poor", [5] * 40))
    result = held_out_selection(frame, ["good", "poor"], baseline="poor", splits=50)
    # good scores 100; poor has Se 50 and +P 100, so (50 + 100 + 50 + 100) / 4 = 75.
    assert result["held_out_gain"] == pytest.approx(25.0)
    assert result["selected_share"]["good"] == 1.0


def test_held_out_selection_can_exclude_records():
    frame = pd.DataFrame(_records("a", [10] * 10) + _records("b", [10] * 10))
    result = held_out_selection(frame, ["a", "b"], baseline="b", splits=5, exclude=("0", "1"))
    assert result["records"] == 8


def test_adjusted_interval_is_wider_and_contains_the_plain_one():
    frame = pd.DataFrame(
        _records("a", [10, 9, 8, 10, 7, 9, 10, 6] * 5)
        + _records("b", [9, 10, 7, 8, 9, 5, 8, 7] * 5)
    )
    _, low, high = paired_difference(frame, "a", "b")
    _, adjusted_low, adjusted_high = paired_difference(frame, "a", "b", confidence=1 - 0.05 / 9)
    assert adjusted_low <= low and adjusted_high >= high
