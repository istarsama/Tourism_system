# Project Plan: Tourism System (Campus + National)

## 📅 Current Status: Phase 1 Completed (2026-03-06)
**Milestone:** Backend Core, Dual-Mode Logic, and Basic Frontend Integration are complete and tested.

### ✅ Completed Tasks
#### 1. Backend Core & API
- [x] **Data Models**: Updated `Diary` model with `scope` ('campus', 'national') and `national_spot_id`.
- [x] **Map APIs**: Implemented `/map/national-spots` to fetch external spots.
- [x] **Navigation**: Integrated OpenStreetMap (OSM) service via `/navigate/osm` (mock/live fallback).
- [x] **Database**: Created `upgrade_database.py` to migrate existing MySQL data (add columns, fix nullable keys).

#### 2. Frontend Integration
- [x] **Mode Toggle**: Added UI switch for "Campus Guide" (Canvas) vs "National Travel" (List/OSM).
- [x] **National View**: Displayed national spots list with search and filtering.
- [x] **Diary Linkage**:
    - "View Diaries" now filters by scope automatically.
    - "Add Diary" context-aware (links to Campus Spot or National Spot based on mode).
- [x] **Route Planning UI**: Input panel for National navigation (Start/End/Transport Mode).

#### 3. Quality Assurance
- [x] **Unit Tests**: Added tests for `Diary` scope, `OSMService`, and Linkage logic.
- [x] **Integration Tests**: Verified full flows (Login -> Switch Mode -> Search -> Navigate -> Comment).
- [x] **Fixes**: Resolved database migration issues for `scope` column.

---

## 🚀 Phase 2: Visualization & Experience Upgrade (Next Steps)
**Goal:** Move from "Text/List" based National view to a rich "Map" based interface using Leaflet.js.

### 1. Frontend Visualization (Leaflet.js Integration)
- [ ] **Library Setup**: Import Leaflet.js (CDN or local) into `index.html`.
- [ ] **Map Container**: Create a separate DOM container `#national-map-container` (hidden in Campus mode).
- [ ] **Spot Rendering**: Render `national_spots` as markers on the Leaflet map.
- [ ] **Interactivity**: Click marker to show popup with "View Diaries" / "Navigate Here" buttons.

### 2. Navigation Visualization
- [ ] **Path Rendering**: Update `/navigate/osm` to return geometry (Polyline).
- [ ] **Draw Route**: Draw the calculated path on the Leaflet map.
- [ ] **Turn-by-Turn**: Display step-by-step instructions in the sidebar.

### 3. Polish & Refactor
- [ ] **State Management**: Refactor `app.js` to cleaner `CampusManager` and `NationalManager` classes.
- [ ] **Spot Details**: Add mock images and ratings to National Spots for better demo effect.

---

## 📝 Operational Notes
- **Database**: Production uses MySQL (dockerized), Dev uses SQLite.
- **Migration**: Always run `python tests/tools/upgrade_database.py` if pulling updates to a new environment.
- **Testing**: Run `uv run run_tests.py` before committing.
