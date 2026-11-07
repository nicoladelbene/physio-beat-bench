"""The Linux sandbox command, checked on any platform: what bubblewrap is told to make visible."""

from pathlib import Path

import pytest

from physio_beat_bench import runner


@pytest.fixture
def linux(monkeypatch):
    monkeypatch.setattr(runner.sys, "platform", "linux")
    monkeypatch.setattr(runner.shutil, "which", lambda name: f"/usr/bin/{name}")


def mounted(command: list[str]) -> list[Path]:
    """Every host path bound into the sandbox, read-only or writable."""
    paths = []
    for flag, source in zip(command, command[1:], strict=False):
        if flag in ("--bind", "--ro-bind"):
            paths.append(Path(source))
    return paths


def denied_paths(tmp_path: Path) -> dict[str, Path]:
    return {name: tmp_path / name.lower() for name in ("ANSWERS", "RECORDS", "PRISTINE", "SOURCES")}


def test_no_denied_path_is_mounted(linux, tmp_path):
    work = tmp_path / "work" / "entry"
    command = runner._sandbox_command(work, denied_paths(tmp_path))
    for path in mounted(command):
        for hidden in denied_paths(tmp_path).values():
            assert not hidden.is_relative_to(path), (hidden, path)


def test_only_the_work_directory_is_writable(linux, tmp_path):
    work = tmp_path / "work" / "entry"
    command = runner._sandbox_command(work, denied_paths(tmp_path))
    writable = [Path(s) for f, s in zip(command, command[1:], strict=False) if f == "--bind"]
    assert writable == [work]


def test_network_and_other_namespaces_are_unshared(linux, tmp_path):
    command = runner._sandbox_command(tmp_path / "w", denied_paths(tmp_path))
    assert "--unshare-all" in command and "--share-net" not in command
    assert "--die-with-parent" in command


def test_user_home_is_not_mounted(linux, tmp_path):
    command = runner._sandbox_command(tmp_path / "w", denied_paths(tmp_path))
    assert Path.home() not in mounted(command)


def test_refuses_when_a_denied_path_sits_inside_the_work_directory(linux, tmp_path):
    work = tmp_path / "work"
    denied = denied_paths(tmp_path) | {"RECORDS": work / "records"}
    with pytest.raises(runner.SandboxUnavailable, match="RECORDS"):
        runner._sandbox_command(work, denied)


def test_refuses_when_a_denied_path_sits_inside_the_wfdb_tools(linux, tmp_path, monkeypatch):
    monkeypatch.setenv("WFDB_HOME", str(tmp_path / "data"))
    denied = denied_paths(tmp_path) | {"RECORDS": tmp_path / "data" / "training"}
    with pytest.raises(runner.SandboxUnavailable, match="RECORDS"):
        runner._sandbox_command(tmp_path / "w", denied)


def test_missing_bubblewrap_is_an_error_not_a_silent_run(monkeypatch, tmp_path):
    monkeypatch.setattr(runner.sys, "platform", "linux")
    monkeypatch.setattr(runner.shutil, "which", lambda name: None)
    with pytest.raises(runner.SandboxUnavailable, match="bwrap"):
        runner._sandbox_command(tmp_path, denied_paths(tmp_path))


def test_unsupported_platform_is_an_error(monkeypatch, tmp_path):
    monkeypatch.setattr(runner.sys, "platform", "win32")
    with pytest.raises(runner.SandboxUnavailable):
        runner._sandbox_command(tmp_path, denied_paths(tmp_path))


def fake_jdk(jvm: Path, name: str) -> Path:
    (jvm / name / "bin").mkdir(parents=True)
    (jvm / name / "bin" / "java").touch()
    return jvm / name / "bin"


def test_entries_get_the_newest_jdk_that_reads_sources_as_utf8(tmp_path):
    fake_jdk(tmp_path, "java-17-openjdk-amd64")
    fake_jdk(tmp_path, "java-21-openjdk-amd64")
    assert runner._linux_java_bin(tmp_path) == [str(tmp_path / "java-21-openjdk-amd64" / "bin")]


def test_no_jdk_from_18_on_means_no_path_change(tmp_path):
    fake_jdk(tmp_path, "java-17-openjdk-arm64")
    assert runner._linux_java_bin(tmp_path) == []
