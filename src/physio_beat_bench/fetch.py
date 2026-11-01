"""Download the published Challenge archive and unpack it into the layout the bench expects.

Records and entries are never redistributed by this repository. The archive is published under
the Open Data Commons Attribution License: https://physionet.org/content/challenge-2014/1.0.0/
"""

from __future__ import annotations

import io
import shutil
import urllib.request
import zipfile
from pathlib import Path

ARCHIVE_URL = "https://physionet.org/content/challenge-2014/get-zip/1.0.0/"
RECORD_SUFFIXES = (".hea", ".dat", ".atr")


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


def fetch(data: Path, url: str = ARCHIVE_URL) -> Path:
    return assemble(download(url, data / "challenge-2014.zip"), data)
