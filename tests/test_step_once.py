import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.classes.event import Event
from src.server import main
from src.server.loop import GameLoopRunner, SimulationStepper
from src.server.runtime import DEFAULT_GAME_STATE, GameSessionRuntime
from src.server.services.game_command_service import GameCommandService
from src.utils.llm.runtime_mode import is_test_mode_enabled


class _FakeSim:
    """Advances the world by one month per step and emits one event."""

    def __init__(self, world, *, gate: asyncio.Event | None = None, on_step=None):
        self.world = world
        self.gate = gate
        self.on_step = on_step
        self.step_count = 0
        self.test_mode_seen: list[bool] = []

    async def step(self):
        self.step_count += 1
        self.test_mode_seen.append(is_test_mode_enabled())
        if self.gate is not None:
            await self.gate.wait()
        self.world.month_stamp = self.world.month_stamp + 1
        if self.on_step is not None:
            self.on_step()
        return [Event(month_stamp=self.world.month_stamp, content=f"Step {self.step_count}")]


def _make_stepper(runtime, *, broadcast=None, should_auto_save=None, trigger_auto_save=None):
    return SimulationStepper(
        runtime=runtime,
        manager=SimpleNamespace(broadcast=broadcast or AsyncMock()),
        tick_payload_builder=SimpleNamespace(
            build=lambda *, events, world: {
                "type": "tick",
                "month": world.month_stamp.get_month().value,
                "events": [event.content for event in events],
            }
        ),
        should_trigger_auto_save=should_auto_save or (lambda _world: (False, 0, 0)),
        trigger_auto_save=trigger_auto_save or (lambda _world, _sim: None),
        build_auto_save_toast=lambda: {"type": "toast"},
    )


def _ready_runtime(world, sim, *, paused=True) -> GameSessionRuntime:
    runtime = GameSessionRuntime(dict(DEFAULT_GAME_STATE))
    runtime.set_world_and_sim(world, sim)
    runtime.finish_initialization()
    runtime.set_paused(paused)
    return runtime


def _make_service(runtime, stepper) -> GameCommandService:
    return GameCommandService(SimpleNamespace(runtime=runtime, get_simulation_stepper=lambda: stepper))


def _error_code(exc_info) -> str:
    return exc_info.value.detail["code"]


# --- SimulationStepper ---------------------------------------------------


@pytest.mark.asyncio
async def test_stepper_steps_once_and_broadcasts_tick(base_world):
    sim = _FakeSim(base_world)
    runtime = _ready_runtime(base_world, sim)
    broadcast = AsyncMock()
    stepper = _make_stepper(runtime, broadcast=broadcast)
    revision_before = runtime.world_revision

    result = await stepper.step_and_broadcast()

    assert sim.step_count == 1
    assert result.year == 1
    assert result.month == 2
    assert [event.content for event in result.events] == ["Step 1"]
    assert result.auto_saved is False
    assert runtime.world_revision == revision_before + 1
    broadcast.assert_awaited_once_with({"type": "tick", "month": 2, "events": ["Step 1"]})


@pytest.mark.asyncio
async def test_stepper_runs_step_in_world_test_mode_scope(base_world):
    base_world.run_config_snapshot = {"test_mode": True}
    sim = _FakeSim(base_world)
    stepper = _make_stepper(_ready_runtime(base_world, sim))

    await stepper.step_and_broadcast()

    assert sim.test_mode_seen == [True]
    assert is_test_mode_enabled() is False


@pytest.mark.asyncio
async def test_stepper_triggers_auto_save_and_toast(base_world):
    sim = _FakeSim(base_world)
    broadcast = AsyncMock()
    saved = []
    stepper = _make_stepper(
        _ready_runtime(base_world, sim),
        broadcast=broadcast,
        should_auto_save=lambda _world: (True, 10, 1),
        trigger_auto_save=lambda world, s: saved.append((world, s)),
    )

    result = await stepper.step_and_broadcast()

    assert result.auto_saved is True
    assert saved == [(base_world, sim)]
    assert broadcast.await_args_list[-1].args[0] == {"type": "toast"}


@pytest.mark.asyncio
async def test_stepper_skips_broadcast_when_reset_requested_during_step(base_world):
    runtime = _ready_runtime(base_world, None)
    sim = _FakeSim(base_world, on_step=runtime.request_reset)
    runtime.set_world_and_sim(base_world, sim)
    broadcast = AsyncMock()

    result = await _make_stepper(runtime, broadcast=broadcast).step_and_broadcast()

    assert result is None
    broadcast.assert_not_awaited()


