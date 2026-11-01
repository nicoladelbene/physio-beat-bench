"""Modern detectors are ECG-only, so channel selection must not mistake other signals for ECG."""

import numpy as np
import pytest

from physio_beat_bench.bench import NoEcgChannelError, first_ecg_channel


def channels(*names):
    return list(names), np.arange(len(names) * 4, dtype=float).reshape(4, len(names))


@pytest.mark.parametrize(
    ("names", "expected"),
    [(("ABP", "ECG"), 1), (("II", "V"), 0), (("ICP", "AVF"), 1), (("RESP", "MLII"), 1)],
)
def test_first_ecg_like_channel_is_selected(names, expected):
    labels, signal = channels(*names)
    assert first_ecg_channel(labels, signal).tolist() == signal[:, expected].tolist()


def test_record_without_ecg_is_an_error_rather_than_a_guess():
    labels, signal = channels("ABP", "ICP", "RESP", "EEG")
    with pytest.raises(NoEcgChannelError):
        first_ecg_channel(labels, signal)
