"""Assembling the expected data layout from the published Challenge archive."""

import io
import zipfile

import pytest

from physio_beat_bench.fetch import assemble, fetch


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


def test_local_archive_is_unpacked_without_downloading(tmp_path, monkeypatch):
    archive = tmp_path / "local.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("root/sources/a-1.zip", b"entry")

    def no_network(*args, **kwargs):
        raise AssertionError("must not touch the network")

    monkeypatch.setattr("urllib.request.urlopen", no_network)
    report = fetch(tmp_path / "data", archive=archive)
    assert (tmp_path / "data" / "sources" / "a-1.zip").read_bytes() == b"entry"
    assert report["verified_against_known_checksum"] is False


def test_missing_local_archive_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        fetch(tmp_path / "data", archive=tmp_path / "nope.zip")


def test_checksum_of_the_archive_used_for_published_results_is_recognised(tmp_path, monkeypatch):
    archive = tmp_path / "local.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("root/sources/a-1.zip", b"entry")
    import hashlib

    monkeypatch.setattr(
        "physio_beat_bench.fetch.PUBLISHED_RESULTS_SHA256",
        hashlib.sha256(archive.read_bytes()).hexdigest(),
    )
    assert fetch(tmp_path / "data", archive=archive)["verified_against_known_checksum"] is True
