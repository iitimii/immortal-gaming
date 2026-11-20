from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from src.run import headless
from src.run.headless import HeadlessOptions, format_summary_text, main, run_headless
from src.systems.cultivation import REALM_ORDER

SHORT_RUN = dict(months=4, seed=1234, avatars=5, sects=2)


@pytest.fixture(autouse=True)
def mock_llm_managers():
    """Disable the global LLM mocks: these tests exercise the real test-mode fallbacks."""
    yield


def _without_timing(summary: dict) -> dict:
    return {key: value for key, value in summary.items() if key != "step_time_ms"}


def _forbid_real_llm():
    """Patch every real provider / connectivity entry point to fail loudly."""

    def _boom(*_args, **_kwargs):
        raise AssertionError("real LLM access attempted during a headless run")

    return (
        patch("src.utils.llm.client._call_with_requests", side_effect=_boom),
        patch("src.utils.llm.client.test_connectivity", side_effect=_boom),
        patch("src.server.init_runtime.check_llm_connectivity", side_effect=_boom),
    )


@pytest.mark.asyncio
async def test_short_run_summary_structure_without_real_llm():
    provider_patch, connectivity_patch, init_check_patch = _forbid_real_llm()
    with provider_patch as provider, connectivity_patch as connectivity, init_check_patch as init_check:
        summary = await run_headless(HeadlessOptions(**SHORT_RUN))

    provider.assert_not_called()
    connectivity.assert_not_called()
    init_check.assert_not_called()

    assert summary["test_mode"] is True
    assert summary["seed"] == 1234
    assert summary["map_id"] == headless.resolve_default_map_id()
    assert summary["init_npc_num"] == 5
    assert summary["months_simulated"] == 4

    start, final = summary["start_date"], summary["final_date"]
    assert (final["year"] * 12 + final["month"]) - (start["year"] * 12 + start["month"]) == 4

    population = summary["population"]
    assert set(population) == {"living", "dead", "deaths_during_run", "awakenings", "births"}
    assert population["living"] > 0
    assert set(summary["realm_distribution"]) == {realm.value for realm in REALM_ORDER}
    assert sum(summary["realm_distribution"].values()) == population["living"]

    sect_total = sum(entry["members"] for entry in summary["top_sects"])
    assert sect_total + summary["unaffiliated"] <= population["living"]
    for entry in summary["top_sects"]:
        assert set(entry) == {"id", "name", "members"}

    events = summary["events"]
    assert events["total"] >= events["major"] >= 0
    assert len(summary["top_event_avatars"]) <= 5
    counts = [entry["events"] for entry in summary["top_event_avatars"]]
    assert counts == sorted(counts, reverse=True)

    timing = summary["step_time_ms"]
    assert timing["max"] >= timing["p95"] > 0
    assert timing["avg"] > 0

    text = format_summary_text(summary)
    assert "Headless simulation summary" in text
    assert "Seed: 1234" in text


@pytest.mark.asyncio
async def test_same_seed_produces_same_summary():
    first = await run_headless(HeadlessOptions(**SHORT_RUN))
    second = await run_headless(HeadlessOptions(**SHORT_RUN))
    assert _without_timing(first) == _without_timing(second)


def test_cli_writes_parseable_json(tmp_path, capsys):
    json_path = tmp_path / "out" / "summary.json"
    exit_code = main(
        ["--months", "2", "--seed", "5", "--avatars", "3", "--quiet", "--json", str(json_path)]
    )

    assert exit_code == 0
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["months_simulated"] == 2
    assert data["seed"] == 5
    assert data["save_file"] is None
    assert "Headless simulation summary" in capsys.readouterr().out


def test_cli_save_writes_into_isolated_saves_dir(tmp_path, capsys):
    from src.utils.config import CONFIG

    saves_dir = Path(CONFIG.paths.saves)
    assert tmp_path in saves_dir.parents

    exit_code = main(["--months", "1", "--seed", "9", "--avatars", "3", "--quiet", "--save", "--json", "-"])

    assert exit_code == 0
    summary = json.loads(capsys.readouterr().out)
    save_file = saves_dir / summary["save_file"]
    assert save_file.exists()
    assert json.loads(save_file.read_text(encoding="utf-8"))["run_config"]["test_mode"] is True
    # Only the final save (and its events DB) land in the saves dir; the init scratch DB does not.
    assert sorted(path.name for path in saves_dir.iterdir()) == sorted(
        [save_file.name, f"{save_file.stem}_events.db"]
    )


@pytest.mark.parametrize(
    "argv",
    [["--map", "no_such_map"], ["--months", "-1"], ["--avatars", "many"], ["--quiet", "--verbose"]],
)
def test_cli_rejects_bad_arguments(argv, capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(argv)
    assert excinfo.value.code == 2
    assert "error" in capsys.readouterr().err


def test_cli_reports_simulator_exception(capsys):
    async def _broken_step(self):
        raise RuntimeError("boom in step")

    with patch("src.sim.simulator_engine.simulator.Simulator.step", _broken_step):
        exit_code = main(["--months", "1", "--seed", "1", "--avatars", "2", "--quiet"])

    assert exit_code == 1
    err = capsys.readouterr().err
    assert "Traceback" in err
    assert "boom in step" in err


def test_module_entry_point_saves_under_cws_data_dir(tmp_path):
    """`python -m src.run.headless --save` must honour CWS_DATA_DIR."""
    project_root = Path(__file__).resolve().parents[1]
    data_dir = tmp_path / "headless_data"
    env = {**os.environ, "CWS_DATA_DIR": str(data_dir), "PYTHONPATH": str(project_root)}
    result = subprocess.run(
        [sys.executable, "-m", "src.run.headless", "--months", "1", "--seed", "2",
         "--avatars", "2", "--quiet", "--save", "--json", "-"],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert (data_dir / "saves" / summary["save_file"]).exists()
