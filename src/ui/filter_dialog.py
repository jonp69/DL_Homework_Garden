"""
Dialog for creating and editing filters.
"""

import logging
from datetime import datetime
from typing import Optional, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton,
    QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem, QComboBox,
    QLabel, QMessageBox, QCheckBox, QSpinBox, QWidget
)

from ..core.filter_manager import LinkFilter, FilterRule, MatchType, FilterAction

logger = logging.getLogger(__name__)

class FilterDialog(QDialog):
    """Dialog for creating and editing link filters."""
    
    def __init__(self, parent=None, example_url: str = "", existing_filter: Optional[LinkFilter] = None):
        super().__init__(parent)
        self.example_url = example_url
        self.existing_filter = existing_filter
        self.is_editing = existing_filter is not None
        
        self.setup_ui()
        
        if self.existing_filter:
            self.load_filter(self.existing_filter)
        elif self.example_url:
            self.populate_from_url(self.example_url)
    
    def setup_ui(self) -> None:
        """Setup the user interface."""
        title = "Edit Filter" if self.is_editing else "Create New Filter"
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumSize(700, 500)
        
        layout = QVBoxLayout(self)
        
        # Filter basic info
        info_layout = self.create_info_section()
        layout.addLayout(info_layout)
        
        # Rules table
        rules_section = self.create_rules_section()
        layout.addWidget(rules_section)
        
        # Action selection
        action_section = self.create_action_section()
        layout.addLayout(action_section)
        
        # Buttons
        button_layout = self.create_button_section()
        layout.addLayout(button_layout)
    
    def create_info_section(self) -> QFormLayout:
        """Create the filter information section."""
        layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Optional; shown in UI only")
        layout.addRow("Name:", self.name_edit)
        
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Optional description")
        layout.addRow("Description:", self.description_edit)
        
        self.enabled_check = QCheckBox()
        self.enabled_check.setChecked(True)
        layout.addRow("Enabled:", self.enabled_check)
        
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(0, 1000)
        self.priority_spin.setValue(0)
        layout.addRow("Priority:", self.priority_spin)
        
        return layout
    
    def create_rules_section(self) -> QWidget:
        """Create the rules table section."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Title
        title_label = QLabel("Rules (positional; tokens must match in order):")
        title_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(title_label)
        
        # Example URL display
        if self.example_url:
            url_label = QLabel(f"Example URL: {self.example_url}")
            url_label.setStyleSheet("color: blue; font-style: italic;")
            url_label.setWordWrap(True)
            layout.addWidget(url_label)
        
        # Rules table
        self.rules_table = QTableWidget()
        self.rules_table.setColumnCount(3)
        self.rules_table.setHorizontalHeaderLabels(["Token", "Match Type", "Expression"])
        self.rules_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.rules_table)
        
        # Rules buttons
        rules_buttons = QHBoxLayout()
        
        self.btn_add_rule = QPushButton("Add Rule")
        self.btn_add_rule.clicked.connect(self.add_rule)
        rules_buttons.addWidget(self.btn_add_rule)
        
        self.btn_remove_rule = QPushButton("Remove Selected")
        self.btn_remove_rule.clicked.connect(self.remove_selected_rule)
        rules_buttons.addWidget(self.btn_remove_rule)
        
        rules_buttons.addStretch()
        
        layout.addLayout(rules_buttons)
        
        return container
    
    def create_action_section(self) -> QFormLayout:
        """Create the action selection section."""
        layout = QFormLayout()
        
        self.action_combo = QComboBox()
        self.action_combo.addItem("Mark as To Download", FilterAction.TO_DOWNLOAD.value)
        self.action_combo.addItem("Mark as To Skip", FilterAction.TO_SKIP.value)
        self.action_combo.addItem("Mark as Deleted", FilterAction.DELETED.value)
        self.action_combo.addItem("Ignore (never download)", FilterAction.IGNORE.value)
        self.action_combo.addItem("Skip (treat as non-existent)", FilterAction.SKIP.value)
        layout.addRow("Action:", self.action_combo)
        
        return layout
    
    def create_button_section(self) -> QHBoxLayout:
        """Create the dialog buttons."""
        layout = QHBoxLayout()
        layout.addStretch()
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        layout.addWidget(self.btn_cancel)
        
        button_text = "Update Filter" if self.is_editing else "Create Filter"
        self.btn_create = QPushButton(button_text)
        self.btn_create.clicked.connect(self.accept_filter)
        self.btn_create.setDefault(True)
        layout.addWidget(self.btn_create)
        
        return layout
    
    def populate_from_url(self, url: str) -> None:
        """Populate with ordered tokens (domain parts, then path segments, then query parts, then fragment)."""
        tokens = self._tokenize_url(url)
        for token in tokens:
            # Add each token as an EXACT rule by default
            self.add_rule(token)
        # Ensure UI reflects proper enabled state
        self.on_match_type_changed()
    
    def _tokenize_url(self, url: str) -> List[str]:
        """Tokenize URL into ordered granular tokens matching filter engine semantics."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        tokens: List[str] = []
        
        # Domain parts only (omit full netloc)
        if parsed.netloc:
            tokens.extend([p for p in parsed.netloc.split('.') if p])
        
        # Path segments only (omit full path)
        if parsed.path:
            tokens.extend([part for part in parsed.path.split('/') if part])
        
        # Query parts (key=value chunks)
        if parsed.query:
            tokens.extend([p for p in parsed.query.split('&') if p])
        
        # Fragment
        if parsed.fragment:
            tokens.append(parsed.fragment)
        
        return tokens
    
    def add_rule(self, token: str = "") -> None:
        """Add a new rule row."""
        row = self.rules_table.rowCount()
        self.rules_table.insertRow(row)
        
        # Token field
        token_item = QTableWidgetItem(token)
        self.rules_table.setItem(row, 0, token_item)
        
        # Match type combo
        match_combo = QComboBox()
        for match_type in MatchType:
            display_name = match_type.value.replace("_", " ").title()
            match_combo.addItem(display_name, match_type.value)
        
        # Default to CASE_INSENSITIVE
        default_index = match_combo.findData(MatchType.CASE_INSENSITIVE.value)
        if default_index < 0:
            default_index = 0
        match_combo.setCurrentIndex(default_index)
        
        self.rules_table.setCellWidget(row, 1, match_combo)
        
        # Expression field
        expression_item = QTableWidgetItem()
        self.rules_table.setItem(row, 2, expression_item)
        
        # Connect match type change to enable/disable expression
        match_combo.currentTextChanged.connect(self.on_match_type_changed)
        self.on_match_type_changed()  # Initialize state
    
    def remove_selected_rule(self) -> None:
        """Remove the selected rule row."""
        current_row = self.rules_table.currentRow()
        if current_row >= 0:
            self.rules_table.removeRow(current_row)
    
    def on_match_type_changed(self) -> None:
        """Handle match type change to enable/disable expression field."""
        for row in range(self.rules_table.rowCount()):
            match_combo = self.rules_table.cellWidget(row, 1)
            expression_item = self.rules_table.item(row, 2)
            
            if match_combo and expression_item:
                # QComboBox currentData()
                match_type = match_combo.currentData()  # type: ignore[attr-defined]
                needs_expression = match_type in [
                    MatchType.STARTS_WITH.value,
                    MatchType.ENDS_WITH.value,
                    MatchType.CONTAINS.value,
                    MatchType.NOT_CONTAINS.value,
                    MatchType.NOT_STARTS_WITH.value,
                    MatchType.NOT_ENDS_WITH.value,
                    MatchType.REGEX.value,
                    MatchType.NOT_REGEX.value,
                    MatchType.EXPRESSION.value
                ]
                
                if needs_expression:
                    expression_item.setFlags(expression_item.flags() | Qt.ItemFlag.ItemIsEnabled)
                    expression_item.setBackground(self.palette().color(self.palette().ColorRole.Base))
                else:
                    expression_item.setFlags(expression_item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                    expression_item.setBackground(self.palette().color(self.palette().ColorRole.Window))
                    expression_item.setText("")
    
    def load_filter(self, filter_obj: LinkFilter) -> None:
        """Load an existing filter into the dialog."""
        self.name_edit.setText(filter_obj.name)
        self.description_edit.setText(filter_obj.description)
        self.enabled_check.setChecked(filter_obj.enabled)
        self.priority_spin.setValue(filter_obj.priority)
        
        # Set action
        action_index = self.action_combo.findData(filter_obj.action.value)
        if action_index >= 0:
            self.action_combo.setCurrentIndex(action_index)
        
        # Load rules
        for rule in filter_obj.rules:
            row = self.rules_table.rowCount()
            self.rules_table.insertRow(row)
            
            # Token
            token_item = QTableWidgetItem(rule.token)
            self.rules_table.setItem(row, 0, token_item)
            
            # Match type
            match_combo = QComboBox()
            for match_type in MatchType:
                display_name = match_type.value.replace("_", " ").title()
                match_combo.addItem(display_name, match_type.value)
            
            match_index = match_combo.findData(rule.match_type.value)
            if match_index >= 0:
                match_combo.setCurrentIndex(match_index)
            
            self.rules_table.setCellWidget(row, 1, match_combo)
            
            # Expression
            expression_item = QTableWidgetItem(rule.expression)
            self.rules_table.setItem(row, 2, expression_item)
            
            # Connect signal
            match_combo.currentTextChanged.connect(self.on_match_type_changed)
        
        self.on_match_type_changed()
    
    def accept_filter(self) -> None:
        """Validate and accept the filter."""
        # Name is optional; do not enforce
        
        # Validate rules
        rules = self.get_rules()
        if not rules:
            QMessageBox.warning(self, "Validation Error", "At least one rule is required.")
            return
        
        # Validate that expressions are provided where needed
        for i, rule in enumerate(rules):
            if rule.match_type in [
                MatchType.STARTS_WITH, MatchType.ENDS_WITH, MatchType.CONTAINS,
                MatchType.NOT_CONTAINS, MatchType.NOT_STARTS_WITH, 
                MatchType.NOT_ENDS_WITH, MatchType.REGEX, MatchType.NOT_REGEX,
                MatchType.EXPRESSION
            ] and not rule.expression.strip():
                QMessageBox.warning(
                    self, 
                    "Validation Error", 
                    f"Rule {i+1} requires an expression for the selected match type."
                )
                return
        
        self.accept()
    
    def get_rules(self) -> List[FilterRule]:
        """Get rules from the table."""
        rules = []
        
        for row in range(self.rules_table.rowCount()):
            token_item = self.rules_table.item(row, 0)
            match_combo = self.rules_table.cellWidget(row, 1)
            expression_item = self.rules_table.item(row, 2)
            
            if token_item and match_combo:
                token = token_item.text().strip()
                match_type_value = match_combo.currentData()  # type: ignore[attr-defined]
                expression = expression_item.text() if expression_item else ""
                
                if token and match_type_value:
                    try:
                        match_type = MatchType(match_type_value)
                        rule = FilterRule(token, match_type, expression.strip())
                        rules.append(rule)
                    except ValueError as e:
                        logger.error(f"Invalid match type: {match_type_value}")
        
        return rules
    
    def get_filter(self) -> LinkFilter:
        """Get the filter from the dialog."""
        rules = self.get_rules()
        action_value = self.action_combo.currentData()
        action = FilterAction(action_value)
        
        # Ensure a display name; if empty, assign Unnamed_NNN using numeric id placeholder
        name_text = self.name_edit.text().strip()
        if not name_text:
            name_text = "Unnamed"
        
        # Create or update filter
        if self.existing_filter:
            filter_obj = self.existing_filter
            filter_obj.name = name_text
            filter_obj.description = self.description_edit.text().strip()
            filter_obj.enabled = self.enabled_check.isChecked()
            filter_obj.priority = self.priority_spin.value()
            filter_obj.rules = rules
            filter_obj.action = action
            filter_obj.modified_timestamp = datetime.now().isoformat()
        else:
            filter_obj = LinkFilter(
                name=name_text,
                rules=rules,
                action=action,
                description=self.description_edit.text().strip(),
                enabled=self.enabled_check.isChecked(),
                priority=self.priority_spin.value(),
                created_timestamp=datetime.now().isoformat()
            )
        
        return filter_obj
