"""Scoring behaviour, specified from the public Challenge 2014 rules.

Expected values are hand-worked from the rules, not recomputed the way the code does it.
"""

import os

import numpy as np
import pytest
import wfdb

from physio_beat_bench.scoring import Counts, bxb_counts, challenge_score

FS = 100  # 1 sample = 10 ms, so the 150 ms window is 15 samples


@pytest.fixture
def record(tmp_path):
    if not os.environ.get("WFDB_HOME"):
        pytest.skip("needs WFDB_HOME")
    wfdb.wrsamp(
        "r1", fs=FS, units=["mV"], sig_name=["ECG"], p_signal=np.zeros((5000, 1)),
        fmt=["16"], write_dir=str(tmp_path),
    )  # fmt: skip
    wfdb.wrann(
        "r1", "atr", np.array([1000, 2000]), symbol=["N", "N"], fs=FS, write_dir=str(tmp_path)
    )
    return tmp_path / "r1"


def detections(record, samples):
    wfdb.wrann(
        "r1", "qrs", np.array(samples), symbol=["N"] * len(samples), fs=FS,
        write_dir=str(record.parent),
    )  # fmt: skip
    return record.with_suffix(".qrs")


def test_detection_inside_the_window_is_a_true_positive(record):
    assert bxb_counts(record, detections(record, [1010, 1990])) == Counts(tp=2, fp=0, fn=0)


def test_detection_outside_the_window_is_a_miss_and_a_false_alarm(record):
    assert bxb_counts(record, detections(record, [1040, 2000])) == Counts(tp=1, fp=1, fn=1)


def test_missing_detections_count_as_misses(record):
    assert bxb_counts(record, detections(record, [1000])) == Counts(tp=1, fp=0, fn=1)


def test_score_averages_gross_and_per_record_statistics_equally():
    # Record A: 90 TP, 10 FP, 0 FN. Record B: 10 TP, 0 FP, 90 FN.
    # gross Se = 100/190, gross +P = 100/110, mean Se = (1 + .1)/2, mean +P = (.9 + 1)/2
    s = challenge_score([Counts(90, 10, 0), Counts(10, 0, 90)])
    assert s.gross_se == pytest.approx(52.6316, abs=1e-3)
    assert s.gross_ppv == pytest.approx(90.9091, abs=1e-3)
    assert s.mean_se == pytest.approx(55.0)
    assert s.mean_ppv == pytest.approx(95.0)
    assert s.score == pytest.approx(73.3852, abs=1e-3)


def test_failed_record_counts_as_zero_sensitivity_and_predictivity():
    # Challenge rule: no output scores zero Se and +P for that record, not "skipped".
    s = challenge_score([Counts(100, 0, 0), Counts(0, 1, 100)])
    assert s.mean_se == pytest.approx(50.0)
    assert s.mean_ppv == pytest.approx(50.0)
