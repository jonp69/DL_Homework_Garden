"""
Filter management for link processing.
"""

import json
import logging
import re
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional
from enum import Enum
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class MatchType(Enum):
    """Enum for filter match types."""
    EXACT = "match_exactly"
    CASE_INSENSITIVE = "match_case_insensitive"
    ANY = "match_any"
    EXPRESSION = "match_expression"
    REGEX = "match_regex"
    STARTS_WITH = "match_starts_with"
    ENDS_WITH = "match_ends_with"
    CONTAINS = "match_contains"
    NOT_CONTAINS = "match_not_contains"
    NOT_STARTS_WITH = "match_not_starts_with"
    NOT_ENDS_WITH = "match_not_ends_with"
    NOT_REGEX = "match_not_regex"

class FilterAction(Enum):
    """Enum for filter actions."""
    TO_DOWNLOAD = "to_download"
    TO_SKIP = "to_skip"
    DELETED = "deleted"
    IGNORE = "ignore"
    SKIP = "skip"

class FilterRule:
    """A single rule within a filter."""
    
    def __init__(self, token: str, match_type: MatchType, expression: str = ""):
        self.token = token
        self.match_type = match_type
        self.expression = expression
    
    def matches(self, value: str) -> bool:
        """Check if the rule matches a single URL token (positional token matching)."""
        # Prefer expression if provided; fall back to token for backward compatibility
        needle = self.expression if (self.expression is not None and self.expression != "") else self.token
        
        try:
            if self.match_type == MatchType.EXACT:
                return value == needle
            elif self.match_type == MatchType.CASE_INSENSITIVE:
                return value.lower() == needle.lower()
            elif self.match_type == MatchType.ANY:
                return True
            elif self.match_type == MatchType.STARTS_WITH:
                return value.startswith(needle)
            elif self.match_type == MatchType.ENDS_WITH:
                return value.endswith(needle)
            elif self.match_type == MatchType.CONTAINS:
                return needle in value
            elif self.match_type == MatchType.NOT_CONTAINS:
                return needle not in value
            elif self.match_type == MatchType.NOT_STARTS_WITH:
                return not value.startswith(needle)
            elif self.match_type == MatchType.NOT_ENDS_WITH:
                return not value.endswith(needle)
            elif self.match_type == MatchType.REGEX:
                return bool(re.search(needle, value))
            elif self.match_type == MatchType.NOT_REGEX:
                return not bool(re.search(needle, value))
        except re.error:
            logger.error(f"Invalid regex pattern: {needle}")
            # For NOT_REGEX, invalid pattern should not block matching other rules; treat as True to avoid false negatives
            return self.match_type == MatchType.NOT_REGEX
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'token': self.token,
            'match_type': self.match_type.value,
            'expression': self.expression
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FilterRule':
        """Create FilterRule from dictionary."""
        return cls(
            token=data['token'],
            match_type=MatchType(data['match_type']),
            expression=data.get('expression', '')
        )

class LinkFilter:
    """A filter for processing links."""
    
    def __init__(self, name: str, rules: List[FilterRule], action: FilterAction, **kwargs):
        self.id = kwargs.get('id', str(uuid.uuid4()))
        # New: stable internal numeric id for referencing filters from links
        self.numeric_id: int | None = kwargs.get('numeric_id', None)
        self.name = name
        self.rules = rules
        self.action = action
        self.enabled = kwargs.get('enabled', True)
        self.priority = kwargs.get('priority', 0)
        self.description = kwargs.get('description', '')
        self.created_timestamp = kwargs.get('created_timestamp', '')
        self.modified_timestamp = kwargs.get('modified_timestamp', '')
    
    def matches(self, url: str) -> bool:
        """Positional matching: rules are applied to ordered URL tokens from the start."""
        if not self.enabled:
            return False
        
        tokens = self._tokenize_url(url)
        if not tokens:
            return False
        
        # All rules must match sequentially from the first token
        if len(self.rules) > len(tokens):
            return False
        
        for i, rule in enumerate(self.rules):
            if not rule.matches(tokens[i]):
                return False
        
        return len(self.rules) > 0
    
    def _tokenize_url(self, url: str) -> List[str]:
        """Break URL into ordered tokens for positional matching (domain parts, then path segments, then query parts, then fragment)."""
        parsed = urlparse(url)
        tokens: List[str] = []
        
        # Domain parts in order (omit full netloc and scheme)
        if parsed.netloc:
            tokens.extend([p for p in parsed.netloc.split('.') if p])
        
        # Path segments in order (omit leading/trailing slashes and full path)
        if parsed.path:
            path_parts = [part for part in parsed.path.split('/') if part]
            tokens.extend(path_parts)
        
        # Query parts in order (key=value)
        if parsed.query:
            tokens.extend([p for p in parsed.query.split('&') if p])
        
        # Fragment last
        if parsed.fragment:
            tokens.append(parsed.fragment)
        
        return tokens
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'numeric_id': self.numeric_id,
            'name': self.name,
            'rules': [rule.to_dict() for rule in self.rules],
            'action': self.action.value,
            'enabled': self.enabled,
            'priority': self.priority,
            'description': self.description,
            'created_timestamp': self.created_timestamp,
            'modified_timestamp': self.modified_timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LinkFilter':
        """Create LinkFilter from dictionary."""
        rules = [FilterRule.from_dict(rule_data) for rule_data in data.get('rules', [])]
        return cls(
            name=data['name'],
            rules=rules,
            action=FilterAction(data['action']),
            id=data.get('id', str(uuid.uuid4())),
            numeric_id=data.get('numeric_id', None),
            enabled=data.get('enabled', True),
            priority=data.get('priority', 0),
            description=data.get('description', ''),
            created_timestamp=data.get('created_timestamp', ''),
            modified_timestamp=data.get('modified_timestamp', '')
        )

