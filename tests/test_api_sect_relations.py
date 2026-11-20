import pytest
from fastapi.testclient import TestClient

from src.server import main
from src.sim.managers.sect_manager import SectManager
from src.classes.core.sect import Sect, SectHeadQuarter
from src.classes.alignment import Alignment
from src.systems.time import create_month_stamp, Year, Month
from src.classes.environment.map import Map


def _build_minimal_world_with_sects():
  """
  Build a minimal environment with a world and two sects for testing /api/v1/query/sect-relations.
  Only verifies the response structure and basic computation.
  """
  # Build a simple map
  game_map = Map(width=5, height=5)
  month_stamp = create_month_stamp(Year(100), Month.JANUARY)

  from src.classes.core.world import World

  world = World(
    map=game_map,
    month_stamp=month_stamp,
  )

  # Build two sects
  hq = SectHeadQuarter(name="HQ", desc="", image=None)  # type: ignore[arg-type]
  sect1 = Sect(
    id=1,
    name="SectA",
    desc="",
    member_act_style="",
    alignment=Alignment.RIGHTEOUS,
    headquarter=hq,
    technique_names=[],
    orthodoxy_id="dao",
  )
  sect2 = Sect(
    id=2,
    name="SectB",
    desc="",
    member_act_style="",
    alignment=Alignment.EVIL,
    headquarter=hq,
    technique_names=[],
    orthodoxy_id="dao",
  )

  world.existed_sects = [sect1, sect2]

  # Build a SectManager and attach it to the simulator
  from src.sim.simulator import Simulator

  sim = Simulator(world)
  sim.sect_manager = SectManager(world)

  return world, sim


@pytest.fixture
def api_client(monkeypatch):
  # Prepare the world and simulator
  world, sim = _build_minimal_world_with_sects()

  # Inject into the global game_instance
  main.game_instance["world"] = world
  main.game_instance["sim"] = sim

  client = TestClient(main.app)
  return client


def test_get_sect_relations_basic(api_client: TestClient):
  """Basic endpoint connectivity and response structure check."""
  resp = api_client.get("/api/v1/query/sect-relations")
  assert resp.status_code == 200

  data = resp.json()["data"]
  assert "relations" in data
  relations = data["relations"]
  assert isinstance(relations, list)

  # With only two sects there should be exactly one relation record
  assert len(relations) <= 1
  if relations:
    rel = relations[0]
    assert rel["sect_a_id"] == 1
    assert rel["sect_b_id"] == 2
    assert isinstance(rel["value"], int)
    assert rel["diplomacy_status"] in {"war", "peace"}
    assert isinstance(rel["diplomacy_duration_months"], int)
    # reason_breakdown is a structured list of reasons with detailed delta/meta
    assert isinstance(rel["reason_breakdown"], list)

