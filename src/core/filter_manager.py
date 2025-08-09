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

class FilterRule:
    """A single rule within a filter."""
    
    def __init__(self, token: str, match_type: MatchType, expression: str = ""):
        self.token = token
        self.match_type = match_type
        self.expression = expression
    
    def matches(self, value: str) -> bool:
        """Check if the rule matches the given value."""
        if self.match_type == MatchType.EXACT:
            return value == self.token
        elif self.match_type == MatchType.CASE_INSENSITIVE:
            return value.lower() == self.token.lower()
        elif self.match_type == MatchType.ANY:
            return True
        elif self.match_type == MatchType.STARTS_WITH:
            return value.startswith(self.expression)
        elif self.match_type == MatchType.ENDS_WITH:
            return value.endswith(self.expression)
        elif self.match_type == MatchType.CONTAINS:
            return self.expression in value
        elif self.match_type == MatchType.NOT_CONTAINS:
            return self.expression not in value
        elif self.match_type == MatchType.NOT_STARTS_WITH:
            return not value.startswith(self.expression)
        elif self.match_type == MatchType.NOT_ENDS_WITH:
            return not value.endswith(self.expression)
        elif self.match_type == MatchType.REGEX:
            try:
                return bool(re.search(self.expression, value))
            except re.error:
                logger.error(f"Invalid regex pattern: {self.expression}")
                return False
        elif self.match_type == MatchType.NOT_REGEX:
            try:
                return not bool(re.search(self.expression, value))
            except re.error:
                logger.error(f"Invalid regex pattern: {self.expression}")
                return True
        
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
        self.name = name
        self.rules = rules
        self.action = action
        self.enabled = kwargs.get('enabled', True)
        self.priority = kwargs.get('priority', 0)
        self.description = kwargs.get('description', '')
        self.created_timestamp = kwargs.get('created_timestamp', '')
        self.modified_timestamp = kwargs.get('modified_timestamp', '')
    
    def matches(self, url: str) -> bool:
        """Check if the filter matches the given URL."""
        if not self.enabled:
            return False
        
        # Parse URL into tokens
        tokens = self._tokenize_url(url)
        
        # All rules must match
        for rule in self.rules:
            rule_matched = False
            for token in tokens:
                if rule.matches(token):
                    rule_matched = True
                    break
            
            if not rule_matched:
                return False
        
        return len(self.rules) > 0  # At least one rule must exist
    
    def _tokenize_url(self, url: str) -> List[str]:
        """Break URL into tokens for matching."""
        parsed = urlparse(url)
        tokens = []
        
        # Add full URL
        tokens.append(url)
        
        # Add components
        if parsed.scheme:
            tokens.append(parsed.scheme)
        if parsed.netloc:
            tokens.append(parsed.netloc)
            # Split domain parts
            tokens.extend(parsed.netloc.split('.'))
        if parsed.path:
            tokens.append(parsed.path)
            # Split path parts
            path_parts = [part for part in parsed.path.split('/') if part]
            tokens.extend(path_parts)
        if parsed.query:
            tokens.append(parsed.query)
            # Split query parameters
            query_parts = parsed.query.split('&')
            tokens.extend(query_parts)
        if parsed.fragment:
            tokens.append(parsed.fragment)
        
        return tokens
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
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
            for filter_data in data:
                filter_obj = LinkFilter.from_dict(filter_data)
                self.filters.append(filter_obj)
            
            # Sort by priority (higher priority first)
            self.filters.sort(key=lambda f: f.priority, reverse=True)
            
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
        self.filters.append(filter_obj)
        self.filters.sort(key=lambda f: f.priority, reverse=True)
        self.save_filters()
        logger.info(f"Added filter: {filter_obj.name}")
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
                logger.debug(f"URL {url} matched filter: {filter_obj.name}")
                return filter_obj
        
        logger.debug(f"No filter matched URL: {url}")
        return None
    
    def get_filters_by_action(self, action: FilterAction) -> List[LinkFilter]:
        """Get all filters with a specific action."""
        return [f for f in self.filters if f.action == action]
