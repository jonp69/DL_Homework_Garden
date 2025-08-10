"""
Gallery-dl integration and download management.
"""

import asyncio
import json
import logging
import subprocess
import threading
import time
from pathlib import Path
import queue
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from ..core.link_manager import LinkMetadata, LinkStatus

logger = logging.getLogger(__name__)

class DownloadStatus(Enum):
    """Download status enum."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"

@dataclass
class DownloadProgress:
    """Progress information for downloads."""
    current_link: Optional[LinkMetadata] = None
    current_progress: float = 0.0
    total_links: int = 0
    completed_links: int = 0
    failed_links: int = 0
    status: DownloadStatus = DownloadStatus.IDLE
    current_operation: str = ""
    images_downloaded: int = 0
    estimated_time_remaining: Optional[float] = None

class DownloadManager:
    """Manager for gallery-dl downloads."""
    
    def __init__(self, config, link_manager):
        self.config = config
        self.link_manager = link_manager
        self.progress = DownloadProgress()
        self.download_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.skip_current = False
        
        # Callbacks for UI updates
        self.progress_callbacks: List[Callable[[DownloadProgress], None]] = []
        self.completion_callbacks: List[Callable[[str, bool], None]] = []
        
        # Callback to ask user decision on limit exceed (returns True to continue, False to skip)
        self.ask_user_decision: Optional[Callable[[LinkMetadata, str], bool]] = None
        
        # Download limits
        self.max_images_per_link = self.config.get('download_limits.max_images_per_link', 1000)
        self.max_time_per_link = self.config.get('download_limits.max_time_per_link_seconds', 3600)
        self.max_file_size_mb = self.config.get('download_limits.max_file_size_mb', 500)
    
    def add_progress_callback(self, callback: Callable[[DownloadProgress], None]) -> None:
        """Add a callback for progress updates."""
        self.progress_callbacks.append(callback)
    
    def add_completion_callback(self, callback: Callable[[str, bool], None]) -> None:
        """Add a callback for download completion."""
        self.completion_callbacks.append(callback)
    
    def set_ask_user_callback(self, callback: Callable[[LinkMetadata, str], bool]) -> None:
        """Register a callback to ask the user whether to continue or skip when limits are exceeded."""
        self.ask_user_decision = callback

    def _notify_progress(self) -> None:
        """Notify all progress callbacks."""
        for callback in self.progress_callbacks:
            try:
                callback(self.progress)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
    
    def _notify_completion(self, link_id: str, success: bool) -> None:
        """Notify all completion callbacks."""
        for callback in self.completion_callbacks:
            try:
                callback(link_id, success)
            except Exception as e:
                logger.error(f"Error in completion callback: {e}")
    
    def start_downloads(self, link_ids: Optional[List[str]] = None) -> bool:
        """Start downloading links."""
        if self.progress.status == DownloadStatus.RUNNING:
            logger.warning("Download already running")
            return False
        
        # Get links to download
        if link_ids:
            links = [self.link_manager.get_link_by_id(link_id) 
                    for link_id in link_ids if self.link_manager.get_link_by_id(link_id)]
            links = [link for link in links if link and not link.deleted]
        else:
            links = self.link_manager.get_downloadable_links()
        
        if not links:
            logger.info("No links to download")
            return False
        
        # Reset state
        self.stop_event.clear()
        self.pause_event.clear()
        self.skip_current = False
        
        # Initialize progress
        self.progress = DownloadProgress(
            total_links=len(links),
            completed_links=0,
            failed_links=0,
            status=DownloadStatus.RUNNING
        )
        
        # Start download thread
        self.download_thread = threading.Thread(
            target=self._download_worker,
            args=(links,),
            daemon=True
        )
        self.download_thread.start()
        
        logger.info(f"Started downloading {len(links)} links")
        return True
    
    def pause_downloads(self) -> None:
        """Pause downloads."""
        if self.progress.status == DownloadStatus.RUNNING:
            self.progress.status = DownloadStatus.PAUSED
            self.pause_event.set()
            logger.info("Downloads paused")
            self._notify_progress()
    
    def resume_downloads(self) -> None:
        """Resume downloads."""
        if self.progress.status == DownloadStatus.PAUSED:
            self.progress.status = DownloadStatus.RUNNING
            self.pause_event.clear()
            logger.info("Downloads resumed")
            self._notify_progress()
    
    def stop_downloads(self) -> None:
        """Stop downloads."""
        self.progress.status = DownloadStatus.STOPPED
        self.stop_event.set()
        logger.info("Downloads stopped")
        self._notify_progress()
    
    def skip_current_download(self) -> None:
        """Skip the current download."""
        self.skip_current = True
        logger.info("Skipping current download")
    
    def _download_worker(self, links: List[LinkMetadata]) -> None:
        """Worker thread for downloads."""
        try:
            for i, link in enumerate(links):
                if self.stop_event.is_set():
                    break
                
                # Wait if paused
                while self.pause_event.is_set() and not self.stop_event.is_set():
                    time.sleep(0.1)
                
                if self.stop_event.is_set():
                    break
                
                self.progress.current_link = link
                self.progress.current_operation = f"Downloading {link.url}"
                self.progress.current_progress = 0.0
                self._notify_progress()
                
                # Update link status
                self.link_manager.update_link_status(link.id, LinkStatus.DOWNLOADING)
                
                # Download the link
                success = self._download_single_link(link)
                
                if success:
                    self.progress.completed_links += 1
                    self.link_manager.update_link_status(link.id, LinkStatus.DOWNLOADED)
                else:
                    self.progress.failed_links += 1
                    if self.skip_current:
                        self.link_manager.update_link_status(link.id, LinkStatus.SKIPPED)
                    elif link.status == LinkStatus.TO_SKIP_LIMIT:
                        # Preserve the explicit limit-based skip set during the download
                        pass
                    else:
                        self.link_manager.update_link_status(link.id, LinkStatus.ERROR)
                
                self._notify_completion(link.id, success)
                self.skip_current = False
                
                # Update progress
                self.progress.current_progress = (i + 1) / len(links)
                self._notify_progress()
            
        except Exception as e:
            logger.error(f"Error in download worker: {e}")
        finally:
            self.progress.status = DownloadStatus.IDLE
            self.progress.current_link = None
            self.progress.current_operation = "Idle"
            self._notify_progress()
    
    def _download_single_link(self, link: LinkMetadata) -> bool:
        """Download a single link using gallery-dl."""
        try:
            # Prepare gallery-dl command
            cmd = self._build_gallery_dl_command(link.url)

            logger.info(f"Starting download: {link.url}")
            logger.debug(f"Command: {' '.join(cmd)}")

            # Start process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8'
            )

            # Monitor process with timeout and skip capability
            start_time = time.time()
            images_count = 0
            output_queue: "queue.Queue[str]" = queue.Queue()

            # Reader thread to stream stdout lines without blocking
            def _reader():
                try:
                    assert process.stdout is not None
                    for line in process.stdout:
                        try:
                            output_queue.put_nowait(line)
                        except Exception:
                            pass
                except Exception:
                    pass

            reader_thread = threading.Thread(target=_reader, daemon=True)
            reader_thread.start()

            last_msg: Optional[str] = None
            while process.poll() is None:
                if self.stop_event.is_set() or self.skip_current:
                    process.terminate()
                    logger.info(f"Download terminated: {link.url}")
                    return False

                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > self.max_time_per_link:
                    logger.warning(f"Download timeout for {link.url}")
                    if self._ask_user_continue_or_skip(link, "timeout"):
                        # User chose to continue, extend timeout
                        start_time = time.time()
                    else:
                        # User chose to skip
                        link.error_message = "error(timeout)"
                        try:
                            self.link_manager.update_link_status(link.id, LinkStatus.TO_SKIP_LIMIT)
                        except Exception:
                            pass
                        # Surface explicit reason in current operation
                        self.progress.current_operation = f"Skipped (timeout): {link.url}"
                        process.terminate()
                        return False

                # Drain any new output lines and push to UI
                drained = False
                while True:
                    try:
                        line = output_queue.get_nowait()
                    except queue.Empty:
                        break
                    drained = True
                    msg = line.strip()
                    if msg:
                        # Suppress consecutive duplicates
                        if last_msg == msg:
                            continue
                        last_msg = msg
                        # Track images downloaded heuristically
                        lower = msg.lower()
                        if ("download" in lower and ("saving" in lower or "downloaded" in lower)) or "exists" in lower:
                            images_count += 1
                            self.progress.images_downloaded = images_count
                        self.progress.current_operation = msg
                        self._notify_progress()

                time.sleep(0.1)

            # Get final output
            # Ensure reader thread finishes and drain remaining lines
            try:
                reader_thread.join(timeout=1.0)
            except Exception:
                pass
            remaining_lines: list[str] = []
            while True:
                try:
                    remaining_lines.append(output_queue.get_nowait())
                except queue.Empty:
                    break
            stdout = "".join(remaining_lines)
            stderr = ""

            # Parse output for statistics
            # Combine counts from stream with any final parse of remaining stdout
            extra_images, file_size = self._parse_gallery_dl_output(stdout)
            images_count = max(images_count, extra_images)

            # Update link metadata
            link.images_count = images_count
            link.file_size_mb = file_size

            # Check limits
            if images_count > self.max_images_per_link:
                logger.warning(f"Image count limit exceeded: {images_count} > {self.max_images_per_link}")
                if not self._ask_user_continue_or_skip(link, "image_count"):
                    link.error_message = "error(image_count)"
                    try:
                        self.link_manager.update_link_status(link.id, LinkStatus.TO_SKIP_LIMIT)
                    except Exception:
                        pass
                    self.progress.current_operation = f"Skipped (image_count): {link.url}"
                    return False

            if file_size > self.max_file_size_mb:
                logger.warning(f"File size limit exceeded: {file_size}MB > {self.max_file_size_mb}MB")
                if not self._ask_user_continue_or_skip(link, "file_size"):
                    link.error_message = "error(file_size)"
                    try:
                        self.link_manager.update_link_status(link.id, LinkStatus.TO_SKIP_LIMIT)
                    except Exception:
                        pass
                    self.progress.current_operation = f"Skipped (file_size): {link.url}"
                    return False

            # Check return code
            if process.returncode == 0:
                logger.info(f"Successfully downloaded: {link.url}")
                return True
            else:
                # Build a helpful error message even when stderr is empty (we merged it into stdout)
                err = (stderr or "").strip()
                if not err:
                    # Try to use the last non-empty stdout line
                    last_line = None
                    for line in stdout.splitlines()[::-1]:
                        if line.strip():
                            last_line = line.strip()
                            break
                    err = last_line or f"gallery-dl failed (code {process.returncode})"
                logger.error(f"Gallery-dl error for {link.url}: {err}")
                link.error_message = err
                return False

        except Exception as e:
            logger.error(f"Error downloading {link.url}: {e}")
            link.error_message = str(e)
            return False
    
    def _build_gallery_dl_command(self, url: str) -> List[str]:
        """Build gallery-dl command."""
        cmd = ["gallery-dl"]
        
        # Add default arguments from config
        default_args = self.config.get('gallery_dl.default_args', [])
        cmd.extend(default_args)
        
        # Set output directory only if configured
        out_dir = self.config.get('gallery_dl.output_dir', "")
        if out_dir:
            out_path = Path(out_dir)
            if not out_path.is_absolute():
                # Resolve relative to the config directory
                out_path = (self.config.config_dir / out_path).resolve()
            try:
                out_path.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            cmd.extend(["-d", str(out_path)])
        
        # Add config file if specified
        config_file = self.config.get('gallery_dl.config_file', '')
        if config_file and Path(config_file).exists():
            cmd.extend(["--config", config_file])
        
        # Add URL
        cmd.append(url)
        
        return cmd
    
    def _parse_gallery_dl_output(self, output: str) -> tuple[int, float]:
        """Parse gallery-dl output for statistics."""
        images_count = 0
        file_size_mb = 0.0
        
        try:
            lines = output.split('\n')
            for line in lines:
                # Count download lines (this is a simple heuristic)
                if 'downloaded' in line.lower() or 'saving' in line.lower():
                    images_count += 1
        except Exception as e:
            logger.error(f"Error parsing gallery-dl output: {e}")
        
        return images_count, file_size_mb
    
    def _ask_user_continue_or_skip(self, link: LinkMetadata, limit_type: str) -> bool:
        """Ask user whether to continue or skip when limits are exceeded."""
        if self.ask_user_decision:
            try:
                return self.ask_user_decision(link, limit_type)
            except Exception as e:
                logger.error(f"Error in ask_user_decision callback: {e}")
        
        # Fallback: skip
        logger.warning(f"Limit exceeded ({limit_type}) for {link.url}, skipping by default")
        try:
            link.error_message = f"error({limit_type})"
        except Exception:
            pass
        return False
    
    def get_progress(self) -> DownloadProgress:
        """Get current download progress."""
        return self.progress
    
    def is_downloading(self) -> bool:
        """Check if downloads are currently running."""
        return self.progress.status == DownloadStatus.RUNNING
