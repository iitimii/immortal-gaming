from __future__ import annotations

from src.i18n import t


def cooldown_action(cls: type) -> type:
    """
    Cooldown class decorator:
    - Only takes effect when the class defines ACTION_CD_MONTHS > 0
    - Checks the cooldown before can_start; records the cooldown start month stamp after finish
    - Cooldown records are stored in avatar._action_cd_last_months[ClassName]
    - Also appends "(Cooldown: X months)" to the DESC for UI display
    """

    cd = int(getattr(cls, "ACTION_CD_MONTHS", 0) or 0)
    if cd <= 0:
        return cls

    # Wrap can_start
    if hasattr(cls, "can_start"):
        original_can_start = cls.can_start

        def can_start(self, **params):  # type: ignore[no-redef]
            last_map = getattr(self.avatar, "_action_cd_last_months", {})
            last = last_map.get(self.__class__.__name__)
            if last is not None:
                elapsed = self.world.month_stamp - last
                if elapsed < cd:
                    remain = cd - elapsed
                    return False, t("Action on cooldown, {remain} month(s) remaining", remain=remain)
            return original_can_start(self, **params)

        cls.can_start = can_start  # type: ignore[assignment]

    # Wrap finish: record the cooldown after calling the original logic
    if hasattr(cls, "finish"):
        original_finish = cls.finish

        async def finish(self, **params):  # type: ignore[no-redef]
            # Must await original_finish first, then record cooldown.
            # This ensures cooldown is only recorded after finish() succeeds.
            events = await original_finish(self, **params)
            last_map = getattr(self.avatar, "_action_cd_last_months", None)
            if last_map is not None:
                last_map[self.__class__.__name__] = self.world.month_stamp
            return events

        cls.finish = finish  # type: ignore[assignment]
    return cls


