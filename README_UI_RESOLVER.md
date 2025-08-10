# Filter Name Resolver UI Wiring

This change introduces a dedicated `FilterNameResolver` class to map `numeric_id` values from links to the current human-readable filter names stored in `filters.json`.

- `src/core/filter_name_resolver.py`: Loads names from `filters.json`, provides a `resolve(id)->name` method, and `refresh()` to reload.
- UI updates:
  - `MainWindow` creates and refreshes a singleton resolver, passes it to `LinkListWidget`, `DownloadProgressWidget`, and `LimitSkipDialog`.
  - Each widget resolves `link.filter_matched_id` via the resolver for display. `filter_matched` remains for backward compatibility.
- `FilterDialog` defaults match type to CASE_INSENSITIVE and makes names optional. `FilterManager` assigns `Unnamed_NNN` when missing and persists a stable `numeric_id`.

If you edit filter names in `filters.json`, the UI will pick up changes when filters are reloaded or when `FilterListWidget` emits `filter_changed` (triggering a resolver refresh).
