# Controlled HEIC Derivative Implementation Plan

**Goal:** Preserve HEIC originals and produce manifest-bound working images
that can enter the existing registration and visual-QC chain.

## Task 1: Lock The V2 Contract In Tests

- Add HEIC fixture generation through the pinned decoder library.
- Assert V1 remains byte-compatible for existing supported images.
- Assert HEIC and mixed packages use V2 with exact source and derivation
  evidence.
- Assert corruption, hash mismatch, missing derivation, and package reuse
  conflicts fail closed.

## Task 2: Implement HEIC Preparation And Storage

- Add strict HEIC MIME/container detection and deterministic primary-image
  decoding.
- Store exact originals under `objects/source-originals/`.
- Store compatible working images under the existing canonical originals
  layout.
- Emit and validate V1 or V2 packages without changing downstream working
  image fields.

## Task 3: Extend Audit And Operator Tooling

- Audit both source-original and working-object trees.
- Add source-original counts without changing historical package meaning.
- Keep the existing staging CLI and make HEIC support explicit in its output
  and documentation.

## Task 4: Real-File Acceptance

- Use one preserved Feishu HEIC as a decoder and integrity acceptance sample.
- Verify original SHA-256 remains unchanged.
- Visually inspect the working image and orientation.
- Do not publish a real board package until BG6/BG6H identity and side mapping
  are confirmed.

## Task 5: Closeout

- Run focused and complete Python/Node suites.
- Run source-library audit, JSON, diff, strict UTF-8, and browser/runtime
  regression checks where affected.
- Commit implementation and sync Ledger, Vault, and Feishu status wording.
