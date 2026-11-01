"""Download the published Challenge archive and unpack it into the layout the bench expects.

Records and entries are never redistributed by this repository. The archive is published under
the Open Data Commons Attribution License: https://physionet.org/content/challenge-2014/1.0.0/
"""

from __future__ import annotations

import hashlib
import io
import shutil
import urllib.request
import zipfile
from pathlib import Path

ARCHIVE_URL = "https://physionet.org/content/challenge-2014/get-zip/1.0.0/"
RECORD_SUFFIXES = (".hea", ".dat", ".atr")
# The archive behind the published results. Not independently checked against PhysioNet's own
# checksum list, because PhysioNet's file server was failing when this was recorded.
PUBLISHED_RESULTS_SHA256 = "d96fa8fd74a04d3935b1bd8b186c88afc0a4074b29dad9d2b1ba30b68ecab352"


def _copy_records(nested: bytes, folder_marker: str, destination: Path) -> None:
    """Copy records and reference annotations only, leaving out any detector outputs."""
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(nested)) as inner:
        for member in inner.namelist():
            name = member.rsplit("/", 1)[-1]
            if folder_marker in member and (name == "RECORDS" or name.endswith(RECORD_SUFFIXES)):
                (destination / name).write_bytes(inner.read(member))


def assemble(archive: Path, data: Path) -> Path:
    data.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as outer:
        for member in outer.namelist():
            parts = member.split("/")
            if member.endswith("/octave-sample-entry.zip"):
                _copy_records(outer.read(member), "/set-p/", data / "training")
            elif member.endswith("/training.zip"):
                _copy_records(outer.read(member), "training/", data / "augmented")
            elif len(parts) == 3 and parts[1] == "sources" and parts[2]:
                target = data / "sources" / parts[2]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(outer.read(member))
            elif len(parts) == 2 and parts[1].startswith("rankings-"):
                (data / parts[1]).write_bytes(outer.read(member))
    return data


def download(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return destination
    partial = destination.with_suffix(".partial")
    with urllib.request.urlopen(url) as response, partial.open("wb") as output:
        shutil.copyfileobj(response, output)
    if not zipfile.is_zipfile(partial):  # PhysioNet can return an HTML error page with a body
        partial.unlink()
        raise RuntimeError(f"{url} did not return a zip archive; try again later")
    partial.rename(destination)
    return destination


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(data: Path, url: str = ARCHIVE_URL, archive: Path | None = None) -> dict:
    """Unpack the archive, downloading it unless a local copy is given."""
    if archive is None:
        source = download(url, data / "challenge-2014.zip")
    elif not archive.is_file():
        raise FileNotFoundError(archive)
    else:
        source = archive
    assemble(source, data)
    checksum = _sha256(source)
    return {
        "archive": str(source),
        "sha256": checksum,
        "verified_against_known_checksum": checksum == PUBLISHED_RESULTS_SHA256,
    }
