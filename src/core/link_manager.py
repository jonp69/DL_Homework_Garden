"""
Link management and processing core functionality.
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from enum import Enum

logger = logging.getLogger(__name__)

class LinkStatus(Enum):
    """Enum for link processing status."""
    PENDING = "pending"
    TO_DOWNLOAD = "to_download"
    TO_SKIP = "to_skip"
    TO_SKIP_LIMIT = "to_skip_limit"
    TO_REPROCESS = "to_reprocess"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    SKIPPED = "skipped"
    ERROR = "error"

class LinkMetadata:
    """Metadata for a processed link."""
    
    def __init__(self, url: str, **kwargs):
        self.id = kwargs.get('id', str(uuid.uuid4()))
        self.url = url
        self.status = LinkStatus(kwargs.get('status', LinkStatus.PENDING.value))
        self.source = kwargs.get('source', 'unknown')  # file, clipboard, manual
        self.source_file = kwargs.get('source_file', '')
        self.added_timestamp = kwargs.get('added_timestamp', datetime.now().isoformat())
        self.processed_timestamp = kwargs.get('processed_timestamp', None)
        self.downloaded_timestamp = kwargs.get('downloaded_timestamp', None)
        self.filter_matched = kwargs.get('filter_matched', '')
        self.download_path = kwargs.get('download_path', '')
        self.images_count = kwargs.get('images_count', 0)
        self.file_size_mb = kwargs.get('file_size_mb', 0.0)
        self.error_message = kwargs.get('error_message', '')
        self.deleted = kwargs.get('deleted', False)
        self.tags = kwargs.get('tags', [])
        self.metadata = kwargs.get('metadata', {})
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'url': self.url,
            'status': self.status.value,
            'source': self.source,
            'source_file': self.source_file,
            'added_timestamp': self.added_timestamp,
            'processed_timestamp': self.processed_timestamp,
            'downloaded_timestamp': self.downloaded_timestamp,
            'filter_matched': self.filter_matched,
            'download_path': self.download_path,
            'images_count': self.images_count,
            'file_size_mb': self.file_size_mb,
            'error_message': self.error_message,
            'deleted': self.deleted,
            'tags': self.tags,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LinkMetadata':
        """Create LinkMetadata from dictionary."""
        return cls(data['url'], **data)

class LinkManager:
    """Manager for link processing and persistence."""
    
    def __init__(self, links_file: Path):
        self.links_file = links_file
        self.links: Dict[str, LinkMetadata] = {}
        self.load_links()
    
    def load_links(self) -> bool:
        """Load links from JSON file."""
        if not self.links_file.exists():
            logger.info(f"Links file {self.links_file} does not exist, starting with empty link list")
            return True
        
        try:
            with open(self.links_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.links.clear()
            for link_data in data:
                link = LinkMetadata.from_dict(link_data)
                self.links[link.id] = link
            
            logger.info(f"Loaded {len(self.links)} links from {self.links_file}")
            return True
        except (json.JSONDecodeError, IOError, KeyError) as e:
            logger.error(f"Error loading links from {self.links_file}: {e}")
            return False
    
    def save_links(self) -> bool:
        """Save links to JSON file."""
        try:
            self.links_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert all links to dictionaries for JSON serialization
            data = [link.to_dict() for link in self.links.values()]
            
            with open(self.links_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved {len(self.links)} links to {self.links_file}")
            return True
        except IOError as e:
            logger.error(f"Error saving links to {self.links_file}: {e}")
            return False
    
    def add_link(self, url: str, source: str = 'manual', source_file: str = '') -> LinkMetadata:
        """Add a new link to the manager."""
        # Check if URL already exists (but not deleted)
        existing_link = self.get_link_by_url(url)
        if existing_link and not existing_link.deleted:
            logger.debug(f"Link already exists: {url}")
            return existing_link
        
        # If link exists but was deleted, reactivate it
        if existing_link and existing_link.deleted:
            existing_link.deleted = False
            existing_link.status = LinkStatus.PENDING
            existing_link.added_timestamp = datetime.now().isoformat()
            existing_link.source = source
            existing_link.source_file = source_file
            logger.info(f"Reactivated deleted link: {url}")
            self.save_links()
            return existing_link
        
        # Create new link
        link = LinkMetadata(
            url=url,
            source=source,
            source_file=source_file
        )
        
        self.links[link.id] = link
        self.save_links()
        logger.info(f"Added new link: {url}")
        return link
    
    def get_link_by_url(self, url: str) -> Optional[LinkMetadata]:
        """Get link by URL."""
        for link in self.links.values():
            if link.url == url:
                return link
        return None
    
    def get_link_by_id(self, link_id: str) -> Optional[LinkMetadata]:
        """Get link by ID."""
        return self.links.get(link_id)
    
    def update_link_status(self, link_id: str, status: LinkStatus) -> bool:
        """Update link status."""
        link = self.links.get(link_id)
        if not link:
            logger.error(f"Link not found: {link_id}")
            return False
        
        link.status = status
        link.processed_timestamp = datetime.now().isoformat()
        
        if status == LinkStatus.DOWNLOADED:
            link.downloaded_timestamp = datetime.now().isoformat()
        
        self.save_links()
        logger.debug(f"Updated link {link_id} status to {status.value}")
        return True
    
    def mark_deleted(self, link_id: str) -> bool:
        """Mark link as deleted (but keep in storage)."""
        link = self.links.get(link_id)
        if not link:
            logger.error(f"Link not found: {link_id}")
            return False
        
        link.deleted = True
        self.save_links()
        logger.info(f"Marked link as deleted: {link.url}")
        return True
    
    def get_active_links(self) -> List[LinkMetadata]:
        """Get all active (non-deleted) links."""
        return [link for link in self.links.values() if not link.deleted]
    
    def get_links_by_status(self, statuses: List[LinkStatus]) -> List[LinkMetadata]:
        """Get links by status (excluding deleted)."""
        status_values = [s.value for s in statuses]
        return [link for link in self.get_active_links() 
                if link.status.value in status_values]
    
    def get_pending_links(self) -> List[LinkMetadata]:
        """Get links with pending status."""
        return self.get_links_by_status([LinkStatus.PENDING])
    
    def get_downloadable_links(self) -> List[LinkMetadata]:
        """Get links ready for download."""
        return self.get_links_by_status([LinkStatus.TO_DOWNLOAD])
    
    def get_skipped_links(self) -> List[LinkMetadata]:
        """Get skipped links that can be retried."""
        return self.get_links_by_status([
            LinkStatus.TO_SKIP, 
            LinkStatus.TO_SKIP_LIMIT, 
            LinkStatus.SKIPPED, 
            LinkStatus.ERROR
        ])
    
    def add_links_from_text(self, text: str, source: str = 'manual', source_file: str = '') -> List[LinkMetadata]:
        """Extract and add links from text."""
        import re
        
        # Simple URL regex - can be improved for specific sites
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        
        added_links = []
        for url in urls:
            # Clean up URL (remove trailing punctuation)
            url = url.rstrip('.,;:!?')
            link = self.add_link(url, source, source_file)
            added_links.append(link)
        
        logger.info(f"Added {len(added_links)} links from text")
        return added_links
