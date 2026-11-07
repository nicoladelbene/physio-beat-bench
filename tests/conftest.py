"""Shared test switches.

Tests that need the sandbox, WFDB, Octave or the downloaded data skip themselves when those are
missing. Set PHYSIO_BEAT_BENCH_REQUIRE_NATIVE=1 to turn every such skip into a failure, so a CI job
that is meant to exercise them can't pass by quietly skipping them.
"""

import os

import pytest

from physio_beat_bench.runner import SandboxUnavailable, sandbox_ready

REQUIRE_NATIVE = os.environ.get("PHYSIO_BEAT_BENCH_REQUIRE_NATIVE") == "1"


def sandbox_problem() -> str | None:
    try:
        sandbox_ready()
    except SandboxUnavailable as error:
        return str(error)
    return None


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if REQUIRE_NATIVE and report.skipped:
        report.outcome = "failed"
        report.longrepr = f"skipped, but PHYSIO_BEAT_BENCH_REQUIRE_NATIVE=1: {report.longrepr}"
