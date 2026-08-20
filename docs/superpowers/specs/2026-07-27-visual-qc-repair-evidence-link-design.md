# Visual-QC Repair Evidence Link V1 Design

**Date:** 2026-07-27
**Status:** Written specification ready for owner review
**Owner:** Milo
**Data operator:** Codex

## Goal

Connect an immutable repair-case fact to the exact physical-board evidence and
engineering object that a data administrator reviewed, without converting that
relationship into a visual-defect conclusion.

The first real use is CASE005:

- repair case `case-005-bg6-f069`, revision `1`;
- repair-case manifest SHA-256
  `85c8c64cb97cf1ea1e567e4d1f7fc62ec00ebf02719939c74a5e0faf46298177`;
- exact board `bg6h-f069` / `BOARD-F069-MAIN-V1.2`;
- reported finding `EMMC坏`;
- candidate engineering component `U4000` on `main_page_2`;
- current compiled display name `eMMC storage`, which is not yet backed by an
  evidence descriptor that proves the semantic `U4000 = eMMC` relationship;
- two after-repair physical photos with immutable source hashes and reviewed
  registration records.

The first link may let the internal workbench navigate from `EMMC坏` to U4000
as `possibly_related`. It may become `related` only after a reviewed source
page or equivalent immutable evidence explicitly proves U4000's eMMC identity.
It must continue to say that the finding was reported by the source and that
no visible EMMC defect has been confirmed.

## Chosen Architecture

Add a separate append-only contract:
`VISUAL-QC-REPAIR-EVIDENCE-LINK-V1`.

The controlled repository-external library is authoritative. The local
Visual-QC server receives an immutable projection for search and workbench
display only:

```text
repair-case manifest + compiled engineering identity
                     + physical evidence snapshot
                               |
                               v
       controlled repair-evidence-link revision
                               |
                     owner-only synchronization
                               |
                               v
              local server read projection
                               |
                               v
           internal workbench evidence panel
```

The link contract does not modify repair-case manifests, source packages,
registration reviews, annotations, QC reviews, Golden Samples, or training
records. Production remains unchanged until a separate deployment decision.

## Why A Separate Fact Layer

The three existing fact authorities answer different questions:

- repair-case source: what the supplied repair record says;
- engineering sources: which component or board region has a reviewed
  identity;
- Visual-QC review: what is visible in one registered physical image.

Embedding one layer into another would make a source diagnosis look like an
image diagnosis or make a point-map relationship look like a confirmed
physical defect. A link manifest preserves the relationship while retaining
the authority and limitations of every input.

## Storage Layout

The controlled source library gains one independent tree:

```text
repair-evidence-links/
  <link_set_id>/
    revisions/
      0001/
        repair-evidence-link.json
        .complete
      0002/
        repair-evidence-link.json
        .complete
```

There is no mutable `latest` file. The valid head is the highest contiguous
revision whose `previous_manifest_sha256` matches the exact preceding
manifest. Publication reuses the repair-case library's locking, temporary
directory, no-clobber, fsync, atomic rename, completion-marker, symlink,
junction, reparse, hard-link, and path-escape protections.

No image, source package, repair-case manifest, or supporting object is copied
into this tree. The link binds existing immutable evidence by identifier and
SHA-256.

## Top-Level Contract

One link-set revision has exact top-level fields:

```json
{
  "schema_version": "VISUAL-QC-REPAIR-EVIDENCE-LINK-V1",
  "link_set_id": "link-case005-f069-after",
  "revision": 1,
  "previous_manifest_sha256": null,
  "source_origin": "codex_operator",
  "repair_case_references": [],
  "board": {},
  "physical_evidence": [],
  "bindings": [],
  "boundaries": {}
}
```

The format has no timestamp or absolute path, so an exact replay produces the
same bytes and manifest hash.

## Repair-Case References

Each item in `repair_case_references` binds:

- stable `repair_case_reference_id`;
- `repair_case_id`;
- exact repair-case `revision`;
- repair-case `schema_version`;
- exact repair-case manifest SHA-256;
- board key and board ID copied from the validated manifest.

The publisher validates the complete repair-case revision from the controlled
library. The referenced manifest must be complete, its chain must be valid,
and its exact board must match the link-set board.

