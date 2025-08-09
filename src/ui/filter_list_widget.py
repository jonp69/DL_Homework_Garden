"""
Filter management widget for the main window.
"""

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QLabel, QMessageBox, QDialog
)

from ..core.filter_manager import FilterManager, LinkFilter

logger = logging.getLogger(__name__)

class FilterListWidget(QWidget):
    """Widget for managing filters list."""
    
    filter_changed = Signal()
    reprocess_requested = Signal()
    
    def __init__(self, filter_manager: FilterManager):
        super().__init__()
        self.filter_manager = filter_manager
        self.setup_ui()
        self.refresh()
    
    def setup_ui(self) -> None:
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Filter list
        self.filter_list = QListWidget()
        self.filter_list.currentItemChanged.connect(self.on_selection_changed)
        layout.addWidget(self.filter_list)
        
        # Button layout for selected filter
        self.button_layout = QHBoxLayout()
        
        self.btn_edit = QPushButton("Edit")
        self.btn_edit.clicked.connect(self.edit_filter)
        self.btn_edit.setEnabled(False)
        self.button_layout.addWidget(self.btn_edit)
        
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.clicked.connect(self.delete_filter)
        self.btn_delete.setEnabled(False)
        self.button_layout.addWidget(self.btn_delete)
        
        self.btn_move_up = QPushButton("↑")
        self.btn_move_up.clicked.connect(self.move_filter_up)
        self.btn_move_up.setEnabled(False)
        self.button_layout.addWidget(self.btn_move_up)
        
        self.btn_move_down = QPushButton("↓")
        self.btn_move_down.clicked.connect(self.move_filter_down)
        self.btn_move_down.setEnabled(False)
        self.button_layout.addWidget(self.btn_move_down)
        
        self.btn_view = QPushButton("View")
        self.btn_view.clicked.connect(self.view_filter_matches)
        self.btn_view.setEnabled(False)
        self.button_layout.addWidget(self.btn_view)
        
        layout.addLayout(self.button_layout)
    
    def refresh(self) -> None:
        """Refresh the filter list."""
        self.filter_list.clear()
        
        for filter_obj in self.filter_manager.filters:
            item = QListWidgetItem()
            
            # Create display text
            enabled_text = "✓" if filter_obj.enabled else "✗"
            action_text = filter_obj.action.value.replace("_", " ").title()
            display_text = f"{enabled_text} {filter_obj.name} → {action_text}"
            
            if filter_obj.description:
                display_text += f" ({filter_obj.description})"
            
            item.setText(display_text)
            item.setData(Qt.ItemDataRole.UserRole, filter_obj.id)
            
            # Set color based on action
            if filter_obj.action.value == "to_download":
                item.setBackground(QColor("lightgreen"))
            elif filter_obj.action.value == "to_skip":
                item.setBackground(QColor("yellow"))
            elif filter_obj.action.value == "deleted":
                item.setBackground(QColor("lightcoral"))
            
            # Disable appearance if filter is disabled
            if not filter_obj.enabled:
                item.setForeground(QColor("gray"))
            
            self.filter_list.addItem(item)
    
    def on_selection_changed(self, current: Optional[QListWidgetItem], 
                           previous: Optional[QListWidgetItem]) -> None:
        """Handle filter selection change."""
        has_selection = current is not None
        
        self.btn_edit.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)
        self.btn_view.setEnabled(has_selection)
        
        # Enable move buttons based on position
        if has_selection:
            row = self.filter_list.row(current)
            self.btn_move_up.setEnabled(row > 0)
            self.btn_move_down.setEnabled(row < self.filter_list.count() - 1)
        else:
            self.btn_move_up.setEnabled(False)
            self.btn_move_down.setEnabled(False)
    
    def get_selected_filter(self) -> Optional[LinkFilter]:
        """Get the currently selected filter."""
        current_item = self.filter_list.currentItem()
        if not current_item:
            return None
        
        filter_id = current_item.data(Qt.ItemDataRole.UserRole)
        for filter_obj in self.filter_manager.filters:
            if filter_obj.id == filter_id:
                return filter_obj
        
        return None
    
    def edit_filter(self) -> None:
        """Edit the selected filter."""
        filter_obj = self.get_selected_filter()
        if not filter_obj:
            return
        
        # Import here to avoid circular imports
        from .filter_dialog import FilterDialog
        
        dialog = FilterDialog(self, existing_filter=filter_obj)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_filter = dialog.get_filter()
            self.filter_manager.update_filter(updated_filter)
            self.refresh()
            self.filter_changed.emit()
    
    def delete_filter(self) -> None:
        """Delete the selected filter."""
        filter_obj = self.get_selected_filter()
        if not filter_obj:
            return
        
        reply = QMessageBox.question(
            self,
            "Delete Filter",
            f"Are you sure you want to delete the filter '{filter_obj.name}'?\\n\\n"
            "This will mark all matching links for reprocessing.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.filter_manager.remove_filter(filter_obj.id)
            self.refresh()
            self.filter_changed.emit()
            # Request reprocessing of affected links
            self.reprocess_requested.emit()
            logger.info(f"Deleted filter: {filter_obj.name}")
    
    def move_filter_up(self) -> None:
        """Move selected filter up in priority."""
        filter_obj = self.get_selected_filter()
        if not filter_obj:
            return
        
        if self.filter_manager.move_filter(filter_obj.id, "up"):
            self.refresh()
            self.filter_changed.emit()
            logger.debug(f"Moved filter '{filter_obj.name}' up")
    
    def move_filter_down(self) -> None:
        """Move selected filter down in priority."""
        filter_obj = self.get_selected_filter()
        if not filter_obj:
            return
        
        if self.filter_manager.move_filter(filter_obj.id, "down"):
            self.refresh()
            self.filter_changed.emit()
            logger.debug(f"Moved filter '{filter_obj.name}' down")
    
    def view_filter_matches(self) -> None:
        """View links that match the selected filter."""
        filter_obj = self.get_selected_filter()
        if not filter_obj:
            return
        
        # Import here to avoid circular imports
        from .filter_matches_dialog import FilterMatchesDialog
        
        dialog = FilterMatchesDialog(self, filter_obj)
        dialog.exec()
