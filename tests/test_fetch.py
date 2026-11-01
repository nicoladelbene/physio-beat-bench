"""Assembling the expected data layout from the published Challenge archive."""

import io
import zipfile

from physio_beat_bench.fetch import assemble


def build_archive(path):
    template = io.BytesIO()
    with zipfile.ZipFile(template, "w") as inner:
        inner.writestr("entry/challenge/2014/set-p/RECORDS", "100\n")
        inner.writestr("entry/challenge/2014/set-p/100.hea", "header")
        inner.writestr("entry/challenge/2014/set-p/100.qrs", "someone else's detections")
    training = io.BytesIO()
    with zipfile.ZipFile(training, "w") as inner:
        inner.writestr("training/RECORDS", "1003\n")
        inner.writestr("training/1003.hea", "header")
    with zipfile.ZipFile(path, "w") as outer:
        outer.writestr("root/octave-sample-entry.zip", template.getvalue())
        outer.writestr("root/training.zip", training.getvalue())
        outer.writestr("root/sources/entry-1.zip", b"zip")
        outer.writestr("root/rankings-20150413", "someone 90.0\n")


def test_archive_is_unpacked_into_the_expected_layout(tmp_path):
    archive = tmp_path / "challenge.zip"
    build_archive(archive)
    data = assemble(archive, tmp_path / "data")
    assert (data / "training/100.hea").exists()
    assert (data / "augmented/1003.hea").exists()
    assert (data / "sources/entry-1.zip").exists()
    assert (data / "rankings-20150413").exists()


def test_sample_entry_outputs_do_not_enter_the_record_folders(tmp_path):
    archive = tmp_path / "challenge.zip"
    build_archive(archive)
    data = assemble(archive, tmp_path / "data")
    assert not (data / "training/100.qrs").exists()