A later repair-case revision does not mutate an existing reference. Referencing
new or corrected facts requires a new link-set revision that appends a new
repair-case reference for the newer manifest. All references in one link set
must retain the same repair-case ID and board.

## Board and Engineering Identity

`board` binds:

- canonical `board_key`;
- canonical `board_id`;
- exact board-catalog asset identity;
- the SHA-256 of the canonical compiled board/entity source consumed during
  publication.

Every designator target must have a reviewed identity on the declared board
side. The publisher copies a minimal engineering snapshot into the binding:

- component ID;
- designator;
- side ID;
- technician-facing category;
- normalized footprint or reviewed point;
- exact engineering evidence descriptors already present in the compiled
  board dataset;
- `geometry_source_status`;
- engineering snapshot SHA-256.

The snapshot does not invent electrical function, package geometry, visibility,
or fault meaning. An exact reviewed designator with low-confidence geometry may
still be the target, but the workbench renders only its conservative source
location marker and never treats the estimated size as a precise footprint.
An unresolved designator identity cannot become a designator target; the
binding must fall back to a board region or whole-board target.

## Physical Evidence Snapshot

Each `physical_evidence` item binds one exact server case:

- stable evidence ID local to the link set;
- `server_case_id`;
- intake batch ID and intake entry ID;
- board key, board ID, and side ID;
- capture stage and evidence role;
- the complete canonical qualified-handoff provenance object;
- `qualified_handoff_sha256`;
- `image_id`;
- `image_sha256`;
- `registration_review_id`;
- registration `job_id`;
- registration method;
- reviewed board-to-image matrix;
- solve anchors, independent check points, and error values;
- `physical_evidence_snapshot_sha256`.

The embedded qualified-handoff object preserves its exact schema version,
handoff schema version, source-package manifest SHA-256, archived-intake
manifest SHA-256, acceptance-report SHA-256, acceptance action,
`registration_review_required=true`, and
`field_accuracy_claim_allowed=false`. Its SHA-256 is computed from canonical
JSON of the complete object.

`physical_evidence_snapshot_sha256` is computed from canonical JSON of every
field in the physical-evidence item except that hash field itself. It therefore
closes the server case, intake identity, handoff provenance, image, job,
registration review, matrix, anchors, check points, and error values into one
immutable snapshot.

Only `physical_capture` cases with a reviewed registration are linkable.
Synthetic or service-manual proxies fail closed. The server case, image,
qualified handoff provenance, and registration review must agree with the
controlled source package and link-set board.

The publisher consumes a strict UTF-8
`VISUAL-QC-LINKABLE-PHYSICAL-EVIDENCE-V1` snapshot exported from the local
server. The export contains only the reduced fields above; it does not copy
credentials, absolute storage paths, source images, audit logs, or unrelated
case data.

Registration reviews are already immutable in the current server. Replacing
an image or choosing a different registration creates a different server case
or review identity. The old link remains historical and cannot silently point
at the replacement.

## Binding Contract

Each binding contains:

- stable `binding_id`;
- non-null `repair_case_reference_id`;
- one repair-case source fact;
- one engineering or board target;
- exactly one `physical_evidence_id`;
- association status;
- visibility status;
- explicit evidence bases;
- nullable `supersedes_binding_id`;
- fixed boundary object.

### Source Fact

The source-fact selector supports:

- `reported_symptom`;
- `finding`;
- `repair_action`;
- `outcome`.

It stores the fact kind, stable fact ID, a minimal display snapshot, claim
status when present, and a canonical fact SHA-256. The publisher derives the
snapshot deterministically from the corresponding repair-case object and
rejects any operator-supplied display text that differs.

The binding's `repair_case_reference_id` fixes the exact repair-case revision
and manifest from which that source fact came. A later top-level repair-case
reference cannot change the provenance of an earlier binding.

`outcome` uses the reserved fact ID `outcome`, because the current repair-case
contract has one outcome object rather than an outcome array.

Corrections are resolved from the complete repair-case chain. A binding whose
source fact has a later active correction derives
`source_fact_superseded=true` and the exact replacement fact ID. The workbench
may show it in history, but it must not present the old wording as a current
association.

### Target

One target has exactly one of these forms:

- `whole_board`;
- `board_region`, with side ID and normalized rectangle or polygon;
- `designator`, with the reviewed engineering snapshot.

