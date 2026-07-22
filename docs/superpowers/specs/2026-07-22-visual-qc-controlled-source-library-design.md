# Visual QC Controlled Source Library Design

**Date:** 2026-07-22
**Status:** Approved

## Purpose

Preserve Milo-supplied physical-board photos before temporary attachment paths disappear, then produce the existing validated intake manifest from those preserved bytes. This is a local data-administrator workflow; it does not add a technician upload path or automatically upload to the controlled server.

## Ownership And Evidence Boundary

Milo remains the sole source of real visual photos and Codex remains the sole intake operator. The command requires explicit confirmation that the inputs are Milo-supplied physical photos and that the existing capture checklist was completed. It never infers model, board side, physical provenance, normality, or defect state from image content.

The controlled library root is required explicitly and must resolve outside the Git repository. `knowledge-base/visual-qc-proxy-inventory-v1.json` persistently binds every configured point map and approved manual proxy path to its reviewed SHA-256. Missing, changed, malformed, or newly configured-but-unregistered proxy sources fail closed. Project assets and every persisted engineering/manual proxy fingerprint remain rejected through both source-package and intake boundaries. Exact-hash blocking does not detect recompressed, cropped, edited, or screenshot proxies; operator provenance confirmation and downstream evidence gates remain mandatory.

The library is an integrity-preserving local operator workflow, not a sandbox against a hostile local administrator. Existing symlink/reparse paths are rejected and newly created controlled paths are immediately rechecked before publication. Normal Windows account and filesystem permissions remain part of the boundary.

## Library Layout

The library is content-addressed:

```text
<library-root>/
  objects/originals/<sha-prefix>/<sha256>.<canonical-extension>
  packages/.locks/<package-id>.lock
  packages/<package-id>/.complete
  packages/<package-id>/source-package.json
  packages/<package-id>/<batch-id>.intake.json
```

The original object contains exactly the source bytes. JPEG, PNG, and WebP use canonical extensions derived from detected MIME, not from a supplied filename. Existing objects are reused only after their bytes still match the expected SHA-256. A conflicting or corrupted object fails closed.

## Source Package Contract

`VISUAL-QC-SOURCE-PACKAGE-V1` contains:

- `package_id`, `batch_id`, `source_origin=milo_supplied`, and `physical_source_confirmed=true`;
- the deterministic `proxy_inventory_sha256` snapshot used when the package was built;
- `board_key`, canonical `board_id`, capture stage/session/setup, and completed capture checklist;
- one entry per explicit board side with original filename, library-relative object path, MIME, dimensions, byte size, and SHA-256.

It deliberately omits the temporary source path, credentials, personal identifiers, timestamps, QC conclusions, Golden status, and defect labels. Omitting timestamps keeps an identical package deterministic and makes idempotency comparison exact.

## Command And Data Flow

The command is `scripts/stage_visual_qc_source_package.py`. It accepts the same board/session/stage/setup and repeated `side_id=path` assignments as the batch builder, plus required `--package-id`, `--library-root`, `--confirm-milo-physical-source`, and `--confirm-capture-checklist`.

1. Validate every identifier, board side, source image, current proxy fingerprint, and confirmation before creating library paths.
2. Compute the complete deterministic source-package payload in memory.
3. Reject controlled child paths containing symbolic links or Windows reparse points.
4. Store each original through no-clobber content-addressed publication, verify the stored bytes, and flush the containing directory metadata.
5. Acquire a per-package file lock, then build the existing `VISUAL-QC-INTAKE-BATCH-V1` from the archived object paths inside an exclusively created final package directory.
6. Write `.complete` only after both manifests are deterministic and durable, then flush the package and packages-root directories.
7. If the package already exists, return success only when the completion marker exists, both committed manifests match the requested package exactly, every object still passes integrity checks, and none of its object hashes appears in the current proxy inventory; otherwise fail closed.
8. Print a machine-readable JSON summary with package, intake manifest, entry count, and whether the run created or reused the package. Unexpected command failures also return one machine-readable JSON object.

Failures never modify incoming photos, overwrite content-addressed objects, partially replace an existing package, or upload data. Orphaned content-addressed objects from a failed package publish are safe and may be reused by a later valid package.

## Testing

Tests cover multi-side staging, exact-byte preservation, MIME-derived extensions, deterministic package and intake manifests, runtime/schema parity, direct CLI invocation, machine-readable errors, package idempotency, changed-content conflicts, duplicate side/path rejection, current-inventory proxy revocation, missing confirmation, library-root/repository separation, junction/reparse rejection, completion-marker enforcement, directory flushes, corrupted existing objects, no partial package publication, and builder/importer dry-run compatibility.

Acceptance uses temporary synthetic images outside the repository. It proves archive and command plumbing only and cannot count as physical-board or visual-QC accuracy evidence.