class FilterManager:
    """Manager for link filters."""
    
    def __init__(self, filters_file: Path):
        self.filters_file = filters_file
        self.filters: List[LinkFilter] = []
        self._next_numeric_id = 1
        self.load_filters()
    
    def load_filters(self) -> bool:
        """Load filters from JSON file."""
        if not self.filters_file.exists():
            logger.info(f"Filters file {self.filters_file} does not exist, starting with empty filter list")
            return True
        
        try:
            with open(self.filters_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.filters.clear()
            max_numeric = 0
            for filter_data in data:
                filter_obj = LinkFilter.from_dict(filter_data)
                if filter_obj.numeric_id is None:
                    # Will assign after loading all
                    pass
                else:
                    max_numeric = max(max_numeric, int(filter_obj.numeric_id))
                self.filters.append(filter_obj)
            
            # Assign numeric IDs to any filters missing one
            self._next_numeric_id = max_numeric + 1
            for f in self.filters:
                if f.numeric_id is None:
                    f.numeric_id = self._next_numeric_id
                    self._next_numeric_id += 1
            
            # Sort by priority (higher priority first)
            self.filters.sort(key=lambda f: f.priority, reverse=True)
            
            # Persist any newly assigned numeric IDs
            self.save_filters()
            
            logger.info(f"Loaded {len(self.filters)} filters from {self.filters_file}")
            return True
        except (json.JSONDecodeError, IOError, KeyError) as e:
            logger.error(f"Error loading filters from {self.filters_file}: {e}")
            return False
    
    def save_filters(self) -> bool:
        """Save filters to JSON file."""
        try:
            self.filters_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = [filter_obj.to_dict() for filter_obj in self.filters]
            
            with open(self.filters_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved {len(self.filters)} filters to {self.filters_file}")
            return True
        except IOError as e:
            logger.error(f"Error saving filters to {self.filters_file}: {e}")
            return False
    
    def add_filter(self, filter_obj: LinkFilter) -> bool:
        """Add a new filter."""
        if filter_obj.numeric_id is None:
            existing = [int(f.numeric_id) for f in self.filters if f.numeric_id is not None]
            next_id = (max(existing) + 1) if existing else 1
            filter_obj.numeric_id = next_id
            # If the filter has a generic name, append the number to keep it unique for display
            if not filter_obj.name or filter_obj.name.lower().startswith("unnamed"):
                filter_obj.name = f"Unnamed_{next_id}"
        
        self.filters.append(filter_obj)
        self.filters.sort(key=lambda f: f.priority, reverse=True)
        self.save_filters()
        logger.info(f"Added filter: {filter_obj.name} (#{filter_obj.numeric_id})")
        return True
    
    def remove_filter(self, filter_id: str) -> bool:
        """Remove a filter by ID."""
        original_count = len(self.filters)
        self.filters = [f for f in self.filters if f.id != filter_id]
        
        if len(self.filters) < original_count:
            self.save_filters()
            logger.info(f"Removed filter with ID: {filter_id}")
            return True
        
        logger.warning(f"Filter not found for removal: {filter_id}")
        return False
    
    def update_filter(self, filter_obj: LinkFilter) -> bool:
        """Update an existing filter."""
        for i, existing_filter in enumerate(self.filters):
            if existing_filter.id == filter_obj.id:
                self.filters[i] = filter_obj
                self.filters.sort(key=lambda f: f.priority, reverse=True)
                self.save_filters()
                logger.info(f"Updated filter: {filter_obj.name}")
                return True
        
        logger.warning(f"Filter not found for update: {filter_obj.id}")
        return False
    
    def move_filter(self, filter_id: str, direction: str) -> bool:
        """Move filter up or down in priority."""
        filter_index = None
        for i, f in enumerate(self.filters):
            if f.id == filter_id:
                filter_index = i
                break
        
        if filter_index is None:
            return False
        
        if direction == "up" and filter_index > 0:
            # Increase priority
            self.filters[filter_index].priority += 1
        elif direction == "down" and filter_index < len(self.filters) - 1:
            # Decrease priority
            self.filters[filter_index].priority -= 1
        else:
            return False
        
        self.filters.sort(key=lambda f: f.priority, reverse=True)
        self.save_filters()
        return True
    
    def find_matching_filter(self, url: str) -> Optional[LinkFilter]:
        """Find the first matching filter for a URL."""
        for filter_obj in self.filters:
            if filter_obj.matches(url):
                logger.debug(f"URL {url} matched filter: {filter_obj.name} (#{filter_obj.numeric_id})")
                return filter_obj
        
        logger.debug(f"No filter matched URL: {url}")
        return None
    
    def get_filters_by_action(self, action: FilterAction) -> List[LinkFilter]:
        """Get all filters with a specific action."""
        return [f for f in self.filters if f.action == action]