Board coordinates are canonical. Image coordinates are projected at runtime
through the exact pinned registration matrix and are never stored as an
independent editable truth.

### Association Status

Association and visibility are independent axes.

`association_status` is one of:

- `related`: the operator has sufficient source and engineering evidence to
  bind the fact to the target;
- `possibly_related`: the target is plausible but the supplied evidence is
  incomplete;
- `not_related`: an earlier candidate was explicitly rejected;
- `insufficient_evidence`: no narrower target than the current scope can be
  supported.

`visibility_status` is one of:

- `not_assessed`;
- `visible`;
- `not_visible`;
- `occluded`.

`visible` means only that the target area can be seen. It does not mean an
anomaly is visible. `not_visible` means the target is outside the usable frame
or cannot be resolved at the available image detail. `occluded` means the
target location is in frame but covered by a shield or installed structure. A
designator may be engineering-related while being occluded in every linked
photo.

The binding's one physical-evidence item must have the same side ID as a
designator or board-region target. A link set may contain multiple photos and
both board sides, but each photo gets a separate binding and its own visibility
status. A side-specific binding cannot use the opposite-side image as support.
Whole-board context across two sides also requires separate bindings.

### Evidence Basis

Every binding lists one or more basis records:

- `repair_case_fact`: the exact source fact;
- `engineering_identity`: a reviewed point-map, schematic, or compiled entity
  identity;
- `human_observation`: an operator statement limited to target visibility or
  location in the registered photo.

Basis records are structured references only. V1 does not accept new free-text
operator notes or observation narratives. `human_observation` uses one fixed
observation code matching the binding's visibility state, so it cannot carry a
defect verdict or personal identifier.

`related` designator bindings require both `repair_case_fact` and
`engineering_identity`. `human_observation` is optional and cannot contain a
defect verdict. A binding based only on filename similarity, model-name
similarity, nearby geometry, or automated language matching cannot be
`related`.

## Governance Boundaries

Every link-set revision stores exactly seven fixed false boundaries:

```json
{
  "visual_defect_confirmed": false,
  "qc_annotation_created": false,
  "golden_approved": false,
  "training_label_allowed": false,
  "repair_causality_confirmed": false,
  "repair_instruction_allowed": false,
  "field_accuracy_claim_allowed": false
}
```

Each binding stores the same seven fixed false values and one additional
`model_identity_resolved` value derived only from its own
`repair_case_reference_id`. CASE005 bindings derive false. A binding against a
resolved repair-case revision may derive true, but the link itself can never
resolve an identity. A V1 repair case derives true because its `device_models`
were already required to be exact catalog-compatible values; a V2 repair case
uses its existing derived boundary.

No relation, visibility state, basis record, or target type can override the
seven fixed boundaries or a binding's derived identity state.

## Revision Rules

Revision 1 has `previous_manifest_sha256 = null`.

Every later revision:

- increments by exactly one;
- binds the exact prior link manifest SHA-256;
- retains the same link-set ID, repair-case ID, board, and source origin;
- preserves all earlier repair-case references unchanged and appends any newer
  repair-case revision as a new reference;
- preserves earlier physical snapshots and bindings unchanged;
- appends new evidence or bindings;
- supersedes an incorrect binding through a new binding whose non-null
  `supersedes_binding_id` names the prior binding.

Using a newer repair-case revision, adding a physical photo, or binding a new
registration review requires a new link revision. Removing evidence, rewriting
an earlier reference or binding, revision gaps, forks, or ambiguous replacement
chains fail closed.

Revision 1 bindings have `supersedes_binding_id = null`. A later binding may
supersede only one active binding in the same link set. One binding cannot have
two active replacements, and replacement chains cannot cycle.

The two historical states remain separate:

- `source_fact_superseded` is derived from the repair-case correction chain and
  points to a replacement fact ID;
- `binding_superseded` is derived from the link replacement chain and points to
  a replacement binding ID.

Either state removes the old binding from the current-association list while
retaining it in history. The workbench shows the exact reason and replacement
identity instead of one generic superseded label.

An exact replay returns the existing revision. A conflicting replay publishes
nothing.

## Owner Tools

Two owner-only commands are added:

```text
export_visual_qc_linkable_evidence.py
stage_visual_qc_repair_evidence_link.py
```

The export command reads one local controlled server case, requires qualified
physical provenance and reviewed registration, emits the reduced deterministic
physical-evidence snapshot, and performs no server write.

