"""
Dialog for viewing links that were skipped due to limits.
"""

import logging
from typing import List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget,
    QTreeWidgetItem, QHeaderView, QLabel, QMessageBox
)

from ..core.link_manager import LinkMetadata
from ..core.download_manager import DownloadManager

logger = logging.getLogger(__name__)

class LimitSkipDialog(QDialog):
    """Dialog for viewing and managing links skipped due to limits."""
    
    def __init__(self, parent, skipped_links: List[LinkMetadata], download_manager: DownloadManager):
        super().__init__(parent)
        self.skipped_links = skipped_links
        self.download_manager = download_manager
        self.setup_ui()
        self.populate_links()
    
    def setup_ui(self) -> None:
        """Setup the user interface."""
        self.setWindowTitle("Links Skipped Due to Limits")
        self.setModal(True)
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel(
            f"The following {len(self.skipped_links)} links were skipped due to exceeding limits:"
        )
        header_label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header_label)
        
        # Links tree
        self.links_tree = QTreeWidget()
        self.links_tree.setHeaderLabels([
            "URL", "Images", "Size (MB)", "Limit Exceeded", "Filter", "Added"
        ])
        self.links_tree.setSelectionMode(QTreeWidget.SelectionMode.MultiSelection)
        
        # Configure column widths
        header = self.links_tree.header()
        header.resizeSection(0, 300)  # URL
        header.resizeSection(1, 80)   # Images
        header.resizeSection(2, 80)   # Size
        header.resizeSection(3, 120)  # Limit Exceeded
        header.resizeSection(4, 120)  # Filter
        header.setStretchLastSection(True)  # Added
        
        layout.addWidget(self.links_tree)
        
        # Instructions
        instructions = QLabel(
            "Select links and click 'Override and Download' to download them despite limits. "
            "Downloads will run in a separate thread."
        )
        instructions.setStyleSheet("font-style: italic; margin-top: 10px;")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.clicked.connect(self.select_all)
        button_layout.addWidget(self.btn_select_all)
        
        self.btn_select_none = QPushButton("Select None")
        self.btn_select_none.clicked.connect(self.select_none)
        button_layout.addWidget(self.btn_select_none)
        
        button_layout.addStretch()
        
        self.btn_override = QPushButton("Override and Download Selected")
        self.btn_override.clicked.connect(self.override_selected)
        self.btn_override.setStyleSheet("font-weight: bold; color: darkred;")
        button_layout.addWidget(self.btn_override)
        
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        button_layout.addWidget(self.btn_close)
        
        layout.addLayout(button_layout)
    
    def populate_links(self) -> None:
        """Populate the links tree with skipped links."""
        for link in self.skipped_links:
            item = QTreeWidgetItem(self.links_tree)
            
            # Store link ID for reference
            item.setData(0, Qt.ItemDataRole.UserRole, link.id)
            
            # Set column data
            item.setText(0, link.url)
            item.setText(1, str(link.images_count) if link.images_count > 0 else "Unknown")
            item.setText(2, f"{link.file_size_mb:.2f}" if link.file_size_mb > 0 else "Unknown")
            
            # Determine limit exceeded (this would need to be stored in link metadata)
            limit_exceeded = self.determine_limit_exceeded(link)
            item.setText(3, limit_exceeded)
            
            item.setText(4, link.filter_matched or "None")
            
            # Format timestamp
            if link.added_timestamp:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(link.added_timestamp.replace('Z', '+00:00'))
                    formatted_time = dt.strftime("%Y-%m-%d %H:%M")
                    item.setText(5, formatted_time)
                except:
                    item.setText(5, link.added_timestamp)
            
            # Set tooltip
            tooltip = f"URL: {link.url}\\nImages: {link.images_count}\\nSize: {link.file_size_mb:.2f}MB"
            if link.error_message:
                tooltip += f"\\nError: {link.error_message}"
            item.setToolTip(0, tooltip)
            
            # Color code by limit type
            if "image" in limit_exceeded.lower():
                item.setBackground(0, Qt.GlobalColor.yellow)
            elif "size" in limit_exceeded.lower():
                item.setBackground(0, Qt.GlobalColor.lightGray)
            elif "time" in limit_exceeded.lower():
                item.setBackground(0, Qt.GlobalColor.cyan)
    
    def determine_limit_exceeded(self, link: LinkMetadata) -> str:
        """Determine which limit was exceeded for a link."""
        # This is a simplified version - in a real implementation,
        # you'd store the specific limit exceeded in the link metadata
        
        if link.images_count > 0:
            max_images = self.download_manager.max_images_per_link
            if link.images_count > max_images:
                return f"Images ({link.images_count} > {max_images})"
        
        if link.file_size_mb > 0:
            max_size = self.download_manager.max_file_size_mb
            if link.file_size_mb > max_size:
                return f"Size ({link.file_size_mb:.2f} > {max_size}MB)"
        
        # Default to timeout if no other limit detected
        return "Timeout"
    
    def select_all(self) -> None:
        """Select all items."""
        for i in range(self.links_tree.topLevelItemCount()):
            item = self.links_tree.topLevelItem(i)
            if item:
                item.setSelected(True)
    
    def select_none(self) -> None:
        """Deselect all items."""
        self.links_tree.clearSelection()
    
    def override_selected(self) -> None:
        """Override limits and download selected links."""
        selected_items = self.links_tree.selectedItems()
        
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select links to override.")
            return
        
        # Confirm override
        reply = QMessageBox.warning(
            self,
            "Override Limits",
            f"Are you sure you want to override limits and download {len(selected_items)} links?\\n\\n"
            "These links were previously skipped for exceeding user-defined limits. "
            "Downloading them may take significant time and storage space.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Get selected link IDs
        link_ids = []
        for item in selected_items:
            link_id = item.data(0, Qt.ItemDataRole.UserRole)
            link_ids.append(link_id)
        
        try:
            # Start downloads for selected links
            # This would typically mark them for download and start a separate download thread
            success = self.download_manager.start_downloads(link_ids)
            
            if success:
                QMessageBox.information(
                    self,
                    "Download Started",
                    f"Started downloading {len(link_ids)} links in background thread."
                )
                self.accept()  # Close dialog
            else:
                QMessageBox.warning(
                    self,
                    "Download Failed",
                    "Failed to start downloads. Check if downloads are already running."
                )
        
        except Exception as e:
            logger.error(f"Error starting override downloads: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to start downloads: {str(e)}"
            )
