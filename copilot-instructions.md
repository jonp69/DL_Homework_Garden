<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

<!-- Workspace-specific Copilot instructions for DL_Homework_Garden -->

# Project Overview
This project is a Python tool for processing and filtering links from files and clipboard for use with gallery-dl. It features a PySide6 GUI for managing, filtering, and downloading links, with persistent, append-only tracking of all links and their metadata.

# Key Requirements
- **Persistent, append-only link tracking:**
  - No link is ever removed from `links.json`. All removals or ignores must be done by metadata (e.g., `deleted: true`).
  - Even if a link is deleted in the UI or by user action, it must remain in `links.json` with `deleted: true`.
- **UI and Logic:**
  - All UI elements (tree view, text box, etc.) must always filter out links with `deleted: true` and never show or process them.
  - Loading from file/clipboard always adds (never replaces) links.
  - Resume only queues links with status `pending` (not `downloaded`, `skipped`, `error`, or `deleted`).
  - Retry only queues links with status `skipped`, `error`, or `pending` (not `downloaded` or `deleted`).
  - Filters allow temporary ignoring of links (not removal or deletion).
- **No destructive operations:**
  - Never remove or drop entries from `links.json` or in-memory structures except for temporary UI filtering.
  - Never delete or clear metadata for any link.
- **Concurrency and error handling:**
  - Accurate state management for downloads, concurrency, and error handling.
  - Robust handling of gallery-dl output for image/output line counting.
- **Diagnostics:**
  - Provide debug output for resume/retry and file handling as needed.

# Corrections and Best Practices
- All method definitions must be unique and it must use the metadata-driven model.
- Never use destructive removal of links or their metadata. All removals must be by setting `deleted: true`.
- All UI and logic must always filter out `deleted: true` links.

# Summary
- **Never remove links from `links.json`**—use `deleted: true` in metadata.
- **No duplicate method definitions**—keep only the correct, metadata-driven versions.
- **UI and logic must always filter out deleted links.**
- **No references to non-existent methods.**
- **All changes must be robust, Windows-compatible, and follow the above rules.**
