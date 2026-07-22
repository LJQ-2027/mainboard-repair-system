# Visual QC Source Library Audit Design

**Date:** 2026-07-22
**Status:** Approved by active continuous-development objective

## Purpose

Add a read-only integrity audit for the repository-external controlled visual source library. The audit proves whether committed packages and content-addressed originals are still internally consistent before Codex imports real photos. It never deletes, repairs, uploads, classifies, or changes evidence.

## Scope And Boundary

The command audits one explicitly supplied library root outside the Git repository. It reuses the current source-package validator and current canonical proxy inventory, so later proxy classification can revoke an older package. It treats the local filesystem and Windows account permissions as part of the trust boundary; it rejects visible symlink/reparse paths but is not a sandbox against a hostile local administrator.

The first version reports five conditions:

- valid complete packages;
- invalid packages, including corrupt, conflicting, revoked, or unsafe manifests/objects;
- incomplete package directories without a trusted `.complete` marker;
- invalid or non-canonical object files;
- valid canonical objects not referenced by any valid package.

Orphaned objects are informational because failed no-clobber publication may safely leave reusable content-addressed bytes. The command does not offer cleanup.

## Report Contract

`VISUAL-QC-SOURCE-AUDIT-V1` is deterministic and contains no timestamp, absolute library path, credential, actor, or photo conclusion. Top-level fields are:

- `schema_version`;
- `status`: `healthy`, `attention`, or `issues`;
- `counts`: package/object totals and category totals;
- sorted `packages`, `invalid_objects`, and `orphaned_objects` arrays.

Each package record contains only its safe directory id, status, entry count when valid, and stable error code/message when invalid. Object records use library-relative POSIX paths and stable reasons. `healthy` means no issues and no orphans; `attention` means orphan-only; `issues` means at least one invalid/incomplete package or invalid object.

## Scan Rules

1. Require an existing directory outside the repository and reject the library root or controlled children when a visible symlink/reparse point is encountered.
2. Enumerate package directories deterministically, excluding the internal `.locks` directory.
3. Require a regular, controlled `.complete` marker and `source-package.json`; then call `validate_source_package` so board identity, manifest contract, current proxy inventory, object integrity, and intake compatibility retain one authority.
4. Count referenced objects only from valid packages.
5. Enumerate files under `objects/originals` and require the canonical `<two-hex-prefix>/<lowercase-sha256>.<jpg|png|webp>` shape, exact SHA-256, matching prefix, valid image evidence, and no symlink/reparse path.
6. Report a valid canonical object as orphaned when no valid package references it.
7. Never write inside the library, repository, server, or network.

## CLI And Exit Codes

`scripts/audit_visual_qc_source_library.py --library-root <path>` prints exactly one JSON object to stdout and keeps stderr empty for handled failures.

- exit `0`: `healthy` or orphan-only `attention`;
- exit `1`: completed audit with integrity `issues`, or unexpected runtime failure;
- exit `2`: invalid arguments or invalid/missing library root.

## Verification

Tests create temporary external libraries and cover healthy multi-side packages, deterministic output, no filesystem mutation, orphan-only attention, incomplete package, corrupt/revoked package, malformed object path, corrupt object bytes, junction/reparse rejection, missing root, CLI exit codes, and machine-readable failures. Full Python and Node regression remains required. Synthetic fixtures prove plumbing only and never count as physical-board evidence.
