#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path

from typing import Any

import flathub


def _create_log_line(ref: str) -> str:
    return (
        '151.100.102.134 "-" "-" [16/May/2023:10:01:16 +0000] "GET /repo/deltas/'
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA-"
        'BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB/superblock HTTP/1.1" '
        '200 822627 "" "libostree/2023.1 flatpak/1.14.0" '
        f'"{ref}" "" US "fedora;38"\n'
    )


def _run_stats(test_log: Path, tmp_path: Path) -> dict[str, Any]:
    stats_dir: Path = tmp_path / "stats"
    result: subprocess.CompletedProcess[str] = subprocess.run(
        [
            sys.executable,
            "update-stats.py",
            str(test_log),
            "--dest",
            str(stats_dir),
            "--ref-cache",
            str(tmp_path / "ref-cache.json"),
        ],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Failed to process stats: {result.stderr}"

    output_file: Path = stats_dir / "2023" / "05" / "16.json"
    with open(output_file) as f:
        data: dict[str, Any] = json.load(f)

    return data


def test_json_structure(tmp_path: Path) -> None:
    test_log: Path = tmp_path / "test-structure.log"

    with open(test_log, "w") as f:
        f.write(_create_log_line("runtime/org.freedesktop.Platform/x86_64/23.08"))

    data: dict[str, Any] = _run_stats(test_log, tmp_path)

    assert data["date"] == "2023/05/16"

    assert isinstance(data["downloads"], int)
    assert data["downloads"] >= 0

    assert isinstance(data["updates"], int)
    assert data["updates"] >= 0

    assert isinstance(data["delta_downloads"], int)
    assert data["delta_downloads"] >= 0

    assert isinstance(data["ostree_versions"], dict)
    assert "2023.1" in data["ostree_versions"]

    assert isinstance(data["flatpak_versions"], dict)
    assert "1.14.0" in data["flatpak_versions"]

    assert isinstance(data["refs"], dict)
    for ref_id, ref_data in data["refs"].items():
        assert isinstance(ref_data, dict)
        for arch, counts in ref_data.items():
            assert isinstance(counts, list)
            assert len(counts) == 2
            assert isinstance(counts[0], int)
            assert isinstance(counts[1], int)

    assert isinstance(data["countries"], dict)
    assert "US" in data["countries"]

    assert isinstance(data["ref_by_country"], dict)
    for ref_id, country_data in data["ref_by_country"].items():
        assert isinstance(country_data, dict)
        for country, counts in country_data.items():
            assert isinstance(counts, list)
            assert len(counts) == 2
            assert isinstance(counts[0], int)
            assert isinstance(counts[1], int)

    assert isinstance(data["os_versions"], dict)
    assert "fedora;38" in data["os_versions"]

    assert isinstance(data["ref_by_os_version"], dict)
    for ref_id, os_data in data["ref_by_os_version"].items():
        assert isinstance(os_data, dict)
        for os_version, counts in os_data.items():
            assert isinstance(counts, list)
            assert len(counts) == 2
            assert isinstance(counts[0], int)
            assert isinstance(counts[1], int)

    assert isinstance(data["os_flatpak_versions"], dict)
    assert "fedora;38" in data["os_flatpak_versions"]
    if "fedora;38" in data["os_flatpak_versions"]:
        assert "1.14.0" in data["os_flatpak_versions"]["fedora;38"]


def test_valid_summary_arches_loaded(tmp_path: Path) -> None:
    cache: flathub.CommitCache = flathub.CommitCache({})

    assert isinstance(cache.valid_arches, set)
    assert len(cache.valid_arches) > 0

    assert {"x86_64", "aarch64", "i386"}.issubset(cache.valid_arches)


def test_exclude_invalid_arches(tmp_path: Path) -> None:
    test_log: Path = tmp_path / "test-invalid-arch.log"

    with open(test_log, "w") as f:
        f.write(_create_log_line("app/org.example.ValidApp/x86_64/stable"))
        f.write(_create_log_line("app/org.example.InvalidApp/abracadabra/stable"))

    data: dict[str, Any] = _run_stats(test_log, tmp_path)

    assert "org.example.ValidApp" in data["refs"]
    assert "org.example.InvalidApp" not in data["refs"]
    assert len(data["refs"]) == 1


def test_exclude_debug_locale_source_refs(tmp_path: Path) -> None:
    test_log: Path = tmp_path / "test-filtered-runtimes.log"

    with open(test_log, "w") as f:
        f.write(_create_log_line("runtime/org.freedesktop.Platform/x86_64/23.08"))
        f.write(_create_log_line("runtime/org.freedesktop.Platform.Debug/x86_64/23.08"))
        f.write(
            _create_log_line("runtime/org.freedesktop.Platform.Locale/x86_64/23.08")
        )
        f.write(_create_log_line("runtime/org.freedesktop.Sdk.Sources/x86_64/23.08"))

    data: dict[str, Any] = _run_stats(test_log, tmp_path)

    assert "org.freedesktop.Platform/23.08" in data["refs"]
    assert "org.freedesktop.Platform.Debug/23.08" not in data["refs"]
    assert "org.freedesktop.Platform.Locale/23.08" not in data["refs"]
    assert "org.freedesktop.Sdk.Sources/23.08" not in data["refs"]
    assert len(data["refs"]) == 1


def test_includes_valid_refs(tmp_path: Path) -> None:
    test_log: Path = tmp_path / "test-valid-refs.log"

    with open(test_log, "w") as f:
        f.write(_create_log_line("app/org.mozilla.Firefox/x86_64/stable"))
        f.write(_create_log_line("runtime/org.freedesktop.Platform/x86_64/23.08"))

    data: dict[str, Any] = _run_stats(test_log, tmp_path)

    assert "org.mozilla.Firefox" in data["refs"]
    assert "org.freedesktop.Platform/23.08" in data["refs"]
    assert len(data["refs"]) == 2
