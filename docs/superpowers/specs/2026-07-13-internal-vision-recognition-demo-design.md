# Internal Vision Recognition Demo Design

Date: 2026-07-13

## Goal

Build a browser-based internal demo that uses the 21 reviewed Service Manual reference images to validate image-quality checks, seven-model similarity retrieval, main/sub/structure reference classification, and the technician-facing result layout before physical board photos are available.

## Product Boundary

The demo is an internal technical validation tool, not a production QC model. It may report reference similarity and image-quality findings, but it must not claim that a board is normal, defective, correctly identified, or repairable. All image processing remains in the browser.

## User Flow

1. Open the visual inspection workbench.
2. Upload, drag, or choose one of the approved reference samples.
3. See resolution, exposure, contrast, clipping, and sharpness checks.
4. If the image is usable, compare it with the 21 reviewed references.
5. Show the top three model candidates, similarity score, matched reference role, board version, and source page.
6. Display the strongest reference beside the input image and preserve an explicit internal-demo disclaimer.

## Architecture

- `vision-core.js`: pure pixel-analysis and ranking functions with no DOM dependencies.
- `app.js`: image loading, Canvas conversion, reference loading, interaction state, and rendering.
- `index.html` / `styles.css`: technician-facing upload and result workspace.
- `vision-reference-gallery.json`: source of approved reference metadata.
- Node built-in tests: deterministic synthetic pixel fixtures for quality and ranking behavior.

## Quality Analysis

The browser downsamples the image for analysis and calculates:

- minimum resolution;
- mean luminance;
- contrast using luminance standard deviation;
- highlight and shadow clipping ratios;
- sharpness using neighbor-gradient energy.

The demo returns `good`, `usable`, or `retake`, plus concrete capture guidance. Thresholds are product heuristics and are labeled as such.

## Similarity Retrieval

Each image is converted to a normalized feature vector combining:

- a low-resolution luminance structure grid;
- RGB histogram bins;
- horizontal and vertical edge-energy cells.

Cosine similarity ranks approved references. Scores are reference similarity, not calibrated recognition probability. Exact or lightly transformed reference samples should rank their own model first; field accuracy remains unverified until physical board photos are added.

## Data And States

Only assets with `review_status: approved` are indexed. Every result retains model, role, board scope, board side, board-version label, manual page, reference strength, and source path.

UI states:

- empty;
- image loading;
- quality failed;
- matching;
- results;
- reference-loading error.

## Acceptance Criteria

- 21 approved references load with zero broken images.
- Upload, drag/drop, and sample selection work.
- Quality metrics are calculated locally and show actionable guidance.
- Top three matches render with explicit similarity language.
- Exact approved samples return the correct model as rank one.
- Desktop and 390px mobile layouts have no body overflow or overlapping controls.
- Browser console has no errors.
- The page never states that it detected a real fault.

## Later Upgrade

Physical board front/back photos will be added as strong references with known board revision and side. The same interface can then use OpenCV registration, learned embeddings, or a server-side model without changing the technician flow.