@pytest.mark.asyncio
async def test_stepper_returns_none_without_world():
    runtime = GameSessionRuntime(dict(DEFAULT_GAME_STATE))
    broadcast = AsyncMock()

    assert await _make_stepper(runtime, broadcast=broadcast).step_and_broadcast() is None
    assert runtime.world_revision == 0
    broadcast.assert_not_awaited()


@pytest.mark.asyncio
async def test_stepper_before_step_can_abort_inside_lock(base_world):
    sim = _FakeSim(base_world)
    stepper = _make_stepper(_ready_runtime(base_world, sim))

    def _reject():
        raise RuntimeError("abort")

    with pytest.raises(RuntimeError):
        await stepper.step_and_broadcast(before_step=_reject)
    assert sim.step_count == 0


# --- GameLoopRunner still steps through the shared helper ---------------


def _make_runner(runtime, stepper):
    errors = []
    runner = GameLoopRunner(
        game_instance={"init_status": "ready"},
        runtime=runtime,
        stepper=stepper,
        get_logger=lambda: SimpleNamespace(logger=SimpleNamespace(error=lambda *a, **k: errors.append(a))),
    )
    return runner, errors


@pytest.mark.asyncio
async def test_runner_run_once_steps_and_broadcasts_when_running(base_world):
    sim = _FakeSim(base_world)
    runtime = _ready_runtime(base_world, sim, paused=False)
    broadcast = AsyncMock()
    runner, errors = _make_runner(runtime, _make_stepper(runtime, broadcast=broadcast))

    await runner.run_once()
    await runner.run_once()

    assert sim.step_count == 2
    assert base_world.month_stamp.get_month().value == 3
    assert broadcast.await_count == 2
    assert errors == []


@pytest.mark.asyncio
async def test_runner_run_once_does_not_step_while_paused(base_world):
    sim = _FakeSim(base_world)
    runtime = _ready_runtime(base_world, sim, paused=True)
    runner, _errors = _make_runner(runtime, _make_stepper(runtime))

    await runner.run_once()

    assert sim.step_count == 0


@pytest.mark.asyncio
async def test_runner_run_once_logs_step_errors(base_world):
    sim = MagicMock()
    sim.step = AsyncMock(side_effect=ValueError("boom"))
    runtime = _ready_runtime(base_world, sim, paused=False)
    runner, errors = _make_runner(runtime, _make_stepper(runtime))

    await runner.run_once()

    assert len(errors) == 1


# --- GameCommandService.step_once -----------------------------------------


@pytest.mark.asyncio
async def test_step_once_advances_one_month_and_reports_events(base_world):
    sim = _FakeSim(base_world)
    runtime = _ready_runtime(base_world, sim)
    broadcast = AsyncMock()
    service = _make_service(runtime, _make_stepper(runtime, broadcast=broadcast))

    result = await service.step_once()

    assert result["year"] == 1
    assert result["month"] == 2
    assert result["event_count"] == 1
    assert result["world_revision"] == runtime.world_revision
    assert sim.step_count == 1
    assert runtime.get("is_paused") is True
    assert runtime.is_manual_step_in_flight() is False
    broadcast.assert_awaited_once()


@pytest.mark.asyncio
async def test_step_once_rejects_when_not_ready():
    runtime = GameSessionRuntime(dict(DEFAULT_GAME_STATE))
    service = _make_service(runtime, _make_stepper(runtime))

    with pytest.raises(HTTPException) as exc_info:
        await service.step_once()

    assert exc_info.value.status_code == 503
    assert _error_code(exc_info) == "GAME_NOT_READY"


@pytest.mark.asyncio
async def test_step_once_rejects_when_not_paused(base_world):
    sim = _FakeSim(base_world)
    runtime = _ready_runtime(base_world, sim, paused=False)
    service = _make_service(runtime, _make_stepper(runtime))

    with pytest.raises(HTTPException) as exc_info:
        await service.step_once()

    assert exc_info.value.status_code == 409
    assert _error_code(exc_info) == "GAME_NOT_PAUSED"
    assert sim.step_count == 0


@pytest.mark.asyncio
async def test_step_once_rejects_while_roleplay_waits_for_decision(base_world):
    sim = _FakeSim(base_world)
    runtime = _ready_runtime(base_world, sim)
    runtime.get_roleplay_session()["status"] = "awaiting_decision"
    runtime.set_roleplay_auto_paused(True)
    service = _make_service(runtime, _make_stepper(runtime))

    with pytest.raises(HTTPException) as exc_info:
        await service.step_once()

    assert exc_info.value.status_code == 409
    assert _error_code(exc_info) == "ROLEPLAY_AWAITING_INPUT"
    assert exc_info.value.detail["details"]["pause_reason"] == "roleplay_waiting_decision"
    assert sim.step_count == 0


