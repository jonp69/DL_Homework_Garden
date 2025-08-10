"""
Widget for displaying and managing the list of links.
"""

import logging
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget,
    QTreeWidgetItem, QHeaderView, QComboBox, QLineEdit, QLabel
)

from ..core.link_manager import LinkManager, LinkMetadata, LinkStatus
from ..core.filter_name_resolver import FilterNameResolver

logger = logging.getLogger(__name__)

class LinkListWidget(QWidget):
    """Widget for displaying and managing links."""
    
    links_updated = Signal()
    
    def __init__(self, link_manager: LinkManager, name_resolver: Optional[FilterNameResolver] = None):
        super().__init__()
        self.link_manager = link_manager
        self.name_resolver = name_resolver
        self.setup_ui()
        self.refresh()
    
    def setup_ui(self) -> None:
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Filter controls
        filter_layout = self.create_filter_controls()
        layout.addLayout(filter_layout)
        
        # Links tree
        self.links_tree = QTreeWidget()
        self.links_tree.setHeaderLabels([
            "URL", "Status", "Source", "Filter", "Images", "Size (MB)", "Added", "Error"
        ])
        
        # Configure column widths
        header = self.links_tree.header()
        header.resizeSection(0, 300)  # URL
        header.resizeSection(1, 100)  # Status
        header.resizeSection(2, 80)   # Source
        header.resizeSection(3, 120)  # Filter
        header.resizeSection(4, 60)   # Images
        header.resizeSection(5, 80)   # Size
        header.resizeSection(6, 120)  # Added
        header.setStretchLastSection(True)  # Error
        
        layout.addWidget(self.links_tree)
        
        # Action buttons
        button_layout = self.create_action_buttons()
        layout.addLayout(button_layout)
    
    def create_filter_controls(self) -> QHBoxLayout:
        """Create filter controls for the link list."""
        layout = QHBoxLayout()

        # Status filter
        layout.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItem("All", "all")
        self.status_filter.addItem("Pending", LinkStatus.PENDING.value)
        self.status_filter.addItem("To Download", LinkStatus.TO_DOWNLOAD.value)
        self.status_filter.addItem("To Skip", LinkStatus.TO_SKIP.value)
        self.status_filter.addItem("Ignored", LinkStatus.IGNORED.value)
        self.status_filter.addItem("Downloaded", LinkStatus.DOWNLOADED.value)
        self.status_filter.addItem("Skipped", LinkStatus.SKIPPED.value)
        self.status_filter.addItem("Error", LinkStatus.ERROR.value)
        self.status_filter.currentTextChanged.connect(self.refresh)
        layout.addWidget(self.status_filter)

        # URL search
        layout.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search URLs...")
        self.search_edit.textChanged.connect(self.refresh)
        layout.addWidget(self.search_edit)

        layout.addStretch()

        # Refresh button
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh)
        layout.addWidget(self.btn_refresh)

        return layout
    
    def create_action_buttons(self) -> QHBoxLayout:
        """Create action buttons for selected links."""
        layout = QHBoxLayout()
        
        self.btn_mark_download = QPushButton("Mark for Download")
        self.btn_mark_download.clicked.connect(self.mark_selected_download)
        layout.addWidget(self.btn_mark_download)
        
        self.btn_mark_skip = QPushButton("Mark to Skip")
        self.btn_mark_skip.clicked.connect(self.mark_selected_skip)
        layout.addWidget(self.btn_mark_skip)
        
        self.btn_mark_delete = QPushButton("Mark as Deleted")
        self.btn_mark_delete.clicked.connect(self.mark_selected_deleted)
        layout.addWidget(self.btn_mark_delete)
        
        layout.addStretch()
        
        self.btn_reprocess = QPushButton("Reprocess Selected")
        self.btn_reprocess.clicked.connect(self.reprocess_selected)
        layout.addWidget(self.btn_reprocess)
        
        return layout
    
    def refresh(self) -> None:
        """Refresh the links tree."""
        self.links_tree.clear()
        
        # Get filtered links
        links = self.get_filtered_links()
        
        # Add links to tree
        for link in links:
            self.add_link_item(link)
        
        self.links_updated.emit()
    
    def get_filtered_links(self) -> List[LinkMetadata]:
        """Get filtered list of links based on current filters."""
        # Get all active links (non-deleted)
        links = self.link_manager.get_active_links()
        
        # Filter by status
        status_filter = self.status_filter.currentData()
        if status_filter != "all":
            links = [link for link in links if link.status.value == status_filter]
        
        # Filter by search text
        search_text = self.search_edit.text().strip().lower()
        if search_text:
            links = [link for link in links if search_text in link.url.lower()]
        
        # Sort by added timestamp (newest first)
        links.sort(key=lambda x: x.added_timestamp, reverse=True)
        
        return links
    
    def add_link_item(self, link: LinkMetadata) -> QTreeWidgetItem:
        """Add a link item to the tree."""
        item = QTreeWidgetItem(self.links_tree)
        
        # Store link ID for reference
        item.setData(0, Qt.ItemDataRole.UserRole, link.id)
        
        # Resolve filter display name
        filter_display = ""
        if getattr(link, 'filter_matched_id', None) is not None and self.name_resolver:
            filter_display = self.name_resolver.resolve(link.filter_matched_id)  # type: ignore[arg-type]
        elif link.filter_matched:
            filter_display = link.filter_matched
        
        # Set column data
        item.setText(0, link.url)
        item.setText(1, link.status.value.replace("_", " ").title())
        item.setText(2, link.source.title())
        item.setText(3, filter_display)
        item.setText(4, str(link.images_count) if link.images_count > 0 else "")
        item.setText(5, f"{link.file_size_mb:.2f}" if link.file_size_mb > 0 else "")
        
        # Format timestamp
        if link.added_timestamp:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(link.added_timestamp.replace('Z', '+00:00'))
                formatted_time = dt.strftime("%Y-%m-%d %H:%M")
                item.setText(6, formatted_time)
            except:
                item.setText(6, link.added_timestamp)
        
        item.setText(7, link.error_message)
        
        # Set color based on status
        self.set_item_color(item, link.status)
        
        # Set tooltip
        tooltip = f"URL: {link.url}\nStatus: {link.status.value}\nSource: {link.source}"
        if filter_display:
            tooltip += f"\nFilter: {filter_display}"
        if link.error_message:
            tooltip += f"\nError: {link.error_message}"
        item.setToolTip(0, tooltip)
        
        return item
    
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
        elif status == LinkStatus.IGNORED:
            color = QColor("khaki")
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
    
    def get_selected_links(self) -> List[LinkMetadata]:
        """Get currently selected links."""
        selected_items = self.links_tree.selectedItems()
        links = []
        
        for item in selected_items:
            link_id = item.data(0, Qt.ItemDataRole.UserRole)
            link = self.link_manager.get_link_by_id(link_id)
            if link:
                links.append(link)
        
        return links
    
    def mark_selected_download(self) -> None:
        """Mark selected links for download."""
        selected_links = self.get_selected_links()
        for link in selected_links:
            if not link.deleted:
                self.link_manager.update_link_status(link.id, LinkStatus.TO_DOWNLOAD)
        
        self.refresh()
        logger.info(f"Marked {len(selected_links)} links for download")
    
    def mark_selected_skip(self) -> None:
        """Mark selected links to skip."""
        selected_links = self.get_selected_links()
        for link in selected_links:
            if not link.deleted:
                self.link_manager.update_link_status(link.id, LinkStatus.TO_SKIP)
        
        self.refresh()
        logger.info(f"Marked {len(selected_links)} links to skip")
    
    def mark_selected_deleted(self) -> None:
        """Mark selected links as deleted."""
        selected_links = self.get_selected_links()
        for link in selected_links:
            self.link_manager.mark_deleted(link.id)
        
        self.refresh()
        logger.info(f"Marked {len(selected_links)} links as deleted")
    
    def reprocess_selected(self) -> None:
        """Mark selected links for reprocessing."""
        selected_links = self.get_selected_links()
        for link in selected_links:
            if not link.deleted:
                self.link_manager.update_link_status(link.id, LinkStatus.TO_REPROCESS)
        
        self.refresh()
        logger.info(f"Marked {len(selected_links)} links for reprocessing")
    
    def refresh_link(self, link_id: str) -> None:
        """Refresh a specific link item."""
        # Find the item
        for i in range(self.links_tree.topLevelItemCount()):
            item = self.links_tree.topLevelItem(i)
            if item and item.data(0, Qt.ItemDataRole.UserRole) == link_id:
                # Get updated link
                link = self.link_manager.get_link_by_id(link_id)
                if link and not link.deleted:
                    # Update item
                    item.setText(1, link.status.value.replace("_", " ").title())
                    item.setText(4, str(link.images_count) if link.images_count > 0 else "")
                    item.setText(5, f"{link.file_size_mb:.2f}" if link.file_size_mb > 0 else "")
                    item.setText(7, link.error_message)
                    # Update filter display name
                    filter_display = ""
                    if getattr(link, 'filter_matched_id', None) is not None and self.name_resolver:
                        filter_display = self.name_resolver.resolve(link.filter_matched_id)  # type: ignore[arg-type]
                    elif link.filter_matched:
                        filter_display = link.filter_matched
                    item.setText(3, filter_display)
                    
                    # Update color
                    self.set_item_color(item, link.status)
                elif link and link.deleted:
                    # Remove deleted item
                    self.links_tree.takeTopLevelItem(i)
                
                break
