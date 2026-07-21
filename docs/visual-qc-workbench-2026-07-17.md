# Visual QC Workbench Baseline

## Status And Route

`http://127.0.0.1:8898/assets/visual-qc-workbench/`

This document began as the local baseline at commit `45a8613`. The workbench now implements the browser side of the approved server-led asynchronous architecture in `docs/superpowers/specs/2026-07-20-visual-qc-server-architecture-design.md`. The controlled pilot is deployed at `https://cccsat.top/mb-repair-beta/assets/visual-qc-workbench/`; this route is an authenticated pilot, not a field-accuracy claim.

## Workflow

The current internal workbench supports the five compiled mainboard platforms:

1. Select the known board and board side.
2. Start or resume one capture session for the same physical board and capture setup.
3. Import a `golden_reference`, `before_repair`, or `after_repair` image.
4. Confirm complete-board framing, focus/lens cleanliness, and even unobstructed lighting.
5. Capture the other declared board side in the same session when the board has two sides.
6. Review brightness, exposure, sharpness, and resolution checks.
7. Let the server propose registration or pair four board/photo anchors as the fallback.
8. Add an independent check point when using manual registration and review the normalized projection error.
9. Confirm registration, annotate visible defects, and review each human or model candidate.
10. Complete the final human QC result. Server-connected physical cases persist an append-only QC review version; local-only cases remain browser drafts.
11. Export the V2 JSON and annotated PNG preview. Reviewers additionally see the server-owned eligible case, confirmed annotation, covered-category and excluded-case totals, together with the current primary gate reasons. A compact disclosure identifies each excluded board, side, case suffix, and blocker without exposing actor identity. Reviewers can download the current manifest, deterministic COCO dataset, or complete ZIP containing both contracts, an index, and all eligible originals.

Cases and source image blobs are recoverable from IndexedDB. Imported JSON requires the original image to be selected again and accepted only after its SHA-256 and dimensions match.

When a QC API is configured, the browser creates a stable idempotency key, uploads the authorized image with byte progress, polls the persistent job, and restores interrupted synchronization after refresh. An automatic registration result remains a draft candidate until the operator checks the overlay and confirms it. A structured automatic failure returns to the same manual four-point process. Reviewed normal-board captures can enter reviewer-gated Golden Sample versioning; reviewed repair captures can request a difference heatmap and receive `model_candidate` regions that remain pending until a technician confirms, rejects, or defers each one. Final `no_visible_anomaly` or `confirmed_anomaly` decisions are synchronized as immutable server QC review versions. Editing an annotation invalidates the browser's synchronized-review marker and requires a new final review. IndexedDB remains the weak-network and in-progress editing layer; the server owns accepted cases and review evidence.

The server-side registration core in `scripts/visual_qc/` generates deterministic point-map proxies, returns draft automatic homography candidates with technical evidence, and falls back to the reviewed manual four-point method. FastAPI upload, persistent jobs, server review state, Golden Sample approval, difference-candidate review, and browser integration are implemented locally. See `docs/visual-qc-auto-registration-2026-07-20.md` and `docs/visual-qc-server-api-2026-07-20.md`.

Historical local cases remain `VISUAL-QC-CASE-V1`. New server-connected drafts use `VISUAL-QC-CASE-V2`, whose schema explicitly permits server synchronization, reviewed automatic registration, physical-board capture sessions, capture checklists, capture-setup Golden state, and difference-review state without silently changing V1 semantics.

## Data Boundary

- The KM4 Service Manual image is a proxy used to verify interaction, projective overlay, annotation, storage, and export behavior.
- Every image records `physical_capture` or `proxy_sample` as its evidence role. Proxy samples may exercise the tools but are rejected by the training gate even if their image quality is otherwise acceptable.
- Physical uploads require all three capture confirmations. One capture session may contain only one board identity, stage, evidence role, and capture setup; the server enforces this again inside the database write transaction.
- `pair_complete` means every source-declared side for that board has been captured in the session. It does not mean the board is normal, registered, or approved.
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

Training-ready V2 data requires a valid image hash, a confirmed physical-capture checklist, acceptable image quality, reviewed registration, legal normalized coordinates, resolved board identity, reviewed human labels, a final human QC result, and a matching eligible server QC review. The reviewer-only server manifest is `VISUAL-QC-TRAINING-MANIFEST-V1`; its image route exposes only originals attached to an eligible latest QC review. `GET /datasets/coco` derives `VISUAL-QC-COCO-V1` directly from that manifest, so local drafts and proxy samples cannot bypass the server gate. `GET /datasets/bundle` emits a deterministic ZIP whose COCO image paths match the included originals and whose `VISUAL-QC-DATASET-BUNDLE-V1` index preserves image hashes and MIME types. The reviewer workbench shows the same server-owned counts and downloads; technicians do not see that section and remain blocked by the API role check.

## Real Acceptance Gate

The next evidence milestone is one known KM4/F151 bare mainboard photographed on both sides. That sample must be used to recheck registration quality, visible component association, and annotation projection before any visual QC accuracy claim or model training begins.

Synthetic point-map transforms and the 21 reviewed Service Manual images may be used before that gate as explicit proxy evidence. They cannot become Golden Samples or field-accuracy evidence.
