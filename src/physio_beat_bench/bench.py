"""Run entries and modern detectors over the record sets and write per-record results."""

from __future__ import annotations

import csv
import re
import shutil
import tarfile
import tempfile
import time
import warnings
import zipfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import wfdb

from .annotations import read_beats
from .runner import RecordResult, run_entry
from .scoring import Counts, bxb_counts

SETS = ("training", "augmented")
FIELDS = [
    "detector", "kind", "set", "record", "status", "seconds", "reproduced",
    "tp", "fp", "fn", "archived_tp", "archived_fp", "archived_fn",
]  # fmt: skip


@dataclass(frozen=True)
class Layout:
    """Where downloaded data lives."""

    data: Path

    @property
    def sources(self) -> Path:
        return self.data / "sources"

    def records(self, set_name: str) -> Path:
        return self.data / set_name

    def record_names(self, set_name: str) -> list[str]:
        return (self.records(set_name) / "RECORDS").read_text().split()


def extract_entry(archive: Path, destination: Path) -> Path:
    """Unpack one entry archive into its own directory; path traversal is rejected."""
    if destination.exists():
        return destination
    destination.mkdir(parents=True)
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as handle:
            handle.extractall(destination)
    else:
        with tarfile.open(archive) as handle:
            handle.extractall(destination, filter="data")
    return destination


def entry_name(archive: Path) -> str:
    return archive.name.removesuffix(".zip").removesuffix(".tar.gz")


def discover_entries(layout: Layout) -> list[Path]:
    # The toolbox archive also lives under sources/ in some copies, but is not an entry.
    return sorted(
        path
        for path in layout.sources.iterdir()
        if path.name.endswith((".zip", ".tar.gz")) and not path.name.startswith("wfdb-app")
    )


def _reference_size(layout: Layout, set_name: str, record: str) -> int:
    return len(read_beats((layout.records(set_name) / record).with_suffix(".atr")))


def score_output(output: Path | None, layout: Layout, set_name: str, record: str) -> Counts:
    """Score one output. A missing or malformed output scores zero, as in the Challenge."""
    if output is not None:
        try:
            return bxb_counts(layout.records(set_name) / record, output)
        except Exception:  # noqa: BLE001 - entries can write anything; bxb's rejection is the signal
            pass
    return Counts(tp=0, fp=1, fn=_reference_size(layout, set_name, record))


def _row(detector, kind, set_name, record, status, seconds, reproduced, counts, archived=None):
    return {
        "detector": detector,
        "kind": kind,
        "set": set_name,
        "record": record,
        "status": status,
        "seconds": round(seconds, 2),
        "reproduced": "" if reproduced is None else int(reproduced),
        "tp": counts.tp,
        "fp": counts.fp,
        "fn": counts.fn,
        "archived_tp": "" if archived is None else archived.tp,
        "archived_fp": "" if archived is None else archived.fp,
        "archived_fn": "" if archived is None else archived.fn,
    }


def run_one_entry(archive: Path, layout: Layout, work: Path, timeout: float) -> list[dict]:
    name = entry_name(archive)
    entry = extract_entry(archive, work / "entries" / name)
    rows = []
    for set_name in SETS:
        records = layout.record_names(set_name)
        results: list[RecordResult] = run_entry(
            entry, layout.records(set_name), records, work / "runs" / name / set_name, timeout
        )
        archive_dir = work / "runs" / name / set_name / "archived/challenge/2014/set-p"
        for result in results:
            archived_file = archive_dir / f"{result.record}.qrs"
            archived = (
                score_output(archived_file, layout, set_name, result.record)
                if archived_file.exists()
                else None
            )
            rows.append(
                _row(
                    name, "entry-2014", set_name, result.record, result.status.value,
                    result.seconds, result.reproduced,
                    score_output(result.output, layout, set_name, result.record), archived,
                )
            )  # fmt: skip
        shutil.rmtree(work / "runs" / name / set_name / "entry", ignore_errors=True)
    return rows


