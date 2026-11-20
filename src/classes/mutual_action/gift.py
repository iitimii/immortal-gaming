from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.i18n import t
from .mutual_action import InvitationAction
from src.classes.action.param_options import ParamOptionSource
from src.classes.event import Event
from src.classes.relation.relation_delta_service import RelationDeltaService
from src.classes.story_event_service import StoryEventKind, StoryEventService
from src.utils.config import CONFIG

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar
    from src.classes.action_runtime import ActionResult
    from src.classes.core.world import World


class Gift(InvitationAction):
    """Gift: give spirit stones or items to a target.

    - Supports gifting spirit stones, materials and equipment.
    - The target is within interaction range.
    - The target can see the specific gift and choose to accept or refuse.
    - If accepted: the item moves from the initiator to the target (equipment is auto-equipped, replacing the old one).
    - Non-spirit-stone items can only be gifted one at a time.
    """
    
    # i18n IDs
    ACTION_NAME_ID = "gift_action_name"
    DESC_ID = "gift_description"
    REQUIREMENTS_ID = "gift_requirements"
    
    # Constants that need no translation
    EMOJI = "🎁"
    SPIRIT_STONE_KEY = "SPIRIT_STONE"
    
    PARAMS = {
        "target_avatar": "Avatar",
        "item_id": "str", 
        "amount": "int"
    }
    PARAM_OPTION_SOURCES = {
        "item_id": ParamOptionSource.GIFTABLE_ITEM_ID,
    }
    
    RESPONSE_ACTIONS = ["Accept", "Reject"]

    def __init__(self, avatar: "Avatar", world: "World"):
        super().__init__(avatar, world)
        # Temporarily store the current gift context, used across step frames and by build_prompt_infos
        self._current_gift_context: dict[str, Any] = {}
        self._gift_success = False

    def _get_template_path(self) -> Path:
        return CONFIG.paths.templates / "mutual_action.txt"

    def _resolve_gift(self, item_id_str: str, amount: int) -> tuple[Any, str, int]:
        """
        Resolve the gift intent; return (item object/None, display name, actual quantity).
        An item object of None means spirit stones.
        """
        # 1. Spirit stones
        if not item_id_str or str(item_id_str).strip().upper() == self.SPIRIT_STONE_KEY:
            return None, t("spirit stones"), max(1, amount)
        
        # Non-spirit-stone gifts are forced to quantity 1
        forced_amount = 1
        
        # Parse the ID
        try:
            target_id = int(item_id_str)
        except (ValueError, TypeError):
            # The ID must be numeric, otherwise it is invalid
            return None, "", 0
        
        # 2. Check equipment (Weapon/Auxiliary)
        if self.avatar.weapon and self.avatar.weapon.id == target_id:
            return self.avatar.weapon, self.avatar.weapon.name, forced_amount
        if self.avatar.auxiliary and self.avatar.auxiliary.id == target_id:
            return self.avatar.auxiliary, self.avatar.auxiliary.name, forced_amount
            
        # 3. Check inventory materials (Materials)
        for mat, qty in self.avatar.materials.items():
            if mat.id == target_id:
                return mat, mat.name, forced_amount
                
        # Not found
        return None, "", 0

    def _get_gift_description(self) -> str:
        name = self._current_gift_context.get("name", "Unknown item")
        amount = self._current_gift_context.get("amount", 0)
        obj = self._current_gift_context.get("obj")
        
        from src.classes.items.weapon import Weapon
        from src.classes.items.auxiliary import Auxiliary
        
        if obj is None: # Spirit stones
            return f"{amount} {t('spirit stones')}"
        elif isinstance(obj, (Weapon, Auxiliary)):
            return f"[{name}]"
        else:
            return f"{amount} {name}"

    def step(self, target_avatar: "Avatar|str", item_id: str = "SPIRIT_STONE", amount: int = 100) -> ActionResult:
        """
        Override step to receive extra params.
        Store the params on self, then call the parent step for the generic logic (LLM interaction).
        """
        # Params are passed in every frame; update the context
        obj, name, real_amount = self._resolve_gift(item_id, amount)
        
        self._current_gift_context = {
            "obj": obj,
            "name": name,
            "amount": real_amount,
            "original_item_id": item_id
        }
        
        # Call the parent step, which calls _build_prompt_infos -> _can_start, etc.
        return super().step(target_avatar)

    def _can_start(self, target: "Avatar") -> tuple[bool, str]:
        """Check gift conditions: whether the item exists and is sufficient."""
        obj = self._current_gift_context.get("obj")
        name = self._current_gift_context.get("name")
        amount = self._current_gift_context.get("amount", 0)
        original_id = self._current_gift_context.get("original_item_id")
        
        # Fix: if the context isn't initialized (step/start not run yet), try to recover it from the current action params
        if name is None and original_id is None:
            cur = self.avatar.current_action
            if cur and cur.action is self:
                p_item = cur.params.get("item_id", "SPIRIT_STONE")
                p_amount = cur.params.get("amount", 100)
                original_id = p_item
                obj, name, amount = self._resolve_gift(p_item, p_amount)
            else:
                return True, ""
        
        # An empty name means resolve failed
        if not name:
            return False, t("Item not found: {name}", name=original_id)

        # 1. Spirit stones
        spirit_stones_text = t("spirit stones")
        if obj is None and name == spirit_stones_text:
            if self.avatar.magic_stone < amount:
                return False, t("Insufficient spirit stones (current: {current}, need: {need})",
                              current=self.avatar.magic_stone, need=amount)
            return True, ""
            
        # 2. Items (equipment/materials)
        from src.classes.items.weapon import Weapon
        from src.classes.items.auxiliary import Auxiliary
        from src.classes.items.elixir import Elixir
        
        if isinstance(obj, Elixir):
            return False, t("Elixirs cannot be gifted")
            
        if isinstance(obj, (Weapon, Auxiliary)):
            if self.avatar.weapon is not obj and self.avatar.auxiliary is not obj:
                 return False, t("Item not equipped: {name}", name=name)
        elif obj is not None:
            # Material
            qty = self.avatar.materials.get(obj, 0)
            if qty < amount:
                 return False, t("Insufficient item: {name}", name=name)
        else:
             return False, t("Item not found: {name}", name=original_id)

        # Check interaction range (the parent MutualAction.can_start already checks; this is the extra _can_start check)
        from src.classes.observe import is_within_observation
            
        return True, ""

    def _build_prompt_infos(self, target_avatar: "Avatar") -> dict:
        """
        Override: build the prompt info passed to the LLM.
        """
        infos = super()._build_prompt_infos(target_avatar)
        
        gift_desc = self._get_gift_description()
        infos["action_info"] = t("Gift you {item}", item=gift_desc)
        
        return infos

    def start(self, target_avatar: "Avatar|str", item_id: str = "SPIRIT_STONE", amount: int = 100) -> Event:
        # start also receives params and needs the context set as well
        obj, name, real_amount = self._resolve_gift(item_id, amount)
        self._current_gift_context = {
            "obj": obj, 
            "name": name, 
            "amount": real_amount, 
            "original_item_id": item_id
        }
        
        target = self._get_target_avatar(target_avatar)
        target_name = target.name if target is not None else str(target_avatar)
        
        gift_desc = self._get_gift_description()
        
        rel_ids = [self.avatar.id]
        if target is not None:
            rel_ids.append(target.id)
        
        content = t("{initiator} attempts to gift {item} to {target}",
                   initiator=self.avatar.name, item=gift_desc, target=target_name)
        event = Event(
            self.world.month_stamp,
            content,
            related_avatars=rel_ids
        )
        
        self._gift_success = False
        return event

    def _settle_response(self, target_avatar: "Avatar", response_name: str) -> None:
        fb = str(response_name).strip()
        if fb == "Accept":
            self._apply_gift(target_avatar)
            self._gift_success = True
        else:
            self._gift_success = False

    def _apply_gift(self, target: "Avatar") -> None:
        """Execute the item transfer."""
        obj = self._current_gift_context.get("obj")
        amount = self._current_gift_context.get("amount", 0)
        
        if obj is None:
            # Spirit stones
            if self.avatar.magic_stone >= amount:
                self.avatar.magic_stone -= amount
                target.magic_stone += amount
        else:
            from src.classes.items.weapon import Weapon
            from src.classes.items.auxiliary import Auxiliary
            
            if isinstance(obj, (Weapon, Auxiliary)):
                # Equipment: initiator unequips -> target equips (old equipment handled automatically)
                if self.avatar.weapon is obj:
                    self.avatar.weapon = None
                elif self.avatar.auxiliary is obj:
                    self.avatar.auxiliary = None
                else:
                    return # No longer equipped
                
                # Target equips
                new_equip = obj 
                
                old_item = None
                if isinstance(new_equip, Weapon):
                    old_item = target.weapon
                    target.weapon = new_equip
                else: # Auxiliary
                    old_item = target.auxiliary
                    target.auxiliary = new_equip
                
                # Old equipment: call the sell_X interface directly
                # This both yields spirit stones and makes CirculationManager record the outgoing item
                if old_item:
                    if isinstance(old_item, Weapon):
                        target.sell_weapon(old_item)
                    elif isinstance(old_item, Auxiliary):
                        target.sell_auxiliary(old_item)
                    
            else:
                # Materials: initiator removes -> target adds
                if self.avatar.remove_material(obj, amount):
                    target.add_material(obj, amount)

    async def finish(self, target_avatar: "Avatar|str") -> list[Event]:
        target = self._get_target_avatar(target_avatar)
        events: list[Event] = []
        if target is None:
            return events

        if self._gift_success:
            gift_desc = self._get_gift_description()
            result_text = t("{initiator} successfully gifted {item} to {target}",
                          initiator=self.avatar.name, item=gift_desc, target=target.name)
            
            result_event = Event(
                self.world.month_stamp,
                result_text,
                related_avatars=[self.avatar.id, target.id]
            )
            events.append(result_event)
            a_to_b, b_to_a = await RelationDeltaService.resolve_event_text_delta(
                action_key="gift",
                avatar_a=self.avatar,
                avatar_b=target,
                event_text=result_text,
            )
            RelationDeltaService.apply_bidirectional_delta(self.avatar, target, a_to_b, b_to_a)
            story_event = await StoryEventService.maybe_create_story(
                kind=StoryEventKind.DAILY_SOCIAL,
                month_stamp=self.world.month_stamp,
                start_text=getattr(self, "_start_event_content", ""),
                result_text=result_text,
                actors=[self.avatar, target],
                related_avatar_ids=[self.avatar.id, target.id],
                allow_relation_changes=False,
            )
            if story_event is not None:
                events.append(story_event)
        else:
            gift_desc = self._get_gift_description()
            result_text = t("{target} rejected {initiator}'s gift: {item}",
                          target=target.name, initiator=self.avatar.name, item=gift_desc)
            a_to_b, b_to_a = await RelationDeltaService.resolve_event_text_delta(
                action_key="gift",
                avatar_a=self.avatar,
                avatar_b=target,
                event_text=result_text,
            )
            RelationDeltaService.apply_bidirectional_delta(self.avatar, target, a_to_b, b_to_a)
            
        return events
