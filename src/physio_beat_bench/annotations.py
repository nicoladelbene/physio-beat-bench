"""Read beat positions from WFDB annotation files."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import wfdb

# WFDB's isqrs() annotation codes, as symbols.
BEAT_SYMBOLS = frozenset("NLRBAaJSVrFejnE/fQ?")


def read_beats(path: Path) -> np.ndarray:
    """Return the sample positions of the beat annotations in a `<record>.<annotator>` file."""
    annotation = wfdb.rdann(str(path.with_suffix("")), path.suffix.lstrip("."))
    keep = [symbol in BEAT_SYMBOLS for symbol in annotation.symbol]
    return np.asarray(annotation.sample)[keep]


def same_beats(first: Path, second: Path) -> bool:
    """True if two annotation files hold the same beat positions, ignoring comments."""
    return np.array_equal(read_beats(first), read_beats(second))
