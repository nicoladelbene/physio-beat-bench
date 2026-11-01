"""The Octave shims must round-trip through the real WFDB tools."""

import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
import wfdb

from physio_beat_bench.annotations import read_beats
from physio_beat_bench.runner import COMPAT, _environment

pytestmark = pytest.mark.skipif(
    not (os.environ.get("WFDB_HOME") and shutil.which("octave")),
    reason="needs WFDB_HOME and Octave",
)


@pytest.fixture
def record(tmp_path) -> Path:
    signal = np.column_stack([np.sin(np.arange(2500) / 10), np.cos(np.arange(2500) / 10)])
    wfdb.wrsamp(
        "r1", fs=250, units=["mV", "mmHg"], sig_name=["ECG", "ABP"], p_signal=signal,
        fmt=["16", "16"], write_dir=str(tmp_path),
    )  # fmt: skip
    return tmp_path


def octave(cwd: Path, code: str) -> str:
    done = subprocess.run(
        ["octave", "--quiet", "--eval", f"addpath('{COMPAT / 'octave'}'); {code}"],
        cwd=cwd, env=_environment(cwd), capture_output=True, text=True, timeout=120,
    )  # fmt: skip
    assert done.returncode == 0, done.stderr
    return done.stdout


def test_wrann_writes_the_beats_it_was_given(record):
    octave(record, "wrann('r1', 'qrs', [101; 501; 901]);")
    assert read_beats(record / "r1.qrs").tolist() == [100, 500, 900]


def test_rdann_reads_back_one_based_positions(record):
    octave(record, "wrann('r1', 'qrs', [101; 501]); a = rdann('r1', 'qrs'); printf('%d,', a);")
    assert octave(record, "a = rdann('r1', 'qrs'); printf('%d,', a);").strip().endswith("101,501,")


def test_rdsamp_returns_signals_in_physical_units(record):
    out = octave(
        record, "[t, s, fs] = rdsamp('r1'); printf('%d %d %d', size(s, 1), size(s, 2), fs);"
    )
    assert out.split()[-3:] == ["2500", "2", "250"]


def test_wfdbdesc_reports_signal_names(record):
    out = octave(record, "s = wfdbdesc('r1'); printf('%s|%s', s(1).Description, s(2).Description);")
    assert "ECG|ABP" in out


def test_entry_call_is_narrowed_to_declared_arguments(record):
    (record / "challenge_x.m").write_text("function challenge_x(r)\n  printf('ran %s', r);\nend\n")
    assert "ran r1" in octave(record, "physio_beat_bench_call('challenge_x', 'r1', 0);")


def test_ann2rr_returns_intervals_in_samples(record):
    octave(record, "wrann('r1', 'qrs', [101; 301; 601]);")
    out = octave(record, "rr = ann2rr('r1', 'qrs'); printf('%d,', rr);")
    assert out.strip().endswith("200,300,")


def test_wrann_accepts_a_cell_annotation_type(record):
    octave(record, "wrann('r1', 'qrs', [101; 501], {'N'});")
    assert read_beats(record / "r1.qrs").tolist() == [100, 500]
