from types import SimpleNamespace

import pytest

from src.server.loop import GameLoopRunner, SimulationStepper
from src.server.runtime import DEFAULT_GAME_STATE, GameSessionRuntime
from src.server.runtime.speed import BASE_STEP_INTERVAL_SECONDS


class _StopLoop(Exception):
    pass


def _make_runner(runtime, sleep):
    return GameLoopRunner(
        game_instance={"init_status": "ready"},
        runtime=runtime,
        stepper=SimulationStepper(
            runtime=runtime,
            manager=SimpleNamespace(broadcast=None),
            tick_payload_builder=SimpleNamespace(build=lambda **_kwargs: {}),
            should_trigger_auto_save=lambda _world: (False, 0, 0),
            trigger_auto_save=lambda _world, _sim: None,
            build_auto_save_toast=lambda: {},
        ),
        get_logger=lambda: SimpleNamespace(logger=SimpleNamespace(error=lambda *a, **k: None)),
        sleep=sleep,
    )


def _recording_sleep(slept: list[float], on_sleep=None):
    async def sleep(seconds: float) -> None:
        slept.append(seconds)
        if on_sleep is not None:
            on_sleep()

    return sleep


def _runtime_with_speed(speed: float) -> GameSessionRuntime:
    runtime = GameSessionRuntime(dict(DEFAULT_GAME_STATE))
    runtime.set_simulation_speed(speed)
    return runtime


@pytest.mark.asyncio
@pytest.mark.parametrize("speed", [0.5, 1.0, 2.0, 4.0])
async def test_wait_for_next_step_scales_interval_with_speed(speed):
    slept: list[float] = []
    runner = _make_runner(_runtime_with_speed(speed), _recording_sleep(slept))

    await runner.wait_for_next_step()

    expected = BASE_STEP_INTERVAL_SECONDS / speed
    assert runner.get_step_interval() == pytest.approx(expected)
    assert sum(slept) == pytest.approx(expected)


@pytest.mark.asyncio
async def test_wait_for_next_step_sleeps_in_short_slices():
    slept: list[float] = []
    runner = _make_runner(_runtime_with_speed(0.5), _recording_sleep(slept))

    await runner.wait_for_next_step()

    assert len(slept) > 1
    assert max(slept) <= runner.sleep_slice_seconds + 1e-9
    assert sum(slept) == pytest.approx(2.0)


@pytest.mark.asyncio
async def test_speed_change_shortens_wait_already_in_progress():
    runtime = _runtime_with_speed(0.5)
    slept: list[float] = []

    def switch_to_fast_after_a_moment() -> None:
        # About 0.1s into a 2s (0.5x) wait, the player switches to 4x.
        if sum(slept) >= 0.1 - 1e-9:
            runtime.set_simulation_speed(4.0)

    runner = _make_runner(runtime, _recording_sleep(slept, switch_to_fast_after_a_moment))

    await runner.wait_for_next_step()

    assert sum(slept) == pytest.approx(0.25)


@pytest.mark.asyncio
async def test_run_forever_waits_speed_interval_between_steps():
    slept: list[float] = []
    steps: list[float] = []

    class _CountingRunner(GameLoopRunner):
        async def run_once(self) -> None:
            steps.append(sum(slept))
            if len(steps) == 3:
                raise _StopLoop()

    base = _make_runner(_runtime_with_speed(2.0), _recording_sleep(slept))
    runner = _CountingRunner(
        **{name: getattr(base, name) for name in GameLoopRunner.__dataclass_fields__}
    )

    with pytest.raises(_StopLoop):
        await runner.run_forever()

    assert steps == [pytest.approx(0.5), pytest.approx(1.0), pytest.approx(1.5)]


def test_runner_uses_default_interval_when_runtime_has_no_speed():
    runner = _make_runner(SimpleNamespace(), _recording_sleep([]))
    assert runner.get_step_interval() == pytest.approx(BASE_STEP_INTERVAL_SECONDS)
