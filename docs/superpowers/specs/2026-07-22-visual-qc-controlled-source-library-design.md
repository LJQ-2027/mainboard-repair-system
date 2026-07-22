# Visual QC Controlled Source Library Design

**Date:** 2026-07-22
**Status:** Approved

## Purpose

Preserve Milo-supplied physical-board photos before temporary attachment paths disappear, then produce the existing validated intake manifest from those preserved bytes. This is a local data-administrator workflow; it does not add a technician upload path or automatically upload to the controlled server.

## Ownership And Evidence Boundary

Milo remains the sole source of real visual photos and Codex remains the sole intake operator. The command requires explicit confirmation that the inputs are Milo-supplied physical photos and that the existing capture checklist was completed. It never infers model, board side, physical provenance, normality, or defect state from image content.

The controlled library root is required explicitly and must resolve outside the Git repository. Project assets and every known engineering/manual proxy fingerprint remain rejected through the existing intake-builder boundary. Exact-hash blocking does not detect recompressed, cropped, edited, or screenshot proxies; operator provenance confirmation and downstream evidence gates remain mandatory.

## Library Layout

The library is content-addressed:

```text
<library-root>/
  objects/originals/<sha-prefix>/<sha256>.<canonical-extension>
  packages/<package-id>/source-package.json
  packages/<package-id>/<batch-id>.intake.json
```

The original object contains exactly the source bytes. JPEG, PNG, and WebP use canonical extensions derived from detected MIME, not from a supplied filename. Existing objects are reused only after their bytes still match the expected SHA-256. A conflicting or corrupted object fails closed.

## Source Package Contract

`VISUAL-QC-SOURCE-PACKAGE-V1` contains:

- `package_id`, `batch_id`, `source_origin=milo_supplied`, and `physical_source_confirmed=true`;
- `board_key`, canonical `board_id`, capture stage/session/setup, and completed capture checklist;
- one entry per explicit board side with original filename, library-relative object path, MIME, dimensions, byte size, and SHA-256.

It deliberately omits the temporary source path, credentials, personal identifiers, timestamps, QC conclusions, Golden status, and defect labels. Omitting timestamps keeps an identical package deterministic and makes idempotency comparison exact.

## Command And Data Flow

The command is `scripts/stage_visual_qc_source_package.py`. It accepts the same board/session/stage/setup and repeated `side_id=path` assignments as the batch builder, plus required `--package-id`, `--library-root`, `--confirm-milo-physical-source`, and `--confirm-capture-checklist`.

1. Validate every identifier, board side, source image, proxy fingerprint, and confirmation before creating library paths.
2. Compute the complete deterministic source-package payload in memory.
3. Store each original through no-clobber content-addressed publication and verify the stored bytes.
4. Build the existing `VISUAL-QC-INTAKE-BATCH-V1` from the archived object paths.
5. Assemble both manifests in a temporary package directory under the library root.
6. Publish the complete package directory without replacing an existing package.
7. If the package already exists, return success only when both committed manifests match the requested package exactly and every object still passes integrity checks; otherwise return a package conflict.
8. Print a machine-readable JSON summary with package, intake manifest, entry count, and whether the run created or reused the package.

Failures never modify incoming photos, overwrite content-addressed objects, partially replace an existing package, or upload data. Orphaned content-addressed objects from a failed package publish are safe and may be reused by a later valid package.

## Testing

Tests cover multi-side staging, exact-byte preservation, MIME-derived extensions, deterministic package and intake manifests, direct CLI invocation, package idempotency, changed-content conflicts, duplicate side/path rejection, proxy blocking, missing confirmation, library-root/repository separation, corrupted existing objects, no partial package publication, and builder/importer dry-run compatibility.

Acceptance uses temporary synthetic images outside the repository. It proves archive and command plumbing only and cannot count as physical-board or visual-QC accuracy evidence.
