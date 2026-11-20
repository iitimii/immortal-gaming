from typing import Dict, List, Optional
from src.classes.mortal import Mortal
from src.systems.time import MonthStamp

class MortalManager:
    """
    Manages mortals (non-cultivators) in the world.
    Handles mortal storage, lifecycle management (aging, death), and provides awakening candidates.
    """
    def __init__(self):
        self.mortals: Dict[str, Mortal] = {}
        
    def register_mortal(self, mortal: Mortal) -> None:
        """Register a new mortal"""
        self.mortals[mortal.id] = mortal
        
    def remove_mortal(self, mortal_id: str) -> None:
        """Remove a mortal (awakened or dead)"""
        if mortal_id in self.mortals:
            del self.mortals[mortal_id]
            
    def get_mortal(self, mortal_id: str) -> Optional[Mortal]:
        return self.mortals.get(mortal_id)
        
    def get_awakening_candidates(self, current_month: MonthStamp, min_age: int = 16) -> List[Mortal]:
        """Get the list of mortals that meet the awakening age requirement"""
        candidates = []
        for mortal in self.mortals.values():
            age_months = int(current_month) - int(mortal.birth_month_stamp)
            age_years = age_months // 12
            if age_years >= min_age:
                candidates.append(mortal)
        return candidates

    def cleanup_dead_mortals(self, current_month: MonthStamp, max_lifespan: int = 80) -> int:
        """
        Clean up mortals that exceed the lifespan cap.
        Returns the number cleaned up.
        """
        dead_ids = []
        for mid, mortal in self.mortals.items():
             age_months = int(current_month) - int(mortal.birth_month_stamp)
             if age_months // 12 >= max_lifespan:
                 dead_ids.append(mid)
        
        for mid in dead_ids:
            self.remove_mortal(mid)
            
        return len(dead_ids)
