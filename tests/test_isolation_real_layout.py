"""Isolation on the real data layout, with a positive control so a pass can't be vacuous."""

import shutil
import stat
from pathlib import Path

import pytest
from conftest import sandbox_problem

from physio_beat_bench.runner import RecordStatus, run_entry

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
pytestmark = pytest.mark.skipif(
    sandbox_problem() is not None or not (DATA / "training").is_dir(),
    reason="needs a working sandbox and the downloaded Challenge data",
)


def forbidden_files():
    candidates = [
        next((DATA / "training").glob("*.atr"), None),
        next((DATA / "augmented").glob("*.atr"), None),
        next((DATA / "sources").glob("*.zip"), None),
        DATA / "challenge-2014.zip",
        next((ROOT / "work" / "entries").glob("*/challenge/2014/set-p/*.qrs"), None),
    ]
    return [path for path in candidates if path is not None and path.exists()]


def attempt(tmp_path, target, record):
    entry = tmp_path / "entry"
    if entry.exists():
        shutil.rmtree(entry)
    entry.mkdir()
    for name, body in (("setup.sh", "true"), ("next.sh", f'head -c 16 "{target}" > "$1.qrs"')):
        script = entry / name
        script.write_text(f"#!/bin/bash\n{body}\n")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return run_entry(
        entry, DATA / "training", [record], tmp_path / "work", sources=DATA / "sources"
    )[0]


def test_control_the_same_probe_succeeds_on_a_permitted_file(tmp_path):
    record = next((DATA / "training").glob("*.hea")).stem
    # The entry's own copy of the record header is the one thing it should be able to read.
    assert attempt(tmp_path, f"{record}.hea", record).status is RecordStatus.OK


@pytest.mark.parametrize("index", range(5))
def test_real_labels_archives_and_archived_outputs_cannot_be_read(tmp_path, index):
    files = forbidden_files()
    if index >= len(files):
        pytest.skip("that file isn't present in this checkout")
    target = files[index]
    assert target.stat().st_size > 0  # it exists and is outside the sandbox's reach only if denied
    record = next((DATA / "training").glob("*.hea")).stem
    assert attempt(tmp_path, target, record).status is RecordStatus.NO_OUTPUT
