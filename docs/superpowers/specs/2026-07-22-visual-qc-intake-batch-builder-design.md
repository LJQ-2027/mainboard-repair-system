# Visual QC Intake Batch Builder Design

**Date:** 2026-07-22
**Status:** Approved

## Purpose

Provide a local, data-administrator command that turns photos supplied by Milo into a validated `VISUAL-QC-INTAKE-BATCH-V1` manifest. The command removes manual JSON and SHA-256 editing while preserving the existing intake contract and server importer.

## Scope

The builder accepts one known board, one capture session, one capture stage, and one or more explicit `side_id=path` image assignments. It writes a manifest that can be passed directly to `scripts/import_visual_qc_batch.py`.

The builder does not upload files, alter or copy source photos, infer board identity or board side from filenames, assess defects, or claim that both sides are present. Single-side batches remain valid because photos may arrive incrementally.

## Command Contract

The command is `scripts/create_visual_qc_intake_batch.py` with these required arguments:

- `--batch-id`
- `--board-key`
- `--capture-session-id`
- `--capture-stage`
- one or more `--image side_id=path`
- `--confirm-capture-checklist`

Optional arguments are `--capture-setup-id` (default `standard-bench`) and `--output`. Without `--output`, the manifest is written to `<batch-id>.intake.json` in the current directory.

Entry IDs are deterministic: `<capture-session-id>-<side-id>`. Identifiers continue to use the existing safe-ID grammar. Explicit duplicate sides, duplicate resolved paths, malformed assignments, unknown boards or sides, unsupported images, and existing output files are rejected. The output may be replaced only with `--force`.

## Data Flow

1. Parse explicit command arguments.
2. Resolve the board and every side through the existing `BoardCatalog`.
3. Inspect each image using the existing intake image-evidence helper.
4. Build entries with absolute source paths and computed `expected_sha256` values.
5. Write the candidate manifest atomically as UTF-8 with LF line endings.
6. Run `validate_intake_batch` against the written file.
7. Return a concise machine-readable JSON summary containing the output path, batch ID, entry count, and per-entry evidence.

If final validation fails, remove the newly written manifest so an invalid batch is never left as a normal output artifact.

## Truth And Safety Rules

- `side_id` always comes from the operator's explicit assignment and the canonical board catalog.
- `expected_sha256` always comes from the current source bytes.
- The three capture checklist fields are written as true only after the explicit confirmation flag is supplied.
- Source images remain in place and unchanged.
- Existing output is protected by default.
- This command prepares evidence; it does not convert proxy material into physical evidence or training-eligible data.

## Testing

Unit and CLI tests cover successful multi-side generation, deterministic IDs and ordering, hash binding, default and explicit output paths, unknown sides, malformed assignments, duplicate sides and paths, invalid images, missing checklist confirmation, overwrite protection, direct script invocation, and compatibility with the existing dry-run importer.

An end-to-end acceptance uses existing non-physical proxy images only to prove command plumbing. It remains explicitly excluded from real visual-QC accuracy evidence.
