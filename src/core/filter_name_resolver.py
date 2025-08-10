"""
FilterNameResolver: maps numeric filter IDs to current display names.
Loads from filters.json and refreshes on demand.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class FilterNameResolver:
    def __init__(self, filters_file: Path):
        self.filters_file = filters_file
        self._id_to_name: Dict[int, str] = {}
    
    def refresh(self) -> None:
        """Load/refresh the id->name map from filters.json."""
        try:
            if not self.filters_file.exists():
                self._id_to_name.clear()
                return
            with open(self.filters_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            mapping: Dict[int, str] = {}
            for entry in data:
                num_id = entry.get('numeric_id')
                if num_id is None:
                    continue
                name = (entry.get('name') or '').strip()
                if not name:
                    name = f"Unnamed_{num_id}"
                mapping[int(num_id)] = name
            self._id_to_name = mapping
            logger.debug(f"FilterNameResolver loaded {len(self._id_to_name)} names")
        except Exception as e:
            logger.error(f"Failed to refresh FilterNameResolver: {e}")
    
    def resolve(self, numeric_id: Optional[int]) -> str:
        """Resolve an id to the current filter name for display."""
        if numeric_id is None:
            return ""
        return self._id_to_name.get(int(numeric_id), f"Unnamed_{numeric_id}")
