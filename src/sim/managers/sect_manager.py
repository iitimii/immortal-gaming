import math
from hashlib import md5
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Iterable, List, Tuple

from src.classes.event import Event
from src.systems.battle import get_base_strength
from src.utils.config import CONFIG

if TYPE_CHECKING:
    from src.classes.core.sect import Sect
    from src.classes.core.world import World
    from src.classes.environment.map import Map


@dataclass
class SectTerritorySnapshot:
    """Snapshot of sect influence areas, reused across multiple systems."""

    active_sects: List["Sect"]
    sect_centers: Dict[int, Tuple[int, int]]
    tile_owners: Dict[Tuple[int, int], List[int]]
    owned_tiles_by_sect: Dict[int, List[Tuple[int, int]]]
    border_contact_counts: Dict[Tuple[int, int], int]
    border_tiles_by_sect: Dict[int, int]
    boundary_edges_by_sect: Dict[int, List[dict[str, int | str]]]


class SectManager:
    """
    Sect manager.
    Handles sect strength calculation, influence area updates, and spirit stone settlement.
    """

    def __init__(self, world: "World"):
        self.world = world

    @staticmethod
    def _normalize_pair(sect_a_id: int, sect_b_id: int) -> Tuple[int, int]:
        a = int(sect_a_id)
        b = int(sect_b_id)
        return (a, b) if a <= b else (b, a)

    def _collect_active_sects(self) -> List["Sect"]:
        """Get the list of sects that still exist and are active."""
        # Prefer World.sect_context to get the sects enabled for this run
        sects: Iterable["Sect"] = []
        sect_context = getattr(self.world, "sect_context", None)
        if sect_context is not None:
            sects = sect_context.get_active_sects()
        else:
            sects = getattr(self.world, "existed_sects", []) or []

        # Fallback: if still empty, fall back to the global sects_by_id
        if not sects:
            from src.classes.core.sect import sects_by_id as _sects_by_id
            sects = list(_sects_by_id.values())

        return [s for s in sects if getattr(s, "is_active", True)]

    def _update_sect_strength_and_radius(self, sect: "Sect") -> None:
        """
        Calculate and update a sect's total strength and influence radius.
        The radius formula is config-driven; by default it is equivalent to int(total_strength) // 10 + 1.
        """
        # Get living members directly via the sect's members property
        members = [m for m in sect.members.values() if not getattr(m, "is_dead", False)]

        # Total strength: log(sum(exp(member strength))), using the max trick for numerical stability
        total_strength = 0.0
        if members:
            strengths = [float(get_base_strength(m)) for m in members]
            if strengths:
                max_str = max(strengths)
                # Prevent exp overflow by capping the value
                sum_exp = sum(
                    math.exp(max(-500.0, min(s - max_str, 500.0)))
                    for s in strengths
                )
                total_strength = max_str + math.log(sum_exp)

        sect.total_battle_strength = max(0.0, total_strength)
        sect_conf = getattr(CONFIG, "sect", None)
        divisor = max(1, int(getattr(sect_conf, "influence_radius_divisor", 10))) if sect_conf else 10
        bias = int(getattr(sect_conf, "influence_radius_bias", 1)) if sect_conf else 1
        sect.influence_radius = int(sect.total_battle_strength) // divisor + bias

    def _compute_sect_centers(
        self, sects: List["Sect"], game_map: "Map"
    ) -> Dict[int, Tuple[int, int]]:
        """
        Compute the center coordinates of each sect headquarters based on SectRegions on the map.
        Returns dict: sect_id -> (x, y)
        """
        centers: Dict[int, Tuple[int, int]] = {}

        # Build sect_id -> all coordinates of the corresponding SectRegion
        region_cors = getattr(game_map, "region_cors", {}) or {}
        for region in getattr(game_map, "sect_regions", {}).values():
            sect_id = getattr(region, "sect_id", -1)
            if sect_id <= 0 or sect_id in centers:
                continue

            cors = region_cors.get(region.id)
            if not cors:
                continue

            centers[sect_id] = game_map.get_center_locs(cors)

        # Keep only sects that currently exist
        return {sect.id: centers[sect.id] for sect in sects if sect.id in centers}

    def _get_claim_score(
        self,
        *,
        sect_id: int,
        tile_x: int,
        tile_y: int,
        center_x: int,
        center_y: int,
        radius: int,
        total_battle_strength: float,
    ) -> float:
        """
        Compute a sect's influence ownership score for a tile.

        Rules:
        - Distance remains the dominant term, so influence expands around the headquarters.
        - Strength provides a competitive edge in border areas, letting strong sects push borders back.
        - Stable deterministic noise gives borders a jagged look without jittering for no reason every year.
        """
        distance = abs(tile_x - center_x) + abs(tile_y - center_y)
        if distance > radius:
            return float("-inf")

        sect_conf = getattr(CONFIG, "sect", None)
        distance_weight = float(getattr(sect_conf, "territory_distance_weight", 100.0)) if sect_conf else 100.0
        strength_weight = float(getattr(sect_conf, "territory_strength_weight", 12.0)) if sect_conf else 12.0
        noise_weight = float(getattr(sect_conf, "territory_noise_weight", 6.0)) if sect_conf else 6.0

        proximity_score = float(radius - distance + 1)
        strength_score = math.log1p(max(0.0, float(total_battle_strength)))

        digest = md5(f"{sect_id}:{tile_x}:{tile_y}".encode("utf-8")).digest()
        noise = (int.from_bytes(digest[:4], "big") / 0xFFFFFFFF) - 0.5

        return (
            proximity_score * distance_weight
            + strength_score * strength_weight
            + noise * noise_weight
        )

    def _build_boundary_and_contact_stats(
        self,
        tile_owners: Dict[Tuple[int, int], List[int]],
        active_sect_ids: set[int],
    ) -> tuple[
        Dict[Tuple[int, int], int],
        Dict[int, int],
        Dict[int, List[dict[str, int | str]]],
    ]:
        border_contact_counts: Dict[Tuple[int, int], int] = {}
        border_tile_sets: Dict[int, set[Tuple[int, int]]] = {sid: set() for sid in active_sect_ids}
        boundary_edges_by_sect: Dict[int, List[dict[str, int | str]]] = {
            sid: [] for sid in active_sect_ids
        }

        directions = (
            ("left", -1, 0),
            ("right", 1, 0),
            ("top", 0, -1),
            ("bottom", 0, 1),
        )

        for (x, y), owners in tile_owners.items():
            if not owners:
                continue
            owner_id = int(owners[0])
            for side, dx, dy in directions:
                neighbor_owner_list = tile_owners.get((x + dx, y + dy), [])
                neighbor_owner = int(neighbor_owner_list[0]) if neighbor_owner_list else None
                if neighbor_owner == owner_id:
                    continue

                boundary_edges_by_sect.setdefault(owner_id, []).append(
                    {"x": x, "y": y, "side": side}
                )
                if neighbor_owner is None:
                    continue

                border_tile_sets.setdefault(owner_id, set()).add((x, y))
                border_tile_sets.setdefault(neighbor_owner, set()).add((x + dx, y + dy))
                if neighbor_owner > owner_id or (neighbor_owner == owner_id and (dx > 0 or dy > 0)):
                    pair = self._normalize_pair(owner_id, neighbor_owner)
                    border_contact_counts[pair] = border_contact_counts.get(pair, 0) + 1

        border_tiles_by_sect = {
            sid: len(border_tile_sets.get(sid, set()))
            for sid in active_sect_ids
        }
        return border_contact_counts, border_tiles_by_sect, boundary_edges_by_sect

    def _compute_snapshot(self) -> SectTerritorySnapshot:
        """
        Compute a snapshot of sect influence areas for the current world.
        Handles in one place:
        - collecting active_sects
        - updating strength and radius
        - headquarters center coordinates
        - filling tile_owners
        """
        active_sects = self._collect_active_sects()
        tile_owners: Dict[Tuple[int, int], List[int]] = {}
        owned_tiles_by_sect: Dict[int, List[Tuple[int, int]]] = {}
        sect_centers: Dict[int, Tuple[int, int]] = {}
        border_contact_counts: Dict[Tuple[int, int], int] = {}
        border_tiles_by_sect: Dict[int, int] = {}
        boundary_edges_by_sect: Dict[int, List[dict[str, int | str]]] = {}

        game_map: "Map" = getattr(self.world, "map", None)
        if not active_sects or not game_map:
            return SectTerritorySnapshot(
                active_sects=active_sects,
                sect_centers=sect_centers,
                tile_owners=tile_owners,
                owned_tiles_by_sect=owned_tiles_by_sect,
                border_contact_counts=border_contact_counts,
                border_tiles_by_sect=border_tiles_by_sect,
                boundary_edges_by_sect=boundary_edges_by_sect,
            )

        # 1. Update strength and radius
        for sect in active_sects:
            self._update_sect_strength_and_radius(sect)

        # 2. Compute headquarters center coordinates
        sect_centers = self._compute_sect_centers(active_sects, game_map)
        if not sect_centers:
            # Consistent with the old logic: if no center can be determined, do not enumerate tile_owners
            return SectTerritorySnapshot(
                active_sects=active_sects,
                sect_centers=sect_centers,
                tile_owners=tile_owners,
                owned_tiles_by_sect=owned_tiles_by_sect,
                border_contact_counts=border_contact_counts,
                border_tiles_by_sect=border_tiles_by_sect,
                boundary_edges_by_sect=boundary_edges_by_sect,
            )

        # 3. Pick a single strongest owner for each valid tile ("unique ownership")
        sect_candidates = []
        for sect in active_sects:
            center = sect_centers.get(sect.id)
            radius = int(getattr(sect, "influence_radius", 0) or 0)
            if center is None or radius <= 0:
                continue
            sect_candidates.append(
                (
                    int(sect.id),
                    center[0],
                    center[1],
                    radius,
                    float(getattr(sect, "total_battle_strength", 0.0)),
                )
            )

        for x, y in game_map.tiles.keys():
            best_owner: int | None = None
            best_score = float("-inf")
            for sect_id, center_x, center_y, radius, total_battle_strength in sect_candidates:
                score = self._get_claim_score(
                    sect_id=sect_id,
                    tile_x=x,
                    tile_y=y,
                    center_x=center_x,
                    center_y=center_y,
                    radius=radius,
                    total_battle_strength=total_battle_strength,
                )
                if score > best_score:
                    best_score = score
                    best_owner = sect_id
            if best_owner is None or best_score == float("-inf"):
                continue
            tile_owners[(x, y)] = [best_owner]
            owned_tiles_by_sect.setdefault(best_owner, []).append((x, y))

        border_contact_counts, border_tiles_by_sect, boundary_edges_by_sect = (
            self._build_boundary_and_contact_stats(
                tile_owners,
                {int(sect.id) for sect in active_sects},
            )
        )

        return SectTerritorySnapshot(
            active_sects=active_sects,
            sect_centers=sect_centers,
            tile_owners=tile_owners,
            owned_tiles_by_sect=owned_tiles_by_sect,
            border_contact_counts=border_contact_counts,
            border_tiles_by_sect=border_tiles_by_sect,
            boundary_edges_by_sect=boundary_edges_by_sect,
        )

    def get_snapshot(self) -> SectTerritorySnapshot:
        """
        Return a snapshot of sect influence areas for the current world.

        - Encapsulates internal details such as _compute_sect_centers / _iter_influence_tiles;
        - Reused by other systems (relation calculation, decision context, etc.) to avoid duplicating the same logic.
        """
        return self._compute_snapshot()

    def get_tile_owners(self) -> Tuple[List["Sect"], Dict[Tuple[int, int], List[int]]]:
        """
        Compute the influence distribution of currently active sects.

        Returns:
            (active_sects, tile_owners)
            - active_sects: list of sects that still exist and are active
            - tile_owners: (x, y) -> [sect_id, ...]
        """
        snapshot = self.get_snapshot()
        # Keep the old behavior: if no center can be determined, return empty tile_owners but still return active_sects
        return snapshot.active_sects, snapshot.tile_owners

    def calculate_income_by_sect(self, snapshot: SectTerritorySnapshot | None = None) -> Dict[int, float]:
        snapshot = snapshot or self._compute_snapshot()
        active_sects = snapshot.active_sects
        tile_owners = snapshot.tile_owners

        if not active_sects or not snapshot.sect_centers or not tile_owners:
            return {}

        income_by_sect_id: Dict[int, float] = {}
        sect_conf = getattr(CONFIG, "sect", None)
        base_income = float(getattr(sect_conf, "income_per_tile", 10)) if sect_conf else 10.0
        current_month = int(self.world.month_stamp)
        sect_by_id = {int(s.id): s for s in active_sects}

        for owners in tile_owners.values():
            if not owners:
                continue
            sid = int(owners[0])
            sect = sect_by_id.get(sid)
            if sect is None:
                continue
            extra_income = float(sect.get_extra_income_per_tile(current_month))
            effective_income_per_tile = max(0.0, base_income + extra_income)
            income_by_sect_id[sid] = income_by_sect_id.get(sid, 0.0) + effective_income_per_tile

        return income_by_sect_id

    def update_sects(self) -> List[Event]:
        """
        Settled once at the end (or start) of each year.
        Flow:
        1. Compute total strength and influence radius of active sects.
        2. Determine the center coordinates of each sect headquarters.
        3. First pass: enumerate each sect's diamond-shaped influence area by radius and record all sects occupying each tile.
        4. Second pass: split each tile's base spirit stone output among the involved sects using the "split evenly on conflict" rule.
        5. Accumulate income for each sect and generate yearly events.
        """
        events: List[Event] = []

        snapshot = self._compute_snapshot()
        active_sects = snapshot.active_sects
        tile_owners = snapshot.tile_owners

        # If there are no active sects or no center can be determined, return directly as in the old logic
        if not active_sects or not snapshot.sect_centers:
            return events

        if not tile_owners:
            # Even without any tiles, still generate the "strength update" event, just with 0 income
            pass

        # 4. Second pass: settle each sect's income using the conflict rule
        income_by_sect_id = self.calculate_income_by_sect(snapshot)

        # 5. Accumulate income for each sect and generate events
        from src.i18n import t

        for sect in active_sects:
            raw_income = income_by_sect_id.get(sect.id, 0.0)
            income = int(raw_income)
            stipend_total, _stipend_breakdown = sect.estimate_yearly_member_upkeep()
            net_change = income - stipend_total
            active_war_count = sum(
                1
                for other in active_sects
                if int(getattr(other, "id", 0)) != int(sect.id)
                and self.world.are_sects_at_war(int(sect.id), int(other.id))
            )

            for avatar in getattr(sect, "members", {}).values():
                if getattr(avatar, "is_dead", False):
                    continue
                avatar.magic_stone = avatar.magic_stone + sect.get_member_upkeep_for_avatar(avatar)

            sect.magic_stone += net_change
            weariness_before = int(getattr(sect, "war_weariness", 0) or 0)
            sect.change_war_weariness(active_war_count - 3)
            weariness_after = int(getattr(sect, "war_weariness", 0) or 0)
            content = t(
                "game.sect_update_event",
                sect_name=sect.name,
                income=income,
                upkeep=stipend_total,
                net_change=net_change,
            )
            weariness_text = t(
                "War weariness adjusted to {weariness_after} (active wars: {active_war_count}, yearly recovery: 3, previous: {weariness_before}).",
                weariness_after=weariness_after,
                active_war_count=active_war_count,
                weariness_before=weariness_before,
            )
            content = f"{content} {weariness_text}"

            event = Event(
                month_stamp=self.world.month_stamp,
                content=content,
                related_sects=[sect.id],
            )
            events.append(event)

        return events
