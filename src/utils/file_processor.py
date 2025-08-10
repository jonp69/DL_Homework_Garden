"""
File processing utilities for extracting links from various file types.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..core.config import Config

logger = logging.getLogger(__name__)

class FileProcessor:
    """Processor for extracting links from files."""
    
    def __init__(self, files_file: Path, config: Optional[Config] = None):
        self.files_file = files_file
        self.config = config
        # Prefer Link_files dir from config for creating/saving files
        self.link_files_dir = (config.link_files_dir if config else self.files_file.parent / "Link_files")
        try:
            self.link_files_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not ensure Link_files exists: {e}")
        self.processed_files: Dict[str, Dict[str, Any]] = {}
        self.load_processed_files()
    
    def load_processed_files(self) -> bool:
        """Load processed files tracking from JSON."""
        if not self.files_file.exists():
            logger.info(f"Files tracking file {self.files_file} does not exist, starting fresh")
            return True
        
        try:
            with open(self.files_file, 'r', encoding='utf-8') as f:
                self.processed_files = json.load(f)
            
            logger.info(f"Loaded tracking for {len(self.processed_files)} files")
            return True
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading files tracking: {e}")
            return False
    
    def save_processed_files(self) -> bool:
        """Save processed files tracking to JSON."""
        try:
            self.files_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.files_file, 'w', encoding='utf-8') as f:
                json.dump(self.processed_files, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved tracking for {len(self.processed_files)} files")
            return True
        except IOError as e:
            logger.error(f"Error saving files tracking: {e}")
            return False
    
    def process_file(self, file_path: Path, ignore_tracking: bool = False) -> Optional[str]:
        """Process a single file and extract its text content."""
        try:
            file_key = str(file_path.absolute())
            
            # Check if already processed
            if not ignore_tracking and file_key in self.processed_files:
                status = self.processed_files[file_key].get('status', 'unknown')
                logger.debug(f"File {file_path} already processed with status: {status}")
                
                # Allow reprocessing of halted files
                if status != 'processed_halted':
                    return None
            
            # Read file content
            content = self._read_file_content(file_path)
            if content is None:
                return None
            
            # Record processing
            self.processed_files[file_key] = {
                'path': str(file_path),
                'processed_timestamp': datetime.now().isoformat(),
                'status': 'processed',
                'size_bytes': file_path.stat().st_size,
                'links_found': 0  # Will be updated later
            }
            
            self.save_processed_files()
            logger.info(f"Processed file: {file_path}")
            return content
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            # Record the error
            file_key = str(file_path.absolute())
            self.processed_files[file_key] = {
                'path': str(file_path),
                'processed_timestamp': datetime.now().isoformat(),
                'status': 'error',
                'error': str(e)
            }
            self.save_processed_files()
            return None
    
    def _read_file_content(self, file_path: Path) -> Optional[str]:
        """Read content from various file types."""
        try:
            suffix = file_path.suffix.lower()
            
            if suffix in ['.txt', '.md', '.log', '.url']:
                return self._read_text_file(file_path)
            elif suffix == '.json':
                return self._read_json_file(file_path)
            elif suffix in ['.html', '.htm']:
                return self._read_html_file(file_path)
            else:
                # Try to read as text
                logger.warning(f"Unknown file type {suffix}, trying as text: {file_path}")
                return self._read_text_file(file_path)
                
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None
    
    def _read_text_file(self, file_path: Path) -> Optional[str]:
        """Read a text file with encoding detection."""
        encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252', 'ascii']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                logger.debug(f"Successfully read {file_path} with encoding {encoding}")
                return content
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"Error reading {file_path} with {encoding}: {e}")
                break
        
        logger.error(f"Failed to read {file_path} with any supported encoding")
        return None
    
    def _read_json_file(self, file_path: Path) -> Optional[str]:
        """Read a JSON file and extract text content."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert JSON to string representation
            if isinstance(data, dict) or isinstance(data, list):
                return json.dumps(data, indent=2)
            else:
                return str(data)
                
        except Exception as e:
            logger.error(f"Error reading JSON file {file_path}: {e}")
            return None
    
    def _read_html_file(self, file_path: Path) -> Optional[str]:
        """Read an HTML file and extract text content."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple HTML tag removal (for basic link extraction)
            import re
            # Remove HTML tags but keep content
            text_content = re.sub(r'<[^>]+>', ' ', content)
            # Clean up whitespace
            text_content = re.sub(r'\s+', ' ', text_content).strip()
            
            return text_content
            
        except Exception as e:
            logger.error(f"Error reading HTML file {file_path}: {e}")
            return None
    
    def process_directory(self, directory: Path, recursive: bool = True, ignore_tracking: bool = False) -> List[str]:
        """Process all supported files in a directory."""
        contents: List[str] = []
        discovered = 0
        
        try:
            # If caller passes the app root or nothing relevant, default to Link_files
            if not directory or not directory.exists():
                directory = self.link_files_dir
            
            if recursive:
                files = directory.rglob('*')
            else:
                files = directory.glob('*')
            
            for file_path in files:
                if file_path.is_file():
                    discovered += 1
                    content = self.process_file(file_path, ignore_tracking=ignore_tracking)
                    if content:
                        contents.append(content)
            
            logger.info(f"Processed {len(contents)} files from {directory} (discovered: {discovered})")
            
        except Exception as e:
            logger.error(f"Error processing directory {directory}: {e}")
        
        return contents
    
    def mark_file_halted(self, file_path: Path) -> bool:
        """Mark a file as processing halted."""
        try:
            file_key = str(file_path.absolute())
            
            if file_key in self.processed_files:
                self.processed_files[file_key]['status'] = 'processed_halted'
                self.processed_files[file_key]['halted_timestamp'] = datetime.now().isoformat()
                self.save_processed_files()
                logger.info(f"Marked file as halted: {file_path}")
                return True
            else:
                logger.warning(f"Cannot mark unknown file as halted: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error marking file as halted {file_path}: {e}")
            return False
    
    def update_links_found(self, file_path: Path, links_count: int) -> bool:
        """Update the number of links found in a file."""
        try:
            file_key = str(file_path.absolute())
            
            if file_key in self.processed_files:
                self.processed_files[file_key]['links_found'] = links_count
                self.save_processed_files()
                return True
            else:
                logger.warning(f"Cannot update links count for unknown file: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating links count for {file_path}: {e}")
            return False
    
    def get_processed_files(self) -> Dict[str, Dict[str, Any]]:
        """Get dictionary of all processed files."""
        return self.processed_files.copy()
    
    def get_halted_files(self) -> List[str]:
        """Get list of files that were halted during processing."""
        return [file_data['path'] for file_data in self.processed_files.values() 
                if file_data.get('status') == 'processed_halted']
    
    def save_clipboard_content(self, content: str) -> Path:
        """Save clipboard content to a timestamped file in Link_files."""
        try:
            timestamp = int(datetime.now().timestamp())
            filename = f"Clipboard_{timestamp:06d}.txt"
            file_path = self.link_files_dir / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Saved clipboard content to: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving clipboard content: {e}")
            raise
