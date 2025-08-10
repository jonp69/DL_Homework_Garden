# Requirements Coverage

This document tracks the current coverage of the project’s functional and non-functional requirements.

## Coverage

- URL ingestion from files and clipboard
  - Status: Done
  - Notes: Text files parsed via UI; clipboard captured and saved to Link_files.

- Centralized storage under `Link_files` subfolder
  - Status: Done
  - Notes: Folder auto-created; dialogs default there; clipboard saves there.

- Non-destructive deletes (append-only semantics for links)
  - Status: Done
  - Notes: Links persist with `deleted` flag; no hard removal from JSON.

- Links persistence (`links.json`)
  - Status: Done
  - Notes: Append/reactivate behavior; full re-save of entries; maintains deleted entries.

- Filters management and matching
  - Status: Done
  - Notes: Positional, per-token matching (domain parts → path segments → query → fragment). First-match wins by priority.

- Filter creation UX
  - Status: Done
  - Notes: Dialog pre-fills ordered tokens; default match type is CASE_INSENSITIVE; names optional.

- Stable filter identifiers
  - Status: Done
  - Notes: Each filter has `numeric_id` (persisted). Links store `filter_matched_id`; display name resolved via a resolver.

- Filter name resolver (id → name)
  - Status: Done
  - Notes: Dedicated class loads from `filters.json`; UI resolves names at display time; refreshes on changes.

- Display filter names in UI while storing stable IDs
  - Status: Done
  - Notes: Link list, download progress, and skipped dialog resolve names from `filter_matched_id`.

- Cancel behavior when selecting directory
  - Status: Done
  - Notes: Cancel results in no action.

- Trailing URL closer trimming prompt
  - Status: Done
  - Notes: Optional prompt removes trailing ) ] } ' " characters.

- Window geometry persistence
  - Status: Done
  - Notes: Saved/restored in config via base64.

- Thread-safe UI updates and limit prompts
  - Status: Done
  - Notes: Background callbacks marshaled via Qt signals; blocking decision with event.

- Remove site-specific logic (e.g., Pixiv)
  - Status: Done
  - Notes: Generic URL handling; no auto site filters.

- Reprocess links after filter changes
  - Status: Done
  - Notes: Silent re-apply of filters to active links.

- Gallery-dl integration for downloads
  - Status: Done (basic)
  - Notes: Downloads managed with progress callbacks; limits prompt supported. Detailed output parsing deferred.

## Deferred / Future Work

- Harden URL extraction regex
  - Reason: Improve stripping of closers, parentheses balancing, and scheme-less URLs.

- Parse gallery-dl JSON output for precise counts/sizes
  - Reason: Capture images and size accurately; store limit reason in link metadata.

- Store explicit limit reason in link metadata
  - Reason: Needed for better reporting in UI.

- Filter creation UX refinements
  - Reason: Additional templates and smarter defaults beyond current behavior.

- Tests (unit/integration)
  - Reason: Add coverage for core managers, filters, and UI logic.

- Migration tool to convert legacy `filter_matched` names → `filter_matched_id`
  - Reason: Optional one-off to normalize existing `links.json`.

## Quality Gates (current)

- Build/Compile: PASS (syntax check on updated modules)
- Lint/Typecheck: Not configured
- Unit Tests: Not present
- Smoke Test: App launches; basic workflows function (per recent manual checks)
