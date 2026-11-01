"""PhysioNet/CinC Challenge 2014 scoring.

Beat matching uses WFDB's `bxb -f 0`, the Challenge's official tool. The overall score is the
equal-weight mean of gross and per-record sensitivity and positive predictivity.
Rules: https://moody-challenge.physionet.org/2014/
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Counts:
    """Beat-matching outcome for one record."""

    tp: int
    fp: int
    fn: int


@dataclass(frozen=True)
class ChallengeScore:
    """All values are percentages."""

    gross_se: float
    gross_ppv: float
    mean_se: float
    mean_ppv: float

    @property
    def score(self) -> float:
        return (self.gross_se + self.gross_ppv + self.mean_se + self.mean_ppv) / 4


def bxb_counts(record: Path, detections: Path) -> Counts:
    """Score a detection file against `<record>.atr` with bxb. Raises if bxb rejects the file."""
    bxb = Path(os.environ["WFDB_HOME"]) / "bin" / "bxb"
    name = record.name
    with tempfile.TemporaryDirectory() as folder:
        work = Path(folder)
        shutil.copy2(record.with_name(f"{name}.hea"), work)
        shutil.copy2(record.with_name(f"{name}.atr"), work)
        shutil.copy2(detections, work / f"{name}.qrs")
        subprocess.run(
            [bxb, "-r", name, "-a", "atr", "qrs", "-f", "0", "-L", "line.txt", "/dev/null"],
            cwd=work, check=True, capture_output=True, env={"WFDB": ".", "PATH": "/usr/bin:/bin"},
        )  # fmt: skip
        # Columns: Nn Sn Vn Fn On Ns Ss Vs Fs Os Nv Sv Vv Fv Ov No So Vo Fo
        fields = (work / "line.txt").read_text().splitlines()[-1].split()
    v = [int(x) for x in fields[1:20]]
    tp = sum(v[0:4]) + sum(v[5:9]) + sum(v[10:14])
    return Counts(tp=tp, fp=v[4] + v[9] + v[14], fn=sum(v[15:19]))


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def challenge_score(records: Iterable[Counts]) -> ChallengeScore:
    """Combine per-record counts into the Challenge's four statistics."""
    counts = list(records)
    if not counts:
        raise ValueError("challenge_score needs at least one record")
    tp = sum(c.tp for c in counts)
    fp = sum(c.fp for c in counts)
    fn = sum(c.fn for c in counts)
    return ChallengeScore(
        gross_se=100 * _ratio(tp, tp + fn),
        gross_ppv=100 * _ratio(tp, tp + fp),
        mean_se=100 * float(np.mean([_ratio(c.tp, c.tp + c.fn) for c in counts])),
        mean_ppv=100 * float(np.mean([_ratio(c.tp, c.tp + c.fp) for c in counts])),
    )