def write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda r: (r["detector"], r["set"], r["record"]))
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def run_entries(
    layout: Layout, work: Path, out: Path, jobs: int, timeout: float, only: list[str] | None = None
) -> None:
    archives = [a for a in discover_entries(layout) if not only or entry_name(a) in only]
    rows: list[dict] = []
    if only and out.exists():  # a partial re-run keeps every other entry's results
        with out.open(newline="") as handle:
            rows = [row for row in csv.DictReader(handle) if row["detector"] not in only]
    with ProcessPoolExecutor(jobs) as pool:
        futures = {pool.submit(run_one_entry, a, layout, work, timeout): a for a in archives}
        for future in as_completed(futures):
            name = entry_name(futures[future])
            try:
                rows.extend(future.result())
                write_rows(out, rows)
                print(f"done {name}", flush=True)
            except Exception as error:  # one broken entry must not stop the rest
                print(f"FAILED {name}: {error!r}", flush=True)


ECG_LABEL = re.compile(r"^(ECG.*|EKG.*|I{1,3}|MLI{1,3}|AV[RLF]|V\d?)$", re.IGNORECASE)


class NoEcgChannelError(ValueError):
    """The record has no ECG, so an ECG-only detector cannot run on it."""


def first_ecg_channel(labels: list[str], signal: np.ndarray) -> np.ndarray:
    for index, label in enumerate(labels):
        if ECG_LABEL.match(label.strip()):
            return np.nan_to_num(signal[:, index])
    raise NoEcgChannelError(str(labels))


def detect_modern(detector: str, ecg: np.ndarray, fs: float) -> np.ndarray:
    """Each library's documented pipeline at default settings, on one ECG channel."""
    if detector == "wfdb-xqrs":
        import wfdb.processing

        return wfdb.processing.xqrs_detect(ecg, fs, verbose=False)
    import neurokit2 as nk

    method = detector.removeprefix("neurokit2-")
    # ecg_clean has no rodrigues2021 method; NeuroKit2's default cleaning applies to it.
    clean_method = "neurokit" if method == "rodrigues2021" else method
    cleaned = nk.ecg_clean(ecg, sampling_rate=int(fs), method=clean_method)
    _, info = nk.ecg_peaks(cleaned, sampling_rate=int(fs), method=method)
    return np.asarray(info["ECG_R_Peaks"])


def _modern_record(detector: str, layout: Layout, set_name: str, record: str) -> dict:
    base = layout.records(set_name) / record
    fs = float(wfdb.rdheader(str(base)).fs)
    started = time.monotonic()
    status = "ok"
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            signal = wfdb.rdrecord(str(base))
            detections = detect_modern(
                detector, first_ecg_channel(signal.sig_name, signal.p_signal), fs
            )
        beats = np.unique(np.asarray(detections, dtype=int))
        beats = beats[(beats > 0) & (beats < signal.sig_len)]
        with tempfile.TemporaryDirectory() as folder:
            wfdb.wrann(record, "qrs", beats, symbol=["N"] * len(beats), fs=fs, write_dir=folder)
            counts = bxb_counts(base, Path(folder) / f"{record}.qrs")
    except Exception:  # noqa: BLE001 - a crashing detector scores zero on that record
        status = "crash"
        counts = Counts(tp=0, fp=1, fn=_reference_size(layout, set_name, record))
    return _row(detector, "modern", set_name, record, status, time.monotonic() - started, None,
                counts)  # fmt: skip


MODERN = (
    "wfdb-xqrs", "neurokit2-neurokit", "neurokit2-pantompkins1985", "neurokit2-hamilton2002",
    "neurokit2-elgendi2010", "neurokit2-engzeemod2012", "neurokit2-rodrigues2021",
)  # fmt: skip


def run_modern(layout: Layout, out: Path, jobs: int) -> None:
    tasks = [
        (detector, layout, set_name, record)
        for detector in MODERN
        for set_name in SETS
        for record in layout.record_names(set_name)
    ]
    with ProcessPoolExecutor(jobs) as pool:
        rows = list(pool.map(_modern_record, *zip(*tasks), chunksize=8))
    write_rows(out, rows)
