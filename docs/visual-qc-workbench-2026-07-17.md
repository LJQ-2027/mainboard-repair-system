# Visual QC Workbench Baseline

## Status And Route

`http://127.0.0.1:8898/assets/visual-qc-workbench/`

This document records the implemented local baseline at commit `45a8613`. It is not the production deployment architecture. The approved target is the server-led asynchronous architecture in `docs/superpowers/specs/2026-07-20-visual-qc-server-architecture-design.md`.

## Workflow

The current internal workbench supports the five compiled mainboard platforms and keeps all photos in the local browser:

1. Select the known board and board side.
2. Import a `golden_reference`, `before_repair`, or `after_repair` image.
3. Review brightness, exposure, sharpness, and resolution checks.
4. Pair four board/photo anchors to solve a homography.
5. Add at least one independent check point and review the normalized projection error.
6. Confirm the registration manually.
7. Draw rectangle or polygon defect annotations.
8. Confirm or reject each human annotation and finalize the QC result.
9. Export the `VISUAL-QC-CASE-V1` JSON and an annotated PNG preview.

Cases and source image blobs are recoverable from IndexedDB. Imported JSON requires the original image to be selected again and accepted only after its SHA-256 and dimensions match.

This `local_only` behavior remains truthful for V1. The next contract version will upload authorized physical-board photos to the controlled server, persist processing jobs and review state centrally, and retain IndexedDB only for draft recovery and weak-network retry.

## Data Boundary

- The KM4 Service Manual image is a proxy used to verify interaction, projective overlay, annotation, storage, and export behavior.
- Every image records `physical_capture` or `proxy_sample` as its evidence role. Proxy samples may exercise the tools but are rejected by the training gate even if their image quality is otherwise acceptable.
- Registration error is reported as normalized RMS and maximum error. No industrial pass threshold is invented.
- Component association is suggested only when the annotation center falls inside a compiled footprint. Overlapping footprints resolve to the smallest area. Otherwise the defect stays board-level.
- Human annotations and future `model_candidate` records remain separate. Model candidates cannot become confirmed labels without human review.
- No current output is evidence of automatic defect recognition or real-board registration accuracy.

## Dataset Tools

Validate one or more case files:

```powershell
py -3 scripts/validate_visual_qc_dataset.py case.visual-qc.json
```

Apply the stricter training gate:

```powershell
py -3 scripts/validate_visual_qc_dataset.py --training-ready cases/
```

Export reviewed cases to deterministic COCO:

```powershell
py -3 scripts/export_visual_qc_coco.py cases/ visual-qc.coco.json
```

Training-ready data requires a valid image hash, acceptable image quality, reviewed registration, legal normalized coordinates, resolved board identity, reviewed human labels, and a final human QC result.

## Real Acceptance Gate

The next evidence milestone is one known KM4/F151 bare mainboard photographed on both sides. That sample must be used to recheck registration quality, visible component association, and annotation projection before any visual QC accuracy claim or model training begins.

Synthetic point-map transforms and the 21 reviewed Service Manual images may be used before that gate as explicit proxy evidence. They cannot become Golden Samples or field-accuracy evidence.