The staging command receives:

- controlled library root;
- link-set ID;
- repair-case manifest path;
- one or more physical-evidence snapshot paths;
- strict UTF-8 binding-record JSON;
- optional previous link manifest.

It validates all authorities, computes exact snapshots and fixed boundaries,
publishes one immutable revision, reopens and validates it, and prints a typed
receipt.

A separate owner synchronization command validates the completed local link
revision and imports its canonical JSON plus SHA-256 into the local server.
Synchronization is idempotent and append-only. The server cannot author or
mutate the controlled link.

## Local Server Projection

The local server gains an additive `repair_evidence_links` projection with:

- link-set ID and revision;
- manifest SHA-256;
- repair-case ID and ordered repair-case reference hashes;
- board identity;
- canonical manifest JSON;
- import actor and server import time.

The import route requires the data-administrator role. It revalidates the JSON
Schema, verifies every referenced server case, image hash, qualified handoff,
and registration review against current SQLite state, and rejects a stale or
conflicting projection.

Projection health is derived, not written back into the controlled manifest:

- `active`: every pinned server, image, handoff, job, review, board, and board
  asset identity still matches;
- `stale`: the referenced records exist but an identity or hash differs;
- `unavailable`: a referenced case, image, job, review, or required board asset
  cannot be read.

Exact stale reasons are:

- `server_case_identity_mismatch`;
- `image_identity_mismatch`;
- `qualified_handoff_mismatch`;
- `registration_job_mismatch`;
- `registration_review_mismatch`;
- `board_asset_mismatch`.

Exact unavailable reasons are:

- `server_case_missing`;
- `image_missing`;
- `registration_job_missing`;
- `registration_review_missing`;
- `board_asset_missing`.

Import performs the full check and accepts only `active`. Every list/detail
read recomputes the health state from current SQLite and board-asset bytes.
Mismatch or absence changes only the derived response; it never edits the
canonical manifest or its projection. Target location is enabled only for
`active`.

Read routes support:

- links for one server case;
- links for one repair case;
- one exact link-set revision.

All link routes are under the data-administrator API and require the
data-administrator role. List responses contain only IDs, revision, board,
association/visibility counts, health state, source-fact-superseded count, and
binding-superseded count. They do not return source wording, fact snapshots,
evidence-basis details, or canonical JSON. Exact detail may return those fields
only to the data administrator.
There is no technician-facing repair-link route in V1.

V1 introduces no new free-text operator field. The only displayed source
wording is the already privacy-reduced snapshot deterministically copied from
the repair-case manifest. Structured human-observation codes contain no
personal information or defect narrative.

Any server case referenced by an imported projection is excluded from
retention candidates in `active`, `stale`, and `unavailable` states. The
retention audit reports `repair_evidence_link_present`; it never deletes the
case silently. Removing that protection requires a future explicit retirement
design and is not part of V1.

The projection is excluded from Golden, QC, dataset, COCO, bundle, and training
queries.

Production routes and schema versions remain unchanged in this phase.

## Workbench Experience

The internal Visual-QC workbench adds one compact `维修案例证据` panel after a
server case has loaded.

The panel shows:

- repair-case ID and revision;
- current source facts;
- badges for `来源报告`, `工程资料关联`, and `照片可见性`;
- association and visibility status;
- separate source-fact-correction and binding-replacement warnings when
  applicable;
- one action to locate the linked target.

Selecting a binding:

1. switches to the correct board side;
2. selects the reviewed component or normalized board region;
3. centers the point-map and photo canvases;
4. projects the target through the pinned reviewed registration;
5. keeps the rest of the board visible as context.

For low-confidence component geometry such as the current F069 U4000 entity,
the workbench centers a compact location marker. It does not draw a
package-sized defect region or imply measured footprint accuracy.

The interface uses neutral source/evidence styling. Coral remains reserved for
confirmed QC anomalies. The initial candidate U4000 binding must read:

```text
来源报告 · 候选工程关联 · 未形成视觉缺陷结论
```

It must not use defect wording, defect icons, anomaly color, or automatic
repair guidance. Only a source-proven `related` binding may replace
`候选工程关联` with `工程资料关联`.

The first release is read-only in the browser. Codex authors and revises links
through the owner CLI so the repository-external controlled library remains
the authority. Browser authoring is a later design.

