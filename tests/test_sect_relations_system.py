import pytest
from pathlib import Path

from src.classes.core.sect import Sect, SectHeadQuarter
from src.classes.alignment import Alignment
from src.systems.sect_relations import (
    SectRelationReason,
    compute_sect_relations,
)


def _make_sect(
    sid: int,
    name: str,
    alignment: Alignment,
    orthodoxy_id: str = "dao",
) -> Sect:
    hq = SectHeadQuarter(name="HQ", desc="", image=Path(""))
    return Sect(
        id=sid,
        name=name,
        desc="",
        member_act_style="",
        alignment=alignment,
        headquarter=hq,
        technique_names=[],
        orthodoxy_id=orthodoxy_id,
    )


def test_compute_sect_relations_alignment_orthodoxy_and_territory():
    """Sect relation values combine alignment, orthodoxy and border-contact pressure."""
    sect_a = _make_sect(1, "Righteous Sect", Alignment.RIGHTEOUS, orthodoxy_id="dao")
    sect_b = _make_sect(2, "Demonic Sect", Alignment.EVIL, orthodoxy_id="dao")

    tile_owners = {
        (0, 0): [1],
        (1, 0): [2],
    }

    relations = compute_sect_relations(
        [sect_a, sect_b],
        tile_owners,
        border_contact_counts={(1, 2): 1},
    )

    assert len(relations) == 1
    rel = relations[0]

    assert rel["sect_a_id"] == 1
    assert rel["sect_b_id"] == 2

    # Expected score: opposite alignment -40, same orthodoxy +10, 1 shared border edge -1 => -31
    assert rel["value"] == -31

    # Extract reason enum values from the structured reason_breakdown
    reasons = {item["reason"] for item in rel["reason_breakdown"]}
    assert SectRelationReason.ALIGNMENT_OPPOSITE.value in reasons
    assert SectRelationReason.ORTHODOXY_SAME.value in reasons
    assert SectRelationReason.TERRITORY_CONFLICT.value in reasons


def test_compute_sect_relations_no_overlap_neutral_alignment():
    """With neutral alignment or no border contact, only alignment/orthodoxy decide the value."""
    sect_a = _make_sect(1, "Neutral Sect One", Alignment.NEUTRAL, orthodoxy_id="dao")
    sect_b = _make_sect(2, "Neutral Sect Two", Alignment.NEUTRAL, orthodoxy_id="buddha")

    # No border contact at all
    tile_owners = {}

    relations = compute_sect_relations([sect_a, sect_b], tile_owners)
    assert len(relations) == 1
    rel = relations[0]

    # Same alignment +20, different orthodoxy -15, total +5
    assert rel["value"] == 5

    reasons = {item["reason"] for item in rel["reason_breakdown"]}
    assert SectRelationReason.ALIGNMENT_SAME.value in reasons
    assert SectRelationReason.ORTHODOXY_DIFFERENT.value in reasons
    assert SectRelationReason.TERRITORY_CONFLICT.value not in reasons


def test_compute_sect_relations_supports_war_and_peace_breakdown():
    sect_a = _make_sect(1, "Sect A", Alignment.RIGHTEOUS, orthodoxy_id="dao")
    sect_b = _make_sect(2, "Sect B", Alignment.RIGHTEOUS, orthodoxy_id="dao")

    relations = compute_sect_relations(
        [sect_a, sect_b],
        {},
        diplomacy_by_pair={
            (1, 2): [
                {"reason": SectRelationReason.WAR_STATE.value, "delta": -20, "meta": {"status": "war", "war_months": 18}},
            ]
        },
    )
    assert relations[0]["diplomacy_status"] == "war"
    assert relations[0]["diplomacy_duration_months"] == 18
    reasons = {item["reason"] for item in relations[0]["reason_breakdown"]}
    assert SectRelationReason.WAR_STATE.value in reasons

    peaceful_relations = compute_sect_relations(
        [sect_a, sect_b],
        {},
        diplomacy_by_pair={
            (1, 2): [
                {"reason": SectRelationReason.PEACE_STATE.value, "delta": 0, "meta": {"status": "peace", "peace_months": 36}},
                {"reason": SectRelationReason.LONG_PEACE.value, "delta": 3, "meta": {"status": "peace", "peace_months": 36}},
            ]
        },
    )
    assert peaceful_relations[0]["diplomacy_status"] == "peace"
    assert peaceful_relations[0]["diplomacy_duration_months"] == 36
    peaceful_reasons = {item["reason"] for item in peaceful_relations[0]["reason_breakdown"]}
    assert SectRelationReason.PEACE_STATE.value in peaceful_reasons
    assert SectRelationReason.LONG_PEACE.value in peaceful_reasons

