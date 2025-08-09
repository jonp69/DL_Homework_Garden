#!/usr/bin/env python3
"""
DL Homework Garden - Main Application
A Python tool for processing and filtering links from files and clipboard for use with gallery-dl.
"""

import sys
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.core.config import Config
from src.utils.logger import setup_logging

def main():
    """Main application entry point."""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("DL Homework Garden")
    app.setApplicationVersion("1.0.0")
    
    # Initialize configuration
    config = Config()
    
    # Create and show main window
    main_window = MainWindow(config)
    main_window.show()
    
    logger.info("Application started")
    
    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
