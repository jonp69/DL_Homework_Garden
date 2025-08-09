"""
Widget for displaying download progress information.
"""

import logging
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, QLabel,
    QTextEdit, QGroupBox
)

from ..core.download_manager import DownloadProgress, DownloadStatus

logger = logging.getLogger(__name__)

class DownloadProgressWidget(QWidget):
    """Widget for displaying download progress."""
    
    def __init__(self):
        super().__init__()
        self.current_progress: Optional[DownloadProgress] = None
        self.setup_ui()
        
        # Update timer for elapsed time
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_elapsed_time)
        self.timer.start(1000)  # Update every second
        
        self.start_time: Optional[float] = None
    
    def setup_ui(self) -> None:
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Main progress section
        progress_group = QGroupBox("Download Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        # Overall progress
        self.overall_progress = QProgressBar()
        self.overall_progress.setVisible(False)
        progress_layout.addWidget(self.overall_progress)
        
        # Progress labels
        labels_layout = QHBoxLayout()
        
        self.status_label = QLabel("Idle")
        labels_layout.addWidget(self.status_label)
        
        labels_layout.addStretch()
        
        self.stats_label = QLabel("0 / 0 completed")
        labels_layout.addWidget(self.stats_label)
        
        progress_layout.addLayout(labels_layout)
        
        # Current operation
        self.operation_label = QLabel("No active downloads")
        self.operation_label.setStyleSheet("font-style: italic;")
        progress_layout.addWidget(self.operation_label)
        
        # Time information
        time_layout = QHBoxLayout()
        
        self.elapsed_label = QLabel("Elapsed: 00:00:00")
        time_layout.addWidget(self.elapsed_label)
        
        time_layout.addStretch()
        
        self.eta_label = QLabel("")
        time_layout.addWidget(self.eta_label)
        
        progress_layout.addLayout(time_layout)
        
        layout.addWidget(progress_group)
        
        # Current link details
        details_group = QGroupBox("Current Link")
        details_layout = QVBoxLayout(details_group)
        
        self.current_url_label = QLabel("No active download")
        self.current_url_label.setWordWrap(True)
        self.current_url_label.setStyleSheet("font-weight: bold;")
        details_layout.addWidget(self.current_url_label)
        
        self.current_details_label = QLabel("")
        details_layout.addWidget(self.current_details_label)
        
        layout.addWidget(details_group)
        
        # Log output (small area)
        log_group = QGroupBox("Recent Activity")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(100)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
    
    def update_progress(self, progress: DownloadProgress) -> None:
        """Update the progress display."""
        self.current_progress = progress
        
        # Update status
        status_text = progress.status.value.replace("_", " ").title()
        self.status_label.setText(f"Status: {status_text}")
        
        # Update overall progress
        if progress.total_links > 0:
            percentage = int((progress.completed_links + progress.failed_links) / progress.total_links * 100)
            self.overall_progress.setValue(percentage)
            self.overall_progress.setVisible(True)
        else:
            self.overall_progress.setVisible(False)
        
        # Update stats
        total_processed = progress.completed_links + progress.failed_links
        self.stats_label.setText(
            f"{total_processed} / {progress.total_links} processed "
            f"({progress.completed_links} success, {progress.failed_links} failed)"
        )
        
        # Update current operation
        self.operation_label.setText(progress.current_operation)
        
        # Update current link details
        if progress.current_link:
            self.current_url_label.setText(progress.current_link.url)
            
            details = []
            if progress.current_link.filter_matched:
                details.append(f"Filter: {progress.current_link.filter_matched}")
            if progress.current_link.source:
                details.append(f"Source: {progress.current_link.source}")
            if progress.images_downloaded > 0:
                details.append(f"Images: {progress.images_downloaded}")
            
            self.current_details_label.setText(" | ".join(details))
        else:
            self.current_url_label.setText("No active download")
            self.current_details_label.setText("")
        
        # Update ETA
        if progress.estimated_time_remaining:
            eta_minutes = int(progress.estimated_time_remaining / 60)
            eta_seconds = int(progress.estimated_time_remaining % 60)
            self.eta_label.setText(f"ETA: {eta_minutes:02d}:{eta_seconds:02d}")
        else:
            self.eta_label.setText("")
        
        # Track start time
        if progress.status == DownloadStatus.RUNNING and self.start_time is None:
            import time
            self.start_time = time.time()
        elif progress.status == DownloadStatus.IDLE:
            self.start_time = None
        
        # Add log entry for status changes
        if progress.current_operation:
            self.add_log_entry(progress.current_operation)
    
    def update_elapsed_time(self) -> None:
        """Update the elapsed time display."""
        if self.start_time is not None:
            import time
            elapsed = time.time() - self.start_time
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            
            self.elapsed_label.setText(f"Elapsed: {hours:02d}:{minutes:02d}:{seconds:02d}")
        else:
            self.elapsed_label.setText("Elapsed: 00:00:00")
    
    def add_log_entry(self, message: str) -> None:
        """Add a log entry to the activity log."""
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        
        # Add to log and scroll to bottom
        self.log_text.append(log_message)
        
        # Limit log size (keep only last 50 lines)
        lines = self.log_text.toPlainText().split('\\n')
        if len(lines) > 50:
            self.log_text.setPlainText('\\n'.join(lines[-50:]))
        
        # Scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_progress(self) -> None:
        """Clear/reset the progress display."""
        self.current_progress = None
        self.start_time = None
        
        self.status_label.setText("Idle")
        self.stats_label.setText("0 / 0 completed")
        self.operation_label.setText("No active downloads")
        self.current_url_label.setText("No active download")
        self.current_details_label.setText("")
        self.elapsed_label.setText("Elapsed: 00:00:00")
        self.eta_label.setText("")
        self.overall_progress.setVisible(False)
