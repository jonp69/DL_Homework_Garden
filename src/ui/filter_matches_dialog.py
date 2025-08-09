"""
Dialog for viewing links that match a specific filter.
"""

import logging
from typing import List

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget,
    QTreeWidgetItem, QHeaderView, QLabel, QComboBox, QMessageBox
)

from ..core.filter_manager import LinkFilter
from ..core.link_manager import LinkMetadata, LinkStatus

logger = logging.getLogger(__name__)

class FilterMatchesDialog(QDialog):
    """Dialog for viewing links that match a specific filter."""
    
    def __init__(self, parent, filter_obj: LinkFilter):
        super().__init__(parent)
        self.filter_obj = filter_obj
        self.matching_links: List[LinkMetadata] = []
        
        # Get link manager from parent - traverse up to find main window
        self.link_manager = None
        current_parent = parent
        while current_parent and not hasattr(current_parent, 'link_manager'):
            current_parent = current_parent.parent() if hasattr(current_parent, 'parent') else None
        
        if current_parent:
            self.link_manager = current_parent.link_manager
        
        self.setup_ui()
        self.find_matching_links()
        self.populate_links()
    
    def setup_ui(self) -> None:
        """Setup the user interface."""
        self.setWindowTitle(f"Links Matching Filter: {self.filter_obj.name}")
        self.setModal(True)
        self.setMinimumSize(900, 600)
        
        layout = QVBoxLayout(self)
        
        # Header with filter info
        header_label = QLabel(f"Filter: {self.filter_obj.name}")
        header_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header_label)
        
        if self.filter_obj.description:
            desc_label = QLabel(self.filter_obj.description)
            desc_label.setStyleSheet("font-style: italic; color: gray;")
            layout.addWidget(desc_label)
        
        # Filter details
        action_text = self.filter_obj.action.value.replace("_", " ").title()
        details_label = QLabel(f"Action: {action_text} | Rules: {len(self.filter_obj.rules)} | Enabled: {self.filter_obj.enabled}")
        layout.addWidget(details_label)
        
        # Links tree
        self.links_tree = QTreeWidget()
        self.links_tree.setHeaderLabels([
            "URL", "Status", "Source", "Images", "Size (MB)", "Added"
        ])
        self.links_tree.setSelectionMode(QTreeWidget.SelectionMode.MultiSelection)
        
        # Configure column widths
        header = self.links_tree.header()
        header.resizeSection(0, 400)  # URL
        header.resizeSection(1, 100)  # Status
        header.resizeSection(2, 80)   # Source
        header.resizeSection(3, 60)   # Images
        header.resizeSection(4, 80)   # Size
        header.setStretchLastSection(True)  # Added
        
        layout.addWidget(self.links_tree)
        
        # Action controls
        action_layout = QHBoxLayout()
        
        action_layout.addWidget(QLabel("Change status of selected links to:"))
        
        self.status_combo = QComboBox()
        self.status_combo.addItem("To Download", LinkStatus.TO_DOWNLOAD.value)
        self.status_combo.addItem("To Skip", LinkStatus.TO_SKIP.value)
        self.status_combo.addItem("To Reprocess", LinkStatus.TO_REPROCESS.value)
        self.status_combo.addItem("Mark as Deleted", "deleted")
        action_layout.addWidget(self.status_combo)
        
        self.btn_apply_status = QPushButton("Apply to Selected")
        self.btn_apply_status.clicked.connect(self.apply_status_to_selected)
        action_layout.addWidget(self.btn_apply_status)
        
        action_layout.addStretch()
        
        layout.addLayout(action_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.clicked.connect(self.select_all)
        button_layout.addWidget(self.btn_select_all)
        
        self.btn_select_none = QPushButton("Select None")
        self.btn_select_none.clicked.connect(self.select_none)
        button_layout.addWidget(self.btn_select_none)
        
        button_layout.addStretch()
        
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh)
        button_layout.addWidget(self.btn_refresh)
        
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        button_layout.addWidget(self.btn_close)
        
        layout.addLayout(button_layout)
    
    def find_matching_links(self) -> None:
        """Find all links that match the filter."""
        self.matching_links.clear()
        
        if not self.link_manager:
            return
        
        # Get all active links
        all_links = self.link_manager.get_active_links()
        
        # Test each link against the filter
        for link in all_links:
            if self.filter_obj.matches(link.url):
                self.matching_links.append(link)
        
        logger.debug(f"Found {len(self.matching_links)} links matching filter '{self.filter_obj.name}'")
    
    def populate_links(self) -> None:
        """Populate the links tree."""
        self.links_tree.clear()
        
        for link in self.matching_links:
            item = QTreeWidgetItem(self.links_tree)
            
            # Store link ID for reference
            item.setData(0, Qt.ItemDataRole.UserRole, link.id)
            
            # Set column data
            item.setText(0, link.url)
            item.setText(1, link.status.value.replace("_", " ").title())
            item.setText(2, link.source.title())
            item.setText(3, str(link.images_count) if link.images_count > 0 else "")
            item.setText(4, f"{link.file_size_mb:.2f}" if link.file_size_mb > 0 else "")
            
            # Format timestamp
            if link.added_timestamp:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(link.added_timestamp.replace('Z', '+00:00'))
                    formatted_time = dt.strftime("%Y-%m-%d %H:%M")
                    item.setText(5, formatted_time)
                except:
                    item.setText(5, link.added_timestamp)
            
            # Set color based on status
            self.set_item_color(item, link.status)
            
            # Set tooltip
            tooltip = f"URL: {link.url}\\nStatus: {link.status.value}\\nSource: {link.source}"
            if link.error_message:
                tooltip += f"\\nError: {link.error_message}"
            item.setToolTip(0, tooltip)
        
        # Update dialog title with count
        self.setWindowTitle(f"Links Matching Filter: {self.filter_obj.name} ({len(self.matching_links)} links)")
    
    def set_item_color(self, item: QTreeWidgetItem, status: LinkStatus) -> None:
        """Set item color based on status."""
        color = None
        
        if status == LinkStatus.TO_DOWNLOAD:
            color = QColor("lightgreen")
        elif status == LinkStatus.DOWNLOADING:
            color = QColor("lightblue")
        elif status == LinkStatus.DOWNLOADED:
            color = QColor("darkgreen")
        elif status == LinkStatus.TO_SKIP:
            color = QColor("yellow")
        elif status == LinkStatus.TO_SKIP_LIMIT:
            color = QColor("orange")
        elif status == LinkStatus.SKIPPED:
            color = QColor("lightgray")
        elif status == LinkStatus.ERROR:
            color = QColor("lightcoral")
        elif status == LinkStatus.TO_REPROCESS:
            color = QColor("lightyellow")
        
        if color:
            for column in range(self.links_tree.columnCount()):
                item.setBackground(column, color)
    
    def select_all(self) -> None:
        """Select all items."""
        for i in range(self.links_tree.topLevelItemCount()):
            item = self.links_tree.topLevelItem(i)
            if item:
                item.setSelected(True)
    
    def select_none(self) -> None:
        """Deselect all items."""
        self.links_tree.clearSelection()
    
    def refresh(self) -> None:
        """Refresh the links list."""
        self.find_matching_links()
        self.populate_links()
    
    def apply_status_to_selected(self) -> None:
        """Apply the selected status to selected links."""
        selected_items = self.links_tree.selectedItems()
        
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select links to modify.")
            return
        
        status_value = self.status_combo.currentData()
        status_text = self.status_combo.currentText()
        
        # Confirm action
        reply = QMessageBox.question(
            self,
            "Confirm Status Change",
            f"Change status of {len(selected_items)} selected links to '{status_text}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            if not self.link_manager:
                QMessageBox.critical(self, "Error", "Cannot access link manager.")
                return
            
            # Apply status changes
            changed_count = 0
            for item in selected_items:
                link_id = item.data(0, Qt.ItemDataRole.UserRole)
                
                if status_value == "deleted":
                    if self.link_manager.mark_deleted(link_id):
                        changed_count += 1
                else:
                    status = LinkStatus(status_value)
                    if self.link_manager.update_link_status(link_id, status):
                        changed_count += 1
            
            # Refresh the display
            self.refresh()
            
            QMessageBox.information(
                self,
                "Status Updated",
                f"Successfully updated {changed_count} links to '{status_text}'."
            )
            
        except Exception as e:
            logger.error(f"Error updating link status: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to update link status: {str(e)}"
            )
