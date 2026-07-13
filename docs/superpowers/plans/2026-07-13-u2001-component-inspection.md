# U2001 Component Inspection Implementation Plan

**Goal:** Deliver one repair-grade U2001 inspection sample with refined procedural visuals, board-context isolation, independent manipulation, and source-backed repair information.

### Task 1: Inspection State Contract

- [x] Add failing Node tests for capability, enter/exit state, ghosting, and bounded transform.
- [x] Implement a DOM-free `component-inspection-state.js` module.
- [x] Run the targeted test and complete Node suite.

### Task 2: U2001 Repair-Visual Package

- [x] Add an explicit U2001 inspection profile to the reviewed dataset.
- [x] Build a layered PMIC/BGA visual profile without claiming exact package dimensions or ball geometry.
- [x] Preserve existing picking, selection, confidence, and side identity.

### Task 3: Complete-Anatomy-Style Inspection

- [x] Add evidence-panel enter/return control and inspection status.
- [x] Ghost board context and unrelated components while keeping U2001 solid.
- [x] Lift and scale U2001, rotate it independently, and retain wheel zoom.
- [x] Exit cleanly on return, entity change, side change, view change, and full reset.

### Task 4: Repair Information

- [x] Render source-backed common faults and detection method blocks.
- [x] Display the visual-model evidence boundary without inventing values or procedures.
- [x] Keep schematic and repair source cards available during inspection.

### Task 5: Verification And Return

- [x] Run syntax checks, all Node tests, all Python tests, JSON validation, and standalone validation.
- [x] Run headed Chromium desktop/mobile interaction and visual QA.
- [ ] Update implementation evidence, Vault, and project ledger.
- [ ] Commit the implementation and closeout state.
