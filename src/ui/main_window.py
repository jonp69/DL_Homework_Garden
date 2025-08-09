"""
Main window for DL Homework Garden application.
"""

from pathlib import Path
from PySide6.QtCore import Qt, QTimer, Signal, QByteArray
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QSplitter, QStatusBar, QProgressBar, QLabel, QMessageBox,
    QFileDialog, QApplication, QDialog
)
import logging
import threading
import base64

from ..core.config import Config
from ..core.link_manager import LinkManager, LinkStatus
from ..core.filter_manager import FilterManager
from ..core.download_manager import DownloadManager, DownloadProgress
from ..utils.file_processor import FileProcessor
from .filter_list_widget import FilterListWidget
from .link_list_widget import LinkListWidget
from .download_progress_widget import DownloadProgressWidget
from .filter_dialog import FilterDialog
from .limit_skip_dialog import LimitSkipDialog

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """Main application window."""
    
    # Signals to marshal background-thread callbacks to the UI thread
    download_progress_signal = Signal(object)
    download_completion_signal = Signal(str, bool)
    limit_decision_signal = Signal(object, str, object)
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        
        # Initialize managers
        self.link_manager = LinkManager(config.links_file)
        self.filter_manager = FilterManager(config.filters_file)
        self.file_processor = FileProcessor(config.files_file)
        self.download_manager = DownloadManager(config, self.link_manager)
        
        # Register UI callback for limit decisions (thread-safe via signal)
        self.download_manager.set_ask_user_callback(self.ask_user_on_limit)
        
        # Setup UI
        self.setup_ui()
        self.setup_connections()
        self.setup_timers()
        
        # Restore window geometry
        self.restore_geometry()
        
        logger.info("Main window initialized")
    
    def setup_ui(self) -> None:
        """Setup the user interface."""
        self.setWindowTitle("DL Homework Garden")
        self.setMinimumSize(1000, 700)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Toolbar
        toolbar_layout = self.create_toolbar()
        main_layout.addLayout(toolbar_layout)
        
        # Content splitter
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Filters
        filter_panel = self.create_filter_panel()
        content_splitter.addWidget(filter_panel)
        
        # Right panel - Links and Downloads
        right_panel = self.create_right_panel()
        content_splitter.addWidget(right_panel)
        
        # Set splitter proportions
        content_splitter.setSizes([300, 700])
        main_layout.addWidget(content_splitter)
        
        # Status bar
        self.setup_status_bar()
    
    def create_toolbar(self) -> QHBoxLayout:
        """Create the main toolbar."""
        toolbar_layout = QHBoxLayout()
        
        # File operations
        self.btn_parse_txt = QPushButton("Parse TXT Files")
        self.btn_parse_txt.setToolTip("Read links from text files in a directory")
        toolbar_layout.addWidget(self.btn_parse_txt)
        
        self.btn_load_clipboard = QPushButton("Load from Clipboard")
        self.btn_load_clipboard.setToolTip("Add links from current clipboard content")
        toolbar_layout.addWidget(self.btn_load_clipboard)
        
        toolbar_layout.addStretch()
        
        # Download controls
        self.btn_start_downloads = QPushButton("Start Downloads")
        self.btn_start_downloads.setToolTip("Start downloading marked links")
        toolbar_layout.addWidget(self.btn_start_downloads)
        
        self.btn_pause_downloads = QPushButton("Pause")
        self.btn_pause_downloads.setToolTip("Pause current downloads")
        self.btn_pause_downloads.setEnabled(False)
        toolbar_layout.addWidget(self.btn_pause_downloads)
        
        self.btn_stop_downloads = QPushButton("Stop")
        self.btn_stop_downloads.setToolTip("Stop all downloads")
        self.btn_stop_downloads.setEnabled(False)
        toolbar_layout.addWidget(self.btn_stop_downloads)
        
        self.btn_skip_current = QPushButton("Skip Current")
        self.btn_skip_current.setToolTip("Skip the current download")
        self.btn_skip_current.setEnabled(False)
        toolbar_layout.addWidget(self.btn_skip_current)
        
        toolbar_layout.addStretch()
        
        # Special views
        self.btn_view_skipped_limits = QPushButton("View Skipped (Limits)")
        self.btn_view_skipped_limits.setToolTip("View links skipped due to limits")
        toolbar_layout.addWidget(self.btn_view_skipped_limits)
        
        return toolbar_layout
    
    def create_filter_panel(self) -> QWidget:
        """Create the filter management panel."""
        filter_widget = QWidget()
        filter_layout = QVBoxLayout(filter_widget)
        
        # Title
        title_label = QLabel("Filters")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        filter_layout.addWidget(title_label)
        
        # Filter list
        self.filter_list_widget = FilterListWidget(self.filter_manager)
        filter_layout.addWidget(self.filter_list_widget)
        
        # Add filter button
        self.btn_add_filter = QPushButton("Add New Filter")
        filter_layout.addWidget(self.btn_add_filter)
        
        return filter_widget
    
    def create_right_panel(self) -> QWidget:
        """Create the right panel with links and downloads."""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Links section
        links_label = QLabel("Links")
        links_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_layout.addWidget(links_label)
        
        self.link_list_widget = LinkListWidget(self.link_manager)
        right_layout.addWidget(self.link_list_widget, 2)  # 2/3 of space
        
        # Download progress section
        progress_label = QLabel("Download Progress")
        progress_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_layout.addWidget(progress_label)
        
        self.download_progress_widget = DownloadProgressWidget()
        right_layout.addWidget(self.download_progress_widget, 1)  # 1/3 of space
        
        return right_widget
    
    def setup_status_bar(self) -> None:
        """Setup the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)
        
        # Stats labels
        self.stats_label = QLabel()
        self.update_stats()
        self.status_bar.addPermanentWidget(self.stats_label)
    
    def setup_connections(self) -> None:
        """Setup signal connections."""
        # Toolbar buttons
        self.btn_parse_txt.clicked.connect(self.parse_txt_files)
        self.btn_load_clipboard.clicked.connect(self.load_from_clipboard)
        self.btn_start_downloads.clicked.connect(self.start_downloads)
        self.btn_pause_downloads.clicked.connect(self.pause_downloads)
        self.btn_stop_downloads.clicked.connect(self.stop_downloads)
        self.btn_skip_current.clicked.connect(self.skip_current_download)
        self.btn_view_skipped_limits.clicked.connect(self.view_skipped_limits)
        self.btn_add_filter.clicked.connect(self.add_new_filter)
        
        # Filter list connections
        self.filter_list_widget.filter_changed.connect(self.on_filter_changed)
        self.filter_list_widget.reprocess_requested.connect(self.reprocess_links)
        
        # Link list connections
        self.link_list_widget.links_updated.connect(self.update_stats)
        
        # Download manager callbacks -> marshal via signals to UI thread
        self.download_manager.add_progress_callback(lambda p: self.download_progress_signal.emit(p))
        self.download_manager.add_completion_callback(lambda i, s: self.download_completion_signal.emit(i, s))
        
        # Connect signals to handlers (UI thread)
        self.download_progress_signal.connect(self.on_download_progress)
        self.download_completion_signal.connect(self.on_download_completion)
        self.limit_decision_signal.connect(self._on_limit_decision)
    
    def setup_timers(self) -> None:
        """Setup UI update timers."""
        # Regular UI update timer
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.update_ui)
        self.ui_timer.start(1000)  # Update every second
    
    def parse_txt_files(self) -> None:
        """Parse text files from a directory."""
        try:
            directory = QFileDialog.getExistingDirectory(
                self, 
                "Select Directory with Text Files",
                str(Path.home())
            )
            
            if not directory:
                return
            
            self.status_label.setText("Processing files...")
            QApplication.processEvents()
            
            directory_path = Path(directory)
            contents = self.file_processor.process_directory(directory_path, recursive=True)
            
            total_links = 0
            for content in contents:
                links = self.link_manager.add_links_from_text(
                    content, 
                    source='file', 
                    source_file=str(directory_path)
                )
                total_links += len(links)
                
                # Process each link through filters
                for link in links:
                    self.process_link_with_filters(link)
            
            self.status_label.setText(f"Added {total_links} links from {len(contents)} files")
            self.link_list_widget.refresh()
            self.update_stats()
            
            logger.info(f"Processed {len(contents)} files, added {total_links} links")
            
        except Exception as e:
            logger.error(f"Error parsing text files: {e}")
            QMessageBox.critical(self, "Error", f"Failed to parse files: {str(e)}")
    
    def load_from_clipboard(self) -> None:
        """Load links from clipboard."""
        try:
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            
            if not text.strip():
                QMessageBox.information(self, "Info", "Clipboard is empty")
                return
            
            # Save clipboard content to file
            clipboard_file = self.file_processor.save_clipboard_content(text)
            
            # Add links from clipboard
            links = self.link_manager.add_links_from_text(
                text, 
                source='clipboard', 
                source_file=str(clipboard_file)
            )
            
            # Process each link through filters
            for link in links:
                self.process_link_with_filters(link)
            
            self.status_label.setText(f"Added {len(links)} links from clipboard")
            self.link_list_widget.refresh()
            self.update_stats()
            
            logger.info(f"Added {len(links)} links from clipboard")
            
        except Exception as e:
            logger.error(f"Error loading from clipboard: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load from clipboard: {str(e)}")
    
    def process_link_with_filters(self, link) -> bool:
        """Process a link through filters, prompting user if no match."""
        # Offer to trim common trailing closers before filtering
        self.maybe_trim_url(link)
        
        matching_filter = self.filter_manager.find_matching_filter(link.url)
        
        if matching_filter:
            # Apply filter action
            if matching_filter.action.value == "to_download":
                link.status = LinkStatus.TO_DOWNLOAD
            elif matching_filter.action.value == "to_skip":
                link.status = LinkStatus.TO_SKIP
            elif matching_filter.action.value == "deleted":
                link.deleted = True
            
            link.filter_matched = matching_filter.name
            self.link_manager.save_links()
            logger.debug(f"Applied filter '{matching_filter.name}' to {link.url}")
            return True
        else:
            # No filter matches, show dialog to create one
            dialog = FilterDialog(self, link.url)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_filter = dialog.get_filter()
                self.filter_manager.add_filter(new_filter)
                self.filter_list_widget.refresh()
                
                # Apply the new filter to this link
                return self.process_link_with_filters(link)
            else:
                # User cancelled, halt processing
                return False

    def maybe_trim_url(self, link) -> None:
        """Ask user whether to remove common trailing closers from the URL."""
        try:
            original = link.url or ""
            if not original:
                return
            trimmed = original.rstrip(")]}'\"")
            if trimmed != original and len(trimmed) > 0:
                reply = QMessageBox.question(
                    self,
                    "Trim trailing characters",
                    f"This link appears to end with a trailing closer.\n\nOriginal:\n{original}\n\nTrim to:\n{trimmed}\n\nDo you want to trim it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    link.url = trimmed
                    self.link_manager.save_links()
        except Exception as e:
            logger.warning(f"Failed to prompt for URL trimming: {e}")
    
    def start_downloads(self) -> None:
        """Start downloading marked links."""
        downloadable_links = self.link_manager.get_downloadable_links()
        
        if not downloadable_links:
            QMessageBox.information(self, "Info", "No links marked for download")
            return
        
        success = self.download_manager.start_downloads()
        if success:
            self.btn_start_downloads.setEnabled(False)
            self.btn_pause_downloads.setEnabled(True)
            self.btn_stop_downloads.setEnabled(True)
            self.btn_skip_current.setEnabled(True)
            self.progress_bar.setVisible(True)
    
    def pause_downloads(self) -> None:
        """Pause current downloads."""
        self.download_manager.pause_downloads()
        self.btn_pause_downloads.setText("Resume")
        self.btn_pause_downloads.clicked.disconnect()
        self.btn_pause_downloads.clicked.connect(self.resume_downloads)
    
    def resume_downloads(self) -> None:
        """Resume paused downloads."""
        self.download_manager.resume_downloads()
        self.btn_pause_downloads.setText("Pause")
        self.btn_pause_downloads.clicked.disconnect()
        self.btn_pause_downloads.clicked.connect(self.pause_downloads)
    
    def stop_downloads(self) -> None:
        """Stop all downloads."""
        self.download_manager.stop_downloads()
        self.reset_download_ui()
    
    def skip_current_download(self) -> None:
        """Skip the current download."""
        self.download_manager.skip_current_download()
    
    def reset_download_ui(self) -> None:
        """Reset download-related UI elements."""
        self.btn_start_downloads.setEnabled(True)
        self.btn_pause_downloads.setEnabled(False)
        self.btn_stop_downloads.setEnabled(False)
        self.btn_skip_current.setEnabled(False)
        self.btn_pause_downloads.setText("Pause")
        
        # Reconnect pause button to pause function
        self.btn_pause_downloads.clicked.disconnect()
        self.btn_pause_downloads.clicked.connect(self.pause_downloads)
        
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
    
    def view_skipped_limits(self) -> None:
        """View links skipped due to limits."""
        skipped_links = self.link_manager.get_links_by_status([LinkStatus.TO_SKIP_LIMIT])
        
        if not skipped_links:
            QMessageBox.information(self, "Info", "No links skipped due to limits")
            return
        
        dialog = LimitSkipDialog(self, skipped_links, self.download_manager)
        dialog.exec()
    
    def add_new_filter(self) -> None:
        """Add a new filter."""
        dialog = FilterDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_filter = dialog.get_filter()
            self.filter_manager.add_filter(new_filter)
            self.filter_list_widget.refresh()
    
    def on_filter_changed(self) -> None:
        """Handle filter changes."""
        self.link_list_widget.refresh()
        self.update_stats()
    
    def reprocess_links(self) -> None:
        """Reprocess links against current filters without prompting for new filters."""
        self.status_label.setText("Reprocessing links...")
        QApplication.processEvents()
        
        try:
            reprocessed = 0
            for link in self.link_manager.get_active_links():
                # Only reprocess links that aren't actively downloading
                if link.status in [LinkStatus.PENDING, LinkStatus.TO_REPROCESS, LinkStatus.TO_SKIP, LinkStatus.TO_DOWNLOAD, LinkStatus.ERROR, LinkStatus.SKIPPED, LinkStatus.TO_SKIP_LIMIT]:
                    f = self.filter_manager.find_matching_filter(link.url)
                    if f:
                        # Apply action
                        if f.action.value == "to_download":
                            link.status = LinkStatus.TO_DOWNLOAD
                        elif f.action.value == "to_skip":
                            link.status = LinkStatus.TO_SKIP
                        elif f.action.value == "deleted":
                            link.deleted = True
                        link.filter_matched = f.name
                        reprocessed += 1
            # Persist changes
            self.link_manager.save_links()
            logger.info(f"Reprocessed {reprocessed} links against filters")
        except Exception as e:
            logger.error(f"Error during reprocessing: {e}")
        
        self.status_label.setText("Links reprocessed")
        self.link_list_widget.refresh()
        self.update_stats()
    
    def on_download_progress(self, progress: DownloadProgress) -> None:
        """Handle download progress updates."""
        if progress.total_links > 0:
            percentage = int(progress.current_progress * 100)
            self.progress_bar.setValue(percentage)
        
        # Update download progress widget
        self.download_progress_widget.update_progress(progress)
        
        # Update status
        if progress.current_operation:
            self.status_label.setText(progress.current_operation)
        
        # Reset UI when downloads complete
        if progress.status.value == "idle":
            self.reset_download_ui()
            self.status_label.setText("Downloads completed")
            self.link_list_widget.refresh()
            self.update_stats()
    
    def on_download_completion(self, link_id: str, success: bool) -> None:
        """Handle individual download completion."""
        # Update link list
        self.link_list_widget.refresh_link(link_id)
    
    def update_stats(self) -> None:
        """Update statistics in status bar."""
        active_links = self.link_manager.get_active_links()
        total_count = len(active_links)
        
        pending_count = len(self.link_manager.get_links_by_status([LinkStatus.PENDING]))
        download_count = len(self.link_manager.get_links_by_status([LinkStatus.TO_DOWNLOAD]))
        downloaded_count = len(self.link_manager.get_links_by_status([LinkStatus.DOWNLOADED]))
        
        stats_text = (f"Total: {total_count} | "
                     f"Pending: {pending_count} | "
                     f"To Download: {download_count} | "
                     f"Downloaded: {downloaded_count}")
        
        self.stats_label.setText(stats_text)
    
    def update_ui(self) -> None:
        """Regular UI updates."""
        # Update download progress if downloads are active
        if self.download_manager.is_downloading():
            progress = self.download_manager.get_progress()
            self.on_download_progress(progress)
    
    def restore_geometry(self) -> None:
        """Restore window geometry from config."""
        geometry_b64 = self.config.get('ui.window_geometry')
        if geometry_b64:
            try:
                geo_bytes = base64.b64decode(geometry_b64)
                self.restoreGeometry(QByteArray(geo_bytes))
            except Exception as e:
                logger.warning(f"Failed to restore window geometry: {e}")
    
    def closeEvent(self, event) -> None:
        """Handle window close event."""
        # Save window geometry
        try:
            geo = self.saveGeometry()  # QByteArray
            self.config.set('ui.window_geometry', base64.b64encode(geo.data()).decode('ascii'))
            self.config.save_config()
        except Exception as e:
            logger.warning(f"Failed to save window geometry: {e}")
        
        # Stop downloads if running
        if self.download_manager.is_downloading():
            reply = QMessageBox.question(
                self, 
                "Downloads in Progress",
                "Downloads are in progress. Do you want to stop them and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.download_manager.stop_downloads()
            else:
                event.ignore()
                return
        
        logger.info("Application closing")
        event.accept()
    
    def ask_user_on_limit(self, link, limit_type: str) -> bool:
        """Thread-safe: ask user on main thread and block caller until decision."""
        class DecisionBox:
            def __init__(self):
                import threading as _t
                self.event = _t.Event()
                self.result = False
        box = DecisionBox()
        self.limit_decision_signal.emit(link, limit_type, box)
        box.event.wait()
        return box.result
    
    def _on_limit_decision(self, link, limit_type: str, box) -> None:
        """UI-thread slot to show modal and return user's decision to background thread."""
        messages = {
            "timeout": "The download has exceeded the time limit.",
            "image_count": "The download exceeds the maximum number of images.",
            "file_size": "The download exceeds the maximum file size."
        }
        msg = messages.get(limit_type, "A limit has been exceeded.")
        reply = QMessageBox.question(
            self,
            "Limit Exceeded",
            f"{msg}\n\nURL:\n{link.url}\n\nDo you want to continue anyway?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        box.result = (reply == QMessageBox.StandardButton.Yes)
        box.event.set()
