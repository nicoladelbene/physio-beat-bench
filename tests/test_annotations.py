"""Reading beats from WFDB annotation files."""

import numpy as np
import wfdb

from physio_beat_bench.annotations import read_beats, same_beats


def write(tmp_path, name, samples, symbols, aux=None):
    wfdb.wrann(
        name, "qrs", np.array(samples), symbol=symbols, fs=250, write_dir=str(tmp_path),
        aux_note=aux,
    )  # fmt: skip
    return tmp_path / f"{name}.qrs"


def test_only_beat_annotations_are_read(tmp_path):
    path = write(tmp_path, "a", [10, 20, 30], ["N", "+", "V"])
    assert read_beats(path).tolist() == [10, 30]


def test_comments_do_not_affect_beat_comparison(tmp_path):
    # gqrs embeds its command line as a comment, so byte comparison reports false differences.
    first = write(tmp_path, "a", [10, 20], ["N", "N"], aux=["run one", ""])
    second = write(tmp_path, "b", [10, 20], ["N", "N"], aux=["run two", ""])
    assert first.read_bytes() != second.read_bytes()
    assert same_beats(first, second)


def test_moved_beat_is_a_difference(tmp_path):
    assert not same_beats(
        write(tmp_path, "a", [10, 20], ["N", "N"]), write(tmp_path, "b", [10, 21], ["N", "N"])
    )
