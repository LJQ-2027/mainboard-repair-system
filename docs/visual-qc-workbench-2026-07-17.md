# Visual QC Workbench Baseline

## Status And Route

`http://127.0.0.1:8898/assets/visual-qc-workbench/`

This document began as the local baseline at commit `45a8613`. The workbench now also implements the browser side of the approved server-led asynchronous architecture in `docs/superpowers/specs/2026-07-20-visual-qc-server-architecture-design.md`. Production deployment is still pending.

## Workflow

The current internal workbench supports the five compiled mainboard platforms:

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

When a QC API is configured, the browser creates a stable idempotency key, uploads the authorized image with byte progress, polls the persistent job, and restores interrupted synchronization after refresh. An automatic registration result remains a draft candidate until the operator checks the overlay and confirms it. A structured automatic failure returns to the same manual four-point process. IndexedDB remains the weak-network and in-progress editing layer; the server owns accepted cases and review evidence.

The server-side registration core in `scripts/visual_qc/` generates deterministic point-map proxies, returns draft automatic homography candidates with technical evidence, and falls back to the reviewed manual four-point method. FastAPI upload, persistent jobs, server review state, and browser integration are implemented locally. Golden Sample approval and difference-candidate review are available through the API but do not yet have workbench screens. See `docs/visual-qc-auto-registration-2026-07-20.md` and `docs/visual-qc-server-api-2026-07-20.md`.

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
