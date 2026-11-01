"""Runner behaviour, exercised through small fake Challenge entries."""

import os
import stat
import sys
from pathlib import Path

import pytest

from physio_beat_bench.runner import RecordStatus, run_entry

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="sandbox-exec is macOS only")


def make_entry(root: Path, next_body: str, setup_body: str = "true", archived: dict | None = None):
    entry = root / "entry"
    entry.mkdir()
    for name, body in (("setup.sh", setup_body), ("next.sh", next_body)):
        script = entry / name
        script.write_text(f"#!/bin/bash\n{body}\n")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
    for record, payload in (archived or {}).items():
        target = entry / "challenge" / "2014" / "set-p" / f"{record}.qrs"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    return entry


def beats(*samples) -> bytes:
    """A minimal WFDB annotation file of normal beats."""
    import tempfile

    import numpy as np
    import wfdb

    with tempfile.TemporaryDirectory() as folder:
        wfdb.wrann(
            "x", "qrs", np.array(samples), symbol=["N"] * len(samples), fs=250, write_dir=folder
        )
        return (Path(folder) / "x.qrs").read_bytes()


def make_records(root: Path, *names: str) -> Path:
    records = root / "records"
    records.mkdir()
    for name in names:
        for suffix in ("hea", "dat", "atr"):
            (records / f"{name}.{suffix}").write_text(suffix)
    return records


def run(tmp_path, entry, records, names=("100",), **kwargs):
    return run_entry(entry, records, list(names), tmp_path / "work", **kwargs)


def test_entry_output_is_collected_and_compared_with_its_archive(tmp_path):
    (tmp_path / "output.qrs").write_bytes(beats(10, 20))
    entry = make_entry(
        tmp_path,
        f'cp "{tmp_path}/output.qrs" "$1.qrs"',
        archived={"100": beats(10, 20), "101": beats(10, 21)},
    )
    records = make_records(tmp_path, "100", "101")
    results = run(tmp_path, entry, records, ("100", "101"))
    assert [(r.record, r.status, r.reproduced) for r in results] == [
        ("100", RecordStatus.OK, True),
        ("101", RecordStatus.OK, False),
    ]


def test_reference_annotations_are_hidden_from_the_entry(tmp_path):
    entry = make_entry(tmp_path, 'if [ -e "$1.atr" ]; then exit 1; fi; printf x > "$1.qrs"')
    assert run(tmp_path, entry, make_records(tmp_path, "100"))[0].status is RecordStatus.OK


def test_entry_cannot_read_its_own_archived_answers(tmp_path):
    entry = make_entry(
        tmp_path, 'cp challenge/2014/set-p/"$1".qrs . || exit 1', archived={"100": b"answer"}
    )
    assert run(tmp_path, entry, make_records(tmp_path, "100"))[0].status is RecordStatus.NO_OUTPUT


def test_entry_cannot_write_outside_its_work_directory(tmp_path):
    outside = Path(os.path.expanduser("~")) / ".physio_beat_bench_sandbox_probe"
    entry = make_entry(tmp_path, f'touch "{outside}"; printf x > "$1.qrs"')
    run(tmp_path, entry, make_records(tmp_path, "100"))
    assert not outside.exists()


def test_entry_cannot_reach_the_network(tmp_path):
    entry = make_entry(
        tmp_path,
        "if /usr/bin/curl -s -m 5 https://physionet.org >/dev/null; then exit 1; fi; "
        'printf x > "$1.qrs"',
    )
    assert run(tmp_path, entry, make_records(tmp_path, "100"))[0].status is RecordStatus.OK


def test_hung_entry_is_stopped_and_reported(tmp_path):
    entry = make_entry(tmp_path, "sleep 30")
    results = run(tmp_path, entry, make_records(tmp_path, "100"), timeout_seconds=1)
    assert results[0].status is RecordStatus.TIMEOUT


def test_entry_without_output_is_reported_rather_than_skipped(tmp_path):
    entry = make_entry(tmp_path, "exit 0")
    assert run(tmp_path, entry, make_records(tmp_path, "100"))[0].status is RecordStatus.NO_OUTPUT


def test_entry_cannot_read_reference_labels_from_the_records_folder(tmp_path):
    records = make_records(tmp_path, "100")
    entry = make_entry(tmp_path, f'cat "{records}/$1.atr" > "$1.qrs"')
    assert run(tmp_path, entry, records)[0].status is RecordStatus.NO_OUTPUT


