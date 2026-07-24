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

## Evidence Boundary

- The Feishu row-level side label was not trusted because other collection
  rows label opposite-side photos identically. Side identity was assigned
  per image from visible board structure and verified against the point-map
  overlay.
- CASE005 is not a Golden Sample.
- No defect annotation or `no_visible_anomaly` conclusion was created.
- The server is a local integration instance. Production revision
  `f278061` does not yet accept the qualified-handoff contract.
- Model naming remains separate from board identity: the exact physical and
  engineering revision is F069 V1.2, while BG6/BG6H sales-model compatibility
  still requires explicit source confirmation.

## Next Gate

Bind CASE005's text repair facts to the two registered images before issuing
human QC conclusions. For automatic registration, use same-modality physical
Golden references or a deliberately evaluated cross-modal matcher; do not
weaken ORB/AKAZE thresholds to force point-map matches.
