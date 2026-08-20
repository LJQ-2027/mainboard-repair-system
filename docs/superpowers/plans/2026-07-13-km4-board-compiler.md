# KM4/F151 Board Compiler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Compile KM4/F151 point-map PDF vectors and embedded text into a deterministic normalized component dataset.

**Architecture:** Pure Python parsing functions consume pypdf content streams and return source-space primitives. A compiler layer classifies designators, pairs plausible geometry, normalizes coordinates, and writes validated JSON for the existing web workbench.

**Tech Stack:** Python, pypdf, NumPy only where needed, unittest, JSON.

---

### Task 1: PDF Primitive Parser

**Files:**
- Create: `scripts/board_compiler/pdf_primitives.py`
- Create: `tests/test_board_compiler_pdf.py`

- [x] Test CMap decoding, graphics-state matrix concatenation, transformed rectangles, and text coordinates.
- [x] Confirm tests fail before implementation.
- [x] Implement the pure parser and make tests pass.

### Task 2: Designator Compiler

**Files:**
- Create: `scripts/board_compiler/compiler.py`
- Create: `tests/test_board_compiler.py`

- [x] Test accepted board prefixes, BGA-grid rejection, normalized coordinates, and deterministic ordering.
- [x] Confirm tests fail before implementation.
- [x] Implement designator classification and candidate-footprint pairing.

### Task 3: KM4 Dataset And Audit

**Files:**
- Create: `scripts/compile_km4_board.py`
- Create: `knowledge-base/km4-board-compiled.json`
- Modify: `scripts/validate_cross_source_registration.py`

- [x] Compile point-map page 2 and verify the seven reviewed entities are recovered.
- [x] Record decoded-text, accepted-designator, footprint-pairing, and unresolved counts.
- [x] Validate normalized coordinates and source evidence.

### Task 4: Workbench Integration

**Files:**
- Modify: `assets/cross-source-registration/app.js`
- Modify: `assets/cross-source-registration/board-renderer.js`

- [x] Replace anonymous raster geometry with compiled source geometry where confidence is sufficient.
- [x] Keep the seven reviewed semantic entities and evidence links synchronized.
- [x] Run desktop/mobile browser QA and inspect the 2.5D output.
