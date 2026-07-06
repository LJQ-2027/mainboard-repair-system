# Board Atlas Guided Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first 2.5D board atlas guided-repair MVP for KM4/F151.

**Architecture:** The MVP uses rendered point-map PNGs as board image layers, `knowledge-base/board-atlas-mvp.json` as the board-atlas source of truth, and a frontend atlas viewer that overlays SVG modules, test points, and SOP state on top of the image.

**Tech Stack:** Existing HTML/JS beta app first, JSON data, SVG overlay, Poppler-based PDF rendering script. Later migration can use React/Next.js, OpenSeadragon, and Konva.

---

## File Structure

- `knowledge-base/board-atlas-mvp.json`: Board atlas data for KM4/F151, including sides, modules, test points, fault paths, and SOP steps.
- `scripts/build_board_atlas_assets.py`: Renders the KM4 point-map PDF into web-ready PNG files.
- `assets/board-atlas/km4-f151/`: Generated board-atlas PNG assets.
- `mainboard_repair_system_v7.4_updated.html`: Later frontend integration target for the atlas viewer.
- `docs/board-atlas-top20-material-audit.md`: Material sufficiency and gap assessment.

## Task 1: Validate Board Atlas Data And Render Assets

**Files:**
- Validate: `knowledge-base/board-atlas-mvp.json`
- Run: `scripts/build_board_atlas_assets.py`
- Generate: `assets/board-atlas/km4-f151/main-point-map-page-1.png`
- Generate: `assets/board-atlas/km4-f151/main-point-map-page-2.png`

- [ ] **Step 1: Parse the board atlas JSON**

Run:

```powershell
python -m json.tool knowledge-base/board-atlas-mvp.json > $null
```

Expected: command exits with code 0.

- [ ] **Step 2: Render KM4 point-map pages**

Run:

```powershell
python scripts/build_board_atlas_assets.py
```

Expected output contains:

```text
Rendered 2 board atlas page(s):
assets/board-atlas/km4-f151/main-point-map-page-1.png
assets/board-atlas/km4-f151/main-point-map-page-2.png
```

- [ ] **Step 3: Verify generated assets exist**

Run:

```powershell
Get-ChildItem assets/board-atlas/km4-f151 | Select-Object Name,Length
```

Expected: both PNG files exist and are non-empty.

## Task 2: Add A Minimal Atlas Viewer To The Existing Beta App

**Files:**
- Modify: `mainboard_repair_system_v7.4_updated.html`

- [ ] **Step 1: Add board atlas data loading**

Add `knowledge-base/board-atlas-mvp.json` to the existing knowledge data loader. Store it in the same in-memory knowledge state used by the other knowledge pages.

- [ ] **Step 2: Add a sidebar item named `主板图谱导诊`**

Wire the item to a new render function named `renderBoardAtlasGuide`.

- [ ] **Step 3: Render the board side selector**

Use the `sides` array from the first board. The default selected side is the first side.

- [ ] **Step 4: Render the board image**

Render the selected side image inside a stable aspect-ratio container. Use `position: relative` for the image wrapper.

- [ ] **Step 5: Render SVG overlay modules**

For each module matching the selected `side_id`, draw an SVG `polygon` using normalized coordinates multiplied by the rendered SVG viewBox size.

- [ ] **Step 6: Render fault choices**

Render all `fault_paths` as technician-facing choices. Selecting a fault highlights its `suspected_modules`.

- [ ] **Step 7: Render the SOP side panel**

When a fault is selected, show the first SOP step from `first_sop_step`. Include title, instruction, expected result, and status.

## Task 3: Interaction QA

**Files:**
- Verify: `mainboard_repair_system_v7.4_updated.html`
- Verify: `knowledge-base/board-atlas-mvp.json`

- [ ] **Step 1: Start a local static server**

Run:

```powershell
python -m http.server 8898
```

Expected: local server starts at `http://localhost:8898`.

- [ ] **Step 2: Open the beta app**

Open:

```text
http://localhost:8898/mainboard_repair_system_v7.4_updated.html
```

Expected: app loads without console errors.

- [ ] **Step 3: Check board atlas page**

Open `主板图谱导诊`. Confirm:

- KM4 board image is visible.
- Side switching works.
- Selecting `还不确定，先做初步主板排查` highlights draft modules.
- Selecting `不开机` highlights power and CPU/memory regions.
- Selecting `不充电` highlights charging and power regions.
- SOP side panel changes with selected fault.

- [ ] **Step 4: Check mobile viewport**

Use a mobile viewport around 390px wide. Confirm:

- Board image remains visible.
- Side panel stacks below or beside the image without overlap.
- Fault choices remain readable and tappable.

## Task 4: Closeout

**Files:**
- Review: `docs/board-atlas-top20-material-audit.md`
- Review: `docs/superpowers/specs/2026-07-06-board-atlas-guided-repair-design.md`
- Review: `docs/superpowers/plans/2026-07-06-board-atlas-guided-repair.md`
- Review: `knowledge-base/board-atlas-mvp.json`
- Review: `scripts/build_board_atlas_assets.py`
- Review: `assets/board-atlas/km4-f151/*`

- [ ] **Step 1: Run JSON parse**

Run:

```powershell
python -m json.tool knowledge-base/board-atlas-mvp.json > $null
```

- [ ] **Step 2: Run render script**

Run:

```powershell
python scripts/build_board_atlas_assets.py
```

- [ ] **Step 3: Run Git status**

Run:

```powershell
git status --short
```

- [ ] **Step 4: Commit once P0/P2 checks pass**

Run:

```powershell
git add docs/board-atlas-top20-material-audit.md docs/superpowers/specs/2026-07-06-board-atlas-guided-repair-design.md docs/superpowers/plans/2026-07-06-board-atlas-guided-repair.md knowledge-base/board-atlas-mvp.json scripts/build_board_atlas_assets.py assets/board-atlas/km4-f151
git commit -m "feat: add board atlas guided repair foundation"
```

