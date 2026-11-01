"""Failures must not be recorded as a detector's poor performance."""

import csv
import zipfile

import pytest

from physio_beat_bench.bench import Layout, extract_entry, run_entries, score_output


def test_missing_scorer_is_an_error_rather_than_a_zero_score(tmp_path, monkeypatch):
    monkeypatch.setenv("WFDB_HOME", str(tmp_path / "nowhere"))
    output = tmp_path / "1.qrs"
    output.write_bytes(b"x")
    (tmp_path / "1.hea").write_text("1 1 250 100\n1.dat 16 200 12 0 0 0 0 ECG\n")
    (tmp_path / "1.atr").write_bytes(b"\x00\x00")
    layout = Layout(tmp_path.parent)
    with pytest.raises(FileNotFoundError):
        score_output(output, layout, tmp_path.name, "1")


def test_interrupted_extraction_is_not_reused(tmp_path):
    archive = tmp_path / "entry.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("setup.sh", "true")
    destination = tmp_path / "entries" / "entry"
    (destination.parent / f"{destination.name}.partial").mkdir(parents=True)
    extract_entry(archive, destination)
    assert (destination / "setup.sh").exists()


def test_failed_rerun_keeps_the_entrys_previous_results(tmp_path, monkeypatch):
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources" / "a-1.zip").write_bytes(b"x")
    out = tmp_path / "entries.csv"
    out.write_text("detector,kind\na-1,entry-2014\n")

    class Broken:
        def __init__(self, *args):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def submit(self, *args):
            from concurrent.futures import Future

            future = Future()
            future.set_exception(RuntimeError("boom"))
            return future

    monkeypatch.setattr("physio_beat_bench.bench.ProcessPoolExecutor", Broken)
    run_entries(Layout(tmp_path), tmp_path / "work", out, 1, 1, only=["a-1"])
    with out.open() as handle:
        assert [row["detector"] for row in csv.DictReader(handle)] == ["a-1"]


def test_detector_finding_no_beats_scores_zero_and_is_not_counted_as_running(tmp_path, monkeypatch):
    import numpy as np
    import wfdb

    from physio_beat_bench.bench import _modern_record

    records = tmp_path / "set"
    records.mkdir()
    wfdb.wrsamp(
        "1", fs=250, units=["mV"], sig_name=["ECG"], p_signal=np.zeros((1000, 1)) + 0.1,
        fmt=["16"], write_dir=str(records),
    )  # fmt: skip
    wfdb.wrann(
        "1", "atr", np.array([100, 500, 900]), symbol=["N"] * 3, fs=250, write_dir=str(records)
    )
    monkeypatch.setattr("physio_beat_bench.bench.detect_modern", lambda *args: [])
    row = _modern_record("flat", Layout(tmp_path), "set", "1")
    assert (row["status"], row["tp"], row["fp"], row["fn"]) == ("no_output", 0, 1, 3)
