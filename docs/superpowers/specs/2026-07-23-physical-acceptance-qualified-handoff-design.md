# Physical Acceptance-Qualified Handoff Design

## Purpose

Create one owner-operated handoff path from a controlled physical-photo package and its completed local registration-acceptance run into the existing server importer. The handoff proves that the uploaded bytes are the same bytes staged and preflighted by Codex, while preserving server-side human registration review as the only approval step.

This closes the bypass between `VISUAL-QC-SOURCE-PACKAGE-V1`, `VISUAL-QC-PHYSICAL-REGISTRATION-RUN-V1`, and the existing resumable intake CLI. It does not approve an automatic registration, perform manual four-point registration, create a Golden Sample, infer a defect, or expose upload controls to technicians.

## Chosen Approach

Add a dedicated physical-package handoff command instead of making the generic importer understand controlled source libraries. The command receives:

- the completed controlled `source-package.json`;
- the published `physical-registration-run.json`;
- the external controlled-library root;
- a handoff working directory for durable receipts;
- the existing server transport options, or `--dry-run`.

It derives the archived intake manifest from the validated package identity. Operators cannot substitute a separate manifest or arbitrary image path. The existing `run_intake` implementation remains responsible for resumable uploads and server job polling.

Alternatives rejected for this increment:

- Extending the generic importer would mix legacy/general batch behavior with the stronger physical-evidence gate and require every existing caller to understand package-level provenance.
- Uploading first and validating acceptance only on the server would allow unqualified physical bytes to enter storage and would duplicate the local source-library/proxy boundary.
- Rebuilding registration review offline would duplicate the existing server workbench and create two competing approval facts.

## Validation And Gate

The handoff revalidates the source package against the current project catalog, controlled object store, completion marker, and current proxy inventory. It reads and hashes the exact acceptance-report bytes once, parses those bytes, applies the existing runtime report validator, and verifies:

- schema, physical-evidence flags, package id, batch id, source manifest SHA-256, and proxy-inventory SHA-256;
- board key/id and capture stage/session/setup;
- an exact one-to-one entry set;
- every entry id, side id, image SHA-256, MIME type, dimensions, and byte size;
- each declared overlay is a regular non-reparse file below the acceptance directory and matches its SHA-256, MIME signature, dimensions, and byte size;
- no absolute path or unrecognized entry is introduced through the report.

Upload is fail-closed for the whole package when the acceptance report has `issues`, any `processing_issue`, any `image_retake_required`, missing/corrupt overlays, or any package/report mismatch. `automatic_candidate_review_required` and `manual_registration_required` are both uploadable because they are unresolved states intentionally completed in the existing server workbench. A mixed candidate/manual package is valid.

The archived intake manifest is independently validated and must have the same batch, board/capture identity, entry ids, sides, and image evidence as the package and acceptance report.

## Handoff Receipt

The command publishes `VISUAL-QC-PHYSICAL-HANDOFF-V1` as the canonical operator receipt. It contains no credentials, absolute paths, source pixels, or approval claim. It records:

- source package id, batch id, and exact manifest SHA-256;
- acceptance report SHA-256 and its `field_accuracy_claim_allowed=false` boundary;
- board and capture identity;
- per-entry image SHA-256, acceptance action, transfer state, server case id, server job id, and typed transfer error;
- deterministic summary counts and a handoff status.

The handoff working directory also contains the existing `VISUAL-QC-INTAKE-RECEIPT-V1` used for resumability. The physical handoff receipt is rebuilt from that receipt after every run, so a process interruption after server upload can be recovered without uploading the same image twice. Existing intake idempotency remains `batch_id + entry_id + image_sha256`.

Handoff statuses are:

- `validated`: dry-run validation completed and no upload was attempted;
- `transferred`: every entry reached the server and its automatic-registration job completed successfully;
- `partial_failure`: at least one entry failed while another entry was uploaded or completed;
- `failed`: upload was attempted and no entry reached the server;
- `processing`: no entry failed and at least one uploaded server job is still non-terminal because the operator did not request or finish waiting.

The receipt never changes an acceptance action into `reviewed`. It states that server registration review remains required for every entry.

## Transport Integrity

The real multipart transport currently reads the image path after intake validation. This increment closes that read race: the transport reads the file once, verifies byte length and SHA-256 against the validated entry, and builds multipart content from those same verified bytes. A mismatch fails before any request is sent. Test transports remain path-independent and do not receive credentials or source bytes.

The handoff command requires HTTPS except for the existing explicit localhost test override. Credentials continue to come from the existing credential file/environment path and are never serialized into either receipt or error output.

## Publication And Concurrency

The handoff working directory must be outside both the project tree and controlled source library. It is created durably and rejects symlinks and Windows reparse points. A per-handoff thread/process lock serializes runs that target the same receipt. Existing files are resumed only when their schema, package manifest SHA-256, acceptance report SHA-256, batch id, and entry image hashes match; otherwise the command fails without resetting server ids.

Both intake and handoff receipts use atomic replacement, file fsync, and parent-directory sync. A handoff receipt is updated only after the underlying intake receipt is durable. No source package, object, acceptance report, or overlay is modified.

## CLI And Exit Codes

Add `scripts/handoff_visual_qc_physical_package.py` with stable JSON stdout/stderr:

- exit `0`: dry-run `validated`, `transferred`, or non-terminal `processing` with no failed entry;
- exit `1`: completed transfer with `partial_failure` or `failed`;
- exit `2`: invalid/revoked package, invalid acceptance evidence, blocked retake/processing state, unsafe working directory, receipt conflict, or invalid arguments.

The command supports the existing `--wait`, `--continue-on-error`, credential, actor, API-base, and localhost options. It does not add a browser upload path or production deployment in this increment.

## Verification

TDD coverage will prove package/report/intake correlation, report-byte hashing, overlay integrity, retake and processing fail-closed behavior, candidate/manual admission, mixed-side ordering, receipt reconstruction/resume, receipt conflicts, multipart same-byte verification, credential redaction, output containment, reparse rejection, and CLI exit codes.

Regression requires the complete Python and Node suites, Python compilation, JSON Schema parsing, UTF-8/U+FFFD checks, and `git diff --check`. A local temporary two-side package will run through staging, acceptance, handoff dry-run, and a fake resumable transport while source and acceptance snapshots remain byte-identical. This increment has no browser UI change and no production deployment, so P3 and production P4 remain not applicable; real KM4/F151 photos remain the physical-accuracy gate.