@pytest.mark.asyncio
async def test_concurrent_step_once_calls_do_not_double_step(base_world):
    gate = asyncio.Event()
    sim = _FakeSim(base_world, gate=gate)
    runtime = _ready_runtime(base_world, sim)
    service = _make_service(runtime, _make_stepper(runtime))

    first = asyncio.create_task(service.step_once())
    await asyncio.sleep(0)
    assert runtime.is_manual_step_in_flight() is True

    with pytest.raises(HTTPException) as exc_info:
        await service.step_once()
    assert exc_info.value.status_code == 409
    assert _error_code(exc_info) == "STEP_IN_PROGRESS"

    gate.set()
    result = await first

    assert result["month"] == 2
    assert sim.step_count == 1
    assert runtime.is_manual_step_in_flight() is False


@pytest.mark.asyncio
async def test_step_once_rechecks_preconditions_after_waiting_for_lock(base_world):
    """A loop step already holding the lock can hand control to roleplay."""
    gate = asyncio.Event()
    runtime = _ready_runtime(base_world, None)

    def _enter_roleplay_wait():
        runtime.get_roleplay_session()["status"] = "awaiting_decision"
        runtime.set_roleplay_auto_paused(True)

    sim = _FakeSim(base_world, gate=gate, on_step=_enter_roleplay_wait)
    runtime.set_world_and_sim(base_world, sim)
    stepper = _make_stepper(runtime)
    service = _make_service(runtime, stepper)

    loop_step = asyncio.create_task(stepper.step_and_broadcast())
    await asyncio.sleep(0)
    manual_step = asyncio.create_task(service.step_once())
    await asyncio.sleep(0)
    gate.set()
    await loop_step

    with pytest.raises(HTTPException) as exc_info:
        await manual_step
    assert _error_code(exc_info) == "ROLEPLAY_AWAITING_INPUT"
    assert sim.step_count == 1
    assert runtime.is_manual_step_in_flight() is False


@pytest.mark.asyncio
async def test_step_once_releases_guard_when_step_fails(base_world):
    sim = MagicMock()
    sim.step = AsyncMock(side_effect=ValueError("boom"))
    runtime = _ready_runtime(base_world, sim)
    service = _make_service(runtime, _make_stepper(runtime))

    with pytest.raises(ValueError):
        await service.step_once()

    assert runtime.is_manual_step_in_flight() is False


# --- Public API -----------------------------------------------------------


@pytest.fixture
def isolated_main_state():
    original = dict(main.game_instance)
    main.runtime.replace_with_defaults()
    try:
        yield
    finally:
        main.runtime.finish_manual_step()
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_step_advances_one_month_and_broadcasts_tick(base_world, isolated_main_state):
    sim = _FakeSim(base_world)
    main.runtime.set_world_and_sim(base_world, sim)
    main.runtime.finish_initialization()
    main.runtime.set_paused(True)

    with patch.object(main.manager, "broadcast", new=AsyncMock()) as broadcast:
        response = TestClient(main.app).post("/api/v1/command/game/step")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["year"] == 1
    assert payload["data"]["month"] == 2
    assert payload["data"]["event_count"] == 1
    assert sim.step_count == 1
    assert main.game_instance["is_paused"] is True

    tick = broadcast.await_args_list[0].args[0]
    assert tick["type"] == "tick"
    assert tick["year"] == 1
    assert tick["month"] == 2
    assert len(tick["events"]) == 1
    assert tick["events"][0]["text"].endswith("Step 1")


def test_v1_step_rejects_when_game_not_ready(isolated_main_state):
    response = TestClient(main.app).post("/api/v1/command/game/step")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "GAME_NOT_READY"


def test_v1_step_rejects_when_not_paused(base_world, isolated_main_state):
    sim = _FakeSim(base_world)
    main.runtime.set_world_and_sim(base_world, sim)
    main.runtime.finish_initialization()
    main.runtime.set_paused(False)

    response = TestClient(main.app).post("/api/v1/command/game/step")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "GAME_NOT_PAUSED"
    assert sim.step_count == 0


def test_v1_step_rejects_while_manual_step_in_flight(base_world, isolated_main_state):
    sim = _FakeSim(base_world)
    main.runtime.set_world_and_sim(base_world, sim)
    main.runtime.finish_initialization()
    main.runtime.set_paused(True)
    assert main.runtime.try_begin_manual_step() is True

    response = TestClient(main.app).post("/api/v1/command/game/step")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "STEP_IN_PROGRESS"
    assert sim.step_count == 0
