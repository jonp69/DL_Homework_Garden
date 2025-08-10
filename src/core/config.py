"""
Configuration and settings management for DL Homework Garden.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class Config:
    """Configuration manager for the application."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration manager."""
        self.config_dir = config_dir or Path.cwd()
        self.config_file = self.config_dir / "config.json"
        self.links_file = self.config_dir / "links.json"
        self.filters_file = self.config_dir / "filters.json"
        self.files_file = self.config_dir / "files.json"
        # Directory to store/link text files
        self.link_files_dir = self.config_dir / "Link_files"
        # Keep a copy of the raw user config (pre-merge) to detect missing keys
        self._raw_user_config: Dict[str, Any] = {}

        # Default configuration
        self.default_config = {
            "download_limits": {
                "max_images_per_link": 1000,
                "max_time_per_link_seconds": 3600,
                "max_file_size_mb": 500
            },
            "processing": {
                # If True, URLs with only a host (no specific path/query/fragment) are ignored automatically
                "ignore_host_only": True,
                # Domains to ignore entirely (e.g., ["example.com", "www.pixiv.net"])
                "ignored_domains": [],
                # Regex patterns to ignore (applied to full URL)
                "ignored_regexes": []
            },
            "gallery_dl": {
                "config_file": "",
                "default_args": ["--write-metadata", "--write-info-json"],
                "output_dir": ""
            },
            "ui": {
                "theme": "default",
                "window_geometry": None
            },
            "logging": {
                "level": "INFO",
                "file": "dl_homework_garden.log"
            }
        }

        # Load config (merged with defaults)
        self.config = self.load_config()

        # Ensure critical fields exist in saved config (persist defaults if missing)
        # The value can be blank; we just guarantee the field is present on disk
        self.ensure_field("gallery_dl.output_dir", "")

        # Ensure the Link_files directory exists
        try:
            self.link_files_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create Link_files directory: {e}")
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # Store raw user config for missing-key detection
                self._raw_user_config = config if isinstance(config, dict) else {}
                # Merge with defaults to ensure all keys exist in memory
                return self._merge_config(self.default_config, self._raw_user_config)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading config: {e}")
                self._raw_user_config = {}
                return self.default_config.copy()
        else:
            self._raw_user_config = {}
            return self.default_config.copy()
    
    def save_config(self) -> bool:
        """Save configuration to file."""
        try:
            self.config_dir.mkdir(exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            logger.error(f"Error saving config: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key path (e.g., 'download_limits.max_images_per_link')."""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value by key path."""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    def ensure_field(self, key: str, default: Any = "") -> None:
        """Ensure the given key path exists in the saved config file.
        If it was missing in the user's config, set it to default (can be blank) and persist.
        """
        # Check presence in the raw user config (pre-merge)
        if not self._key_in_dict(self._raw_user_config, key):
            # Set in the in-memory config
            # If a merged default already exists, keep it; otherwise, set provided default
            existing = self.get(key, None)
            self.set(key, default if existing is None else existing)
            # Persist to disk so the field is always present in file
            try:
                self.save_config()
            except Exception:
                pass

    def _key_in_dict(self, data: Dict[str, Any], key_path: str) -> bool:
        """Return True if the nested key_path exists in the dict."""
        node: Any = data
        for part in key_path.split('.'):
            if not isinstance(node, dict) or part not in node:
                return False
            node = node[part]
        return True
    
    def _merge_config(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge user config with defaults."""
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result