def test_entry_cannot_read_its_pristine_archived_answers(tmp_path):
    entry = make_entry(tmp_path, "true", archived={"100": b"answer"})
    (entry / "next.sh").write_text(
        f'#!/bin/bash\ncat "{entry}/challenge/2014/set-p/$1.qrs" > "$1.qrs"\n'
    )
    assert run(tmp_path, entry, make_records(tmp_path, "100"))[0].status is RecordStatus.NO_OUTPUT


def test_exit_code_is_recorded(tmp_path):
    entry = make_entry(tmp_path, 'printf x > "$1.qrs"; exit 3')
    assert run(tmp_path, entry, make_records(tmp_path, "100"))[0].exit_code == 3


def test_temporary_files_stay_inside_the_work_directory(tmp_path):
    entry = make_entry(tmp_path, 'touch "$TMPDIR/probe" && printf x > "$1.qrs"')
    assert run(tmp_path, entry, make_records(tmp_path, "100"))[0].status is RecordStatus.OK
    assert list((tmp_path / "work").rglob("probe"))


def test_entry_cannot_read_labels_from_another_record_set(tmp_path):
    other = tmp_path / "other-set"
    other.mkdir()
    (other / "100.atr").write_text("label")
    entry = make_entry(tmp_path, f'cat "{other}/$1.atr" > "$1.qrs"')
    assert run(tmp_path, entry, make_records(tmp_path, "100"))[0].status is RecordStatus.NO_OUTPUT


def test_entry_cannot_read_another_entrys_archived_outputs(tmp_path):
    other = tmp_path / "other-entry" / "challenge" / "2014" / "set-p"
    other.mkdir(parents=True)
    (other / "100.qrs").write_text("answer")
    entry = make_entry(tmp_path, f'cat "{other}/$1.qrs" > "$1.qrs"')
    assert run(tmp_path, entry, make_records(tmp_path, "100"))[0].status is RecordStatus.NO_OUTPUT


def test_entry_can_still_read_a_label_file_it_ships_itself(tmp_path):
    entry = make_entry(tmp_path, 'cat own.atr > "$1.qrs"')
    (entry / "own.atr").write_text("bundled")
    assert run(tmp_path, entry, make_records(tmp_path, "100"))[0].status is RecordStatus.OK


def test_entry_cannot_read_a_challenge_archive_anywhere(tmp_path):
    archive = tmp_path / "elsewhere" / "challenge-2014.zip"
    archive.parent.mkdir()
    archive.write_text("labels and archived outputs")
    entry = make_entry(tmp_path, f'cat "{archive}" > "$1.qrs"')
    assert run(tmp_path, entry, make_records(tmp_path, "100"))[0].status is RecordStatus.NO_OUTPUT


def test_setup_script_is_isolated_too(tmp_path):
    records = make_records(tmp_path, "100")
    entry = make_entry(
        tmp_path, 'cat stolen > "$1.qrs"', setup_body=f'cat "{records}/100.atr" > stolen'
    )
    assert run(tmp_path, entry, records)[0].status is RecordStatus.NO_OUTPUT


def test_symlink_inside_the_work_folder_does_not_reach_labels(tmp_path):
    records = make_records(tmp_path, "100")
    entry = make_entry(tmp_path, f'ln -s "{records}/$1.atr" link; cat link > "$1.qrs"')
    assert run(tmp_path, entry, records)[0].status is RecordStatus.NO_OUTPUT


def test_reference_labels_are_never_copied_in_for_the_entry(tmp_path):
    entry = make_entry(tmp_path, 'ls > "$1.qrs"')
    run(tmp_path, entry, make_records(tmp_path, "100"))
    assert not list((tmp_path / "work").rglob("100.atr"))
    listing = (tmp_path / "work" / "outputs" / "100.qrs").read_text()
    assert "100.hea" in listing and "100.atr" not in listing


def test_archived_outputs_stay_available_to_the_comparison_after_the_run(tmp_path):
    entry = make_entry(tmp_path, 'printf x > "$1.qrs"', archived={"100": beats(10, 20)})
    result = run(tmp_path, entry, make_records(tmp_path, "100"))[0]
    assert result.reproduced is False
