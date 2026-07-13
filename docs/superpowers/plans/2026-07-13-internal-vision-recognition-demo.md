# Internal Vision Recognition Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a locally runnable visual-inspection workbench that quality-checks an uploaded image and retrieves the closest models from the 21 approved Service Manual references.

**Architecture:** Keep pixel analysis and similarity ranking in a DOM-free ES module, while a thin browser controller loads images and renders states. Read approved reference metadata from the existing gallery manifest and perform all analysis client-side.

**Tech Stack:** HTML, CSS, browser Canvas, ES modules, Node built-in test runner, Playwright/Chrome visual QA.

---

### Task 1: Pixel Analysis Core

**Files:**
- Create: `assets/vision-recognition-demo/vision-core.js`
- Create: `tests/vision-core.test.mjs`

- [ ] Write failing Node tests for overexposure, low contrast, sharpness ordering, feature-vector normalization, and exact-candidate rank one.
- [ ] Run `node --test tests/vision-core.test.mjs` and confirm missing-module failure.
- [ ] Implement `analyzeImageQuality`, `extractFeatureVector`, `cosineSimilarity`, and `rankReferenceCandidates` using pixel arrays.
- [ ] Run the tests and require all assertions to pass.

### Task 2: Reference Loader And Workbench Controller

**Files:**
- Create: `assets/vision-recognition-demo/app.js`
- Create: `assets/vision-recognition-demo/index.html`
- Create: `assets/vision-recognition-demo/styles.css`

- [ ] Add the real upload/drop/sample controls and empty/loading/error/result states.
- [ ] Load `knowledge-base/vision-reference-gallery.json`, filter to `approved`, and precompute 21 feature vectors.
- [ ] Convert uploaded images to Canvas pixel data, run quality analysis, rank top three references, and render the matched source image and metadata.
- [ ] Keep all wording limited to image quality and reference similarity; include the internal-demo accuracy boundary beside results.

### Task 3: Automated Validation

**Files:**
- Create: `scripts/validate_vision_recognition_demo.py`

- [ ] Validate the HTML/CSS/JS file references, JSON paths, approved-reference count, source-image existence, and prohibited production-claim phrases.
- [ ] Run `python scripts/validate_vision_recognition_demo.py` and require a zero exit status.
- [ ] Run `node --test tests/vision-core.test.mjs` and require all tests to pass.

### Task 4: Real Browser QA

**Files:**
- Update only if QA exposes a verified defect.

- [ ] Serve the project locally and open `/assets/vision-recognition-demo/index.html` in Chrome/Playwright.
- [ ] Select an approved KM4 sample and verify KM4 ranks first, quality metrics render, and three candidates appear.
- [ ] Upload or select a second model and verify result state changes without reload.
- [ ] Verify desktop 1440x900 and mobile 390x844: no body overflow, no broken images, readable selected/unselected controls, and zero console errors.

### Task 5: Project Integration And Closeout

**Files:**
- Modify: `knowledge-base/README.md`
- Create: `docs/vision-recognition-demo-2026-07-13.md`
- Modify: Vault `Task Index.md` and `Overview.md`

- [ ] Record the demo route, algorithm boundary, reference count, verification evidence, and physical-photo gap.
- [ ] Run JSON, UTF-8, test, validator, browser, and `git diff --check` gates.
- [ ] Commit the completed demo without pushing under the current network constraint.
