import base64
import json
import runpy
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

import flathub


COMMIT = "ab" * 32
ROOT = "cd" * 32
REF = "app/org.example.App/x86_64/stable"
DELTA_ID = (
    base64.b64encode(bytes.fromhex(COMMIT)).decode().rstrip("=").replace("/", "_")
)
SCRATCH = f"/repo/deltas/{DELTA_ID[:2]}/{DELTA_ID[2:]}/superblock"
REVISION = f"/repo/deltas/{DELTA_ID[:2]}/{DELTA_ID[2:]}-{DELTA_ID}/superblock"
DIRTREE = f"/repo/objects/{ROOT[:2]}/{ROOT[2:]}.dirtree"


@pytest.mark.parametrize("ignore_deltas", [False, True])
@pytest.mark.parametrize(
    "path,upgrade_from,status,method,downloads,updates,delta_downloads",
    [
        pytest.param(SCRATCH, "", 200, "GET", 1, 0, 0, id="scratch-fresh"),
        pytest.param(SCRATCH, COMMIT, 200, "GET", 1, 1, 0, id="scratch-update"),
        pytest.param(REVISION, "", 200, "GET", 1, 1, 1, id="revision-no-header"),
        pytest.param(REVISION, COMMIT, 200, "GET", 1, 1, 1, id="revision-update"),
        pytest.param(DIRTREE, "", 200, "GET", 1, 0, 0, id="root-fresh"),
        pytest.param(DIRTREE, COMMIT, 200, "GET", 1, 1, 0, id="root-update"),
        pytest.param(
            f"/repo/objects/ef/{'ef' * 31}.dirtree",
            "",
            200,
            "GET",
            0,
            0,
            0,
            id="nested-dirtree",
        ),
        pytest.param(
            SCRATCH.replace("superblock", "0"),
            "",
            200,
            "GET",
            0,
            0,
            0,
            id="payload",
        ),
        pytest.param(SCRATCH, "", 404, "GET", 0, 0, 0, id="failed-request"),
        pytest.param(SCRATCH, "", 200, "HEAD", 0, 0, 0, id="head-request"),
    ],
)
def test_transport_counts(
    tmp_path,
    monkeypatch,
    ignore_deltas,
    path,
    upgrade_from,
    status,
    method,
    downloads,
    updates,
    delta_downloads,
):
    cache = Mock(spec=flathub.CommitCache)
    cache.valid_arches = {"x86_64"}
    cache.has_commit.return_value = True
    cache.lookup_by_dirtree.side_effect = lambda tree: COMMIT if tree == ROOT else None
    monkeypatch.setattr(flathub, "load_cache", lambda _: cache)

    log = tmp_path / "access.log"
    log.write_text(
        '192.0.2.1 "-" "-" [16/Nov/2026:00:00:04 +0000] '
        f'"{method} {path} HTTP/1.1" {status} 1024 "" '
        f'"libostree/2026.2 flatpak/1.16.6" "{REF}" "{upgrade_from}" '
        'DE "fedora;43"\n'
    )
    dest = tmp_path / "stats"
    script = Path(__file__).resolve().parents[1] / "update-stats.py"
    args = [str(script), str(log), "--dest", str(dest)]
    if ignore_deltas:
        args.append("--ignore-deltas")
    monkeypatch.setattr(sys, "argv", args)
    runpy.run_path(str(script), run_name="__main__")

    output = dest / "2026" / "11" / "16.json"
    if not downloads:
        assert not output.exists()
        return

    assert output.exists()
    data = json.loads(output.read_text())
    assert data["downloads"] == downloads
    assert data["updates"] == updates
    assert data["delta_downloads"] == (0 if ignore_deltas else delta_downloads)
    assert data["refs"]["org.example.App"]["x86_64"] == [downloads, updates]
    assert data["ref_by_country"]["org.example.App"]["DE"] == [downloads, updates]
    assert data["ref_by_os_version"]["org.example.App"]["fedora;43"] == [
        downloads,
        updates,
    ]