## CASE005 First Link Set

After implementation, the first real link set is:

- link-set ID `link-case005-f069-after`;
- repair case `case-005-bg6-f069`, revision `1`;
- exact repair-case manifest hash already published;
- exact F069 board identity;
- both reviewed after-repair server cases;
- source fact `case005-reported-emmc-fault`;
- target `U4000` on exact side `main_page_2`;
- the U4000 binding references only the same-side physical evidence; the
  opposite side remains available to a separate whole-board context binding;
- initial association `possibly_related`, because the current compiled
  `eMMC storage` display name has no evidence descriptor that independently
  proves `U4000 = eMMC`;
- association may become `related` only in a later link revision after a
  reviewed source page or equivalent immutable evidence proves that semantic
  identity;
- U4000's current low-confidence geometry is displayed as a conservative
  location marker rather than a precise footprint;
- visibility set from explicit human inspection, with no defect verdict;
- all fixed boundaries preserved.

If the source/compiler evidence is not sufficient to prove the semantic
EMMC-to-U4000 relationship, publication must use `possibly_related` or
`insufficient_evidence`. The software must not force the desired demonstration.

## Failure Handling

Publication fails without a completed revision when:

- repair-case or link history is invalid;
- board identities differ;
- a physical snapshot is proxy evidence, unreviewed, stale, or hash-mismatched;
- a server case does not bind the declared source package;
- a fact ID or fact snapshot does not resolve;
- a designator or engineering snapshot does not resolve on the declared side;
- normalized geometry is invalid;
- a `related` binding lacks its required bases;
- a boundary is supplied with an unauthorized value;
- unsafe paths, links, publication races, or no-clobber conflicts are found.

Server synchronization rejects stale physical evidence and leaves the local
controlled revision intact. Workbench fetch failures show an unavailable
evidence state without clearing annotations, registration, or QC work.

## Validation

### Contract and Library

- exact JSON Schema and Python validation parity;
- all association, visibility, source-fact, and target variants;
- canonical fact, engineering, physical-evidence, and manifest hashes;
- complete qualified-handoff and physical-evidence snapshot hashes;
- append-only revision, replay, conflict, race, and completion-marker tests;
- separate `source_fact_superseded` and `binding_superseded` derivation;
- binding-level repair-case revision provenance;
- exactly one same-side physical evidence item per binding;
- invalid geometry, cross-board, cross-side, proxy, unreviewed, stale, and
  dangling-reference rejection;
- symlink, junction, reparse, hard-link, and path-escape rejection.

### Server Projection

- data-administrator import authorization;
- idempotent exact import and conflicting revision rejection;
- server case, image, provenance, and registration identity verification;
- active/stale/unavailable derivation for every exact reason code;
- read-time revalidation without controlled-manifest mutation;
- redacted list and data-administrator-only canonical detail;
- absence of every repair-link field from technician APIs;
- migration and old-database readability;
- linked-case retention blocking with
  `repair_evidence_link_present`;
- exclusion from QC, Golden, dataset, COCO, bundle, and training exits.

### Workbench

- CASE005 facts load only for the linked server cases;
- selecting U4000 changes side and centers both canvases;
- pinned registration projects the same normalized target deterministically;
- stale review or board-asset hash disables location rather than guessing;
- source, engineering, visibility, and QC states remain visually distinct;
- no link state changes annotation or final QC state;
- desktop and 390 px touch layouts have no overlap or horizontal overflow;
- keyboard focus, screen-reader labels, loading, empty, stale, and error states
  remain usable.

### Full Verification

- focused Python and Node suites;
- full Python and Node suites;
- Python compilation and JSON Schema validation;
- strict UTF-8 and U+FFFD scan;
- deterministic controlled-source audit;
- real CASE005 publication and idempotent server projection;
- headed browser QA for both F069 sides;
- Git diff and clean-worktree checks.

## Non-Goals

- Confirming that CASE005 has a visible EMMC defect.
- Inferring that replacing or testing U4000 caused the reported repair result.
- Resolving `TECNO/BG6` to `BG6H/BG6h`.
- Creating or editing QC annotations from a repair-case link.
- Approving a Golden Sample or training label.
- Generating technician repair instructions.
- Browser-side link authoring.
- Production deployment or migration.
