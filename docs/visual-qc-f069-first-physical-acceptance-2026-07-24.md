# F069 First Physical Visual-QC Acceptance

## Scope

The first governed physical-board batch is Feishu repair case `CASE005`,
received from Milo's overseas collection table. It contains two after-repair
HEIC photos of board revision `F069_MAIN_PCB_V1.2`.

This acceptance proves the controlled source, server intake, physical-image
quality, manual point-map registration, and workbench restoration path. It
does not prove automatic cross-modal registration accuracy, visible-defect
recognition, repair success, Golden Sample eligibility, or training
eligibility.

The independent repair-case fact source supports both
`VISUAL-QC-REPAIR-CASE-SOURCE-V1` and
`VISUAL-QC-REPAIR-CASE-SOURCE-V2`. Historical V1 manifests remain unchanged;
the CASE005 publication described below is V2.

## Governed Source

- Board key: `bg6h-f069`
- Board ID: `BOARD-F069-MAIN-V1.2`
- Package: `f069-case005-after-source`
- Package schema: `VISUAL-QC-SOURCE-PACKAGE-V2`
- Capture stage: `after_repair`
- Capture session: `feishu-case005-board-01-after`
- Capture setup: `overseas-blue-mat-v1`
- Source row: `recvq19VUYj1AX`
- `IMG_5608.HEIC`: `main_page_1`, the SIM-card/shield side
- `IMG_5605.HEIC`: `main_page_2`, the main-chip/shield side

The package preserves two exact HEIC source objects and two deterministic
JPEG working objects. `VISUAL-QC-SOURCE-AUDIT-V2` reported `healthy`: one
valid package, four referenced objects, no invalid objects, no orphaned
objects, and no library-structure issues.

## Registration Result

Both working images passed image-quality admission as `usable` and required
no retake. ORB and AKAZE did not produce enough geometrically consistent
inliers between the color physical photos and engineering point maps.
Automatic output therefore correctly remained `manual_required`.

The data-administrator workbench restored both server cases and completed
reviewed manual four-point registration with one independent check point per
side:

| Side | Server case | Registration | Independent RMS |
| --- | --- | --- | ---: |
| `main_page_1` | `vqc_0d436505e8794c06999ffa9dddd2d538` | `reviewed_manual_four_point` | `0.00081` |
| `main_page_2` | `vqc_05982f6198c142f9810665f7ea80c45c` | `reviewed_manual_four_point` | `0.00012` |

The capture session is `pair_complete`; both cases are
`ready_for_human_qc`. The workbench unlocked defect annotation only after
the append-only registration reviews were stored.

## Repair Case Publication

CASE005's supplied text facts are now preserved independently from the two
local registration cases:

- Repair case: `case-005-bg6-f069`
- Revision: `1`
- Schema: `VISUAL-QC-REPAIR-CASE-SOURCE-V2`
- Manifest SHA-256:
  `85c8c64cb97cf1ea1e567e4d1f7fc62ec00ebf02719939c74a5e0faf46298177`
- Identity status: `unresolved_alias`
- Model identity: `model_identity_resolved=false`
- Completeness: `symptom_linked`
- Reported source model: `TECNO/BG6`
- Catalog models: `BG6H/BG6h`

The board identity is exact, but the supplied and catalog model names are not
forced into one identity. Identity progresses monotonically only through a
complete revision with appended evidence. Only `conflict -> confirmed_alias`
requires a new correction record. A resolved identity is immutable; revision 1
remains unchanged.

## Evidence Boundary

- The Feishu row-level side label was not trusted because other collection
  rows label opposite-side photos identically. Side identity was assigned
  per image from visible board structure and verified against the point-map
  overlay.
- CASE005 is not a Golden Sample.
- No defect annotation or `no_visible_anomaly` conclusion was created.
- The published repair-case manifest is not visual diagnosis evidence.
- It is not confirmed defect evidence.
- It is not Golden Sample evidence.
- It is not training label evidence.
- It is not repair causality evidence.
- It is not field accuracy evidence.
- Model naming remains separate from board identity: the exact physical and
  engineering revision is F069 V1.2, while `TECNO/BG6` and `BG6H/BG6h`
  compatibility still requires explicit source confirmation.
- The server cases are local integration instances. Production remains `f278061`;
  the repair-case publication did not change production.

## Next Gate

Keep the repair-case manifest and physical-registration evidence as separate
fact layers until an explicit, reviewed link contract is approved. Human QC
conclusions still require their own evidence. For automatic registration, use
same-modality physical Golden references or a deliberately evaluated
cross-modal matcher; do not weaken ORB/AKAZE thresholds to force point-map
matches.

## 2026-07-29 Current Supplement: Repair Evidence Links

The controlled library is the authoritative source of truth for each immutable
repair-evidence-link revision. The server stores only a read-only projection
that can be rebuilt by validating and replaying that exact library revision.
The contract enforces one photo per binding; one link revision may contain
separate bindings for separate photos.

Repair-evidence detail is exposed only through the administrator/reviewer
detail API. Technicians have no repair-evidence detail route. A binding records
an evidence association only and carries no annotation, QC, Golden Sample,
training-label, repair-causality, or repair-action authority.

CASE005 keeps the source-reported U4000 association as `possibly_related` and
`not_assessed`. It has no visual defect conclusion and does not establish that
U4000 caused the reported symptom or that any repair action is required.

The owner-operated chain is:

```text
repair case revision
-> export linkable physical evidence
-> stage repair evidence link revision
-> validate/replay
-> sync read-only projection
-> inspect in internal workbench
```

This implementation and the local CASE005 projection are local evidence only.
Production remains unchanged at `f278061`; no production deployment, database,
or route was changed by this work.
