"""Run one archived Challenge entry through its setup.sh / next.sh interface.

Enforced by the sandbox for every run: no network; no reads of the records folder (and so the
reference annotations), the pristine entry or the moved archived outputs; writes only to the work
directory, the system's per-user temp folder and /dev.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from .annotations import same_beats

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPAT = REPO_ROOT / "compat"
SETUP_TIMEOUT_SECONDS = 300  # the Challenge's own limit for setup.sh
OCTAVE_PACKAGE_LIST = max(
    Path.home().glob(".config/octave/*/octave_packages"),
    key=lambda path: path.stat().st_mtime,
    default="",
)


class RecordStatus(StrEnum):
    OK = "ok"
    NO_OUTPUT = "no_output"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class RecordResult:
    record: str
    status: RecordStatus
    seconds: float
    output: Path | None
    reproduced: bool | None  # same beats as the archive; None when the archive has no output
    exit_code: int | None  # None after a timeout. Informational: 2014 entries often exit oddly


def wfdb_home() -> Path | None:
    configured = os.environ.get("WFDB_HOME")
    return Path(configured) if configured else None


def _environment(work: Path) -> dict[str, str]:
    path = [
        str(COMPAT / "bin"),
        "/opt/homebrew/bin",
        "/opt/homebrew/opt/openjdk/bin",
        "/usr/local/bin",
        "/usr/bin",
        "/bin",
    ]
    env = {
        "HOME": str(work),
        "TMPDIR": str(work / ".tmp"),
        "WFDB": ".",
        "TERM": "dumb",
        "LC_ALL": "C",
        "LANG": "C",
        "PHYSIO_BEAT_BENCH_COMPAT": str(COMPAT),
        "PHYSIO_BEAT_BENCH_PKG_LIST": str(OCTAVE_PACKAGE_LIST),
        "CC": str(COMPAT / "bin/gcc"),
        "CXX": str(COMPAT / "bin/g++"),
    }
    home = wfdb_home()
    if home:
        path.insert(1, str(home / "bin"))
        env.update(
            CPATH=str(home / "include"),
            LIBRARY_PATH=str(home / "lib"),
            DYLD_FALLBACK_LIBRARY_PATH=str(home / "lib"),
            WFDB_HOME=str(home),
        )
    env["PATH"] = ":".join(path)
    return env


def _run_sandboxed(
    script: str, args: list[str], work: Path, denied: dict[str, Path], timeout: float, log: Path
) -> int | None:
    """Run a script in the sandbox. Returns its exit code, or None if it timed out."""
    command = [
        "sandbox-exec", "-f", str(COMPAT / "sandbox.sb"),
        "-D", f"WORK={work}",
        *(item for name, path in denied.items() for item in ("-D", f"{name}={path}")),
        "bash", f"./{script}", *args,
    ]  # fmt: skip
    (work / ".tmp").mkdir(exist_ok=True)
    with log.open("ab") as output:
        process = subprocess.Popen(
            command,
            cwd=work,
            env=_environment(work),
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            return process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            return None


def _is_foreign_binary(path: Path) -> bool:
    """True for Linux-built objects, which would stop `make` rebuilding them on this machine."""
    if path.suffix == ".o":
        return True
    try:
        with path.open("rb") as handle:
            return handle.read(4) == b"\x7fELF"
    except OSError:
        return False


def _prepare(entry: Path, work: Path) -> tuple[Path, Path]:
    """Copy the entry into work/entry and move its archived outputs out of reach."""
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    entry_work = work / "entry"
    shutil.copytree(entry, entry_work, symlinks=True)
    answers = work / "archived"
    answers.mkdir()
    challenge = entry_work / "challenge"
    if challenge.exists():
        shutil.move(str(challenge), str(answers / "challenge"))
    for path in entry_work.rglob("*"):
        if path.is_file() and _is_foreign_binary(path):
            path.unlink()
    return entry_work.resolve(), answers.resolve()


def _remove_bundled_toolbox_shadows(entry_work: Path) -> None:
    """Delete the bundled 2014 toolbox wrappers, which need a Linux Java library, so shims apply."""
    shims = {path.name for path in (COMPAT / "octave").glob("*.m")}
    for path in entry_work.rglob("mcode/*.m"):
        if path.name in shims:
            path.unlink()


def _configure_octave(entry_work: Path) -> None:
    """Make Octave find the WFDB shims first and the host's signal package."""
    _remove_bundled_toolbox_shadows(entry_work)
    shims = COMPAT / "octave"
    rc = entry_work / ".octaverc"
    existing = rc.read_text() if rc.exists() else ""
    rc.write_text(existing + f"\naddpath('{shims}');\nphysio_beat_bench_startup();\n")


def _archived_output(answers: Path, record: str) -> Path | None:
    matches = list(answers.glob(f"challenge/2014/set-p/{record}.qrs"))
    return matches[0] if matches else None


def _beats_match(output: Path, archived: Path) -> bool:
    try:
        return same_beats(output, archived)
    except Exception:  # entries can write malformed annotation files
        return False


def run_entry(
    entry: Path,
    records_dir: Path,
    records: list[str],
    work: Path,
    timeout_seconds: float = 180,
    sources: Path | None = None,
) -> list[RecordResult]:
    """Build an entry once and run it on each record, blind to the reference annotations.

    `sources` is the folder of entry archives, which also hold archived outputs.
    """
    entry_work, answers = _prepare(entry, work)
    denied = {
        "ANSWERS": answers,
        "RECORDS": records_dir.resolve(),
        "PRISTINE": entry.resolve(),
        "SOURCES": (sources or entry).resolve(),
    }
    _run_sandboxed("setup.sh", [], entry_work, denied, SETUP_TIMEOUT_SECONDS, work / "setup.log")
    _configure_octave(entry_work)

    outputs = work / "outputs"
    outputs.mkdir()
    results = []
    for record in records:
        for suffix in ("hea", "dat"):
            source = records_dir / f"{record}.{suffix}"
            if source.exists():
                shutil.copy2(source, entry_work / source.name)
        produced = entry_work / f"{record}.qrs"
        started = time.monotonic()
        exit_code = _run_sandboxed(
            "next.sh", [record], entry_work, denied, timeout_seconds, work / f"next_{record}.log"
        )
        finished = exit_code is not None
        seconds = time.monotonic() - started

        output = None
        status = RecordStatus.TIMEOUT if not finished else RecordStatus.NO_OUTPUT
        if finished and produced.exists() and produced.stat().st_size > 0:
            output = outputs / produced.name
            shutil.move(str(produced), str(output))
            status = RecordStatus.OK

        archived = _archived_output(answers, record)
        identical = None
        if archived is not None:
            identical = output is not None and _beats_match(output, archived)
        results.append(RecordResult(record, status, seconds, output, identical, exit_code))

        for suffix in ("hea", "dat"):
            (entry_work / f"{record}.{suffix}").unlink(missing_ok=True)
    return results
