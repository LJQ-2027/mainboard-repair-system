# Visual QC Workbench Baseline

## Status And Route

`http://127.0.0.1:8898/assets/visual-qc-workbench/`

This document began as the local baseline at commit `45a8613` and now describes the **Local HEAD workbench contract** in `docs/superpowers/specs/2026-07-20-visual-qc-server-architecture-design.md`.

Production remains `f278061` at `https://cccsat.top/mb-repair-beta/assets/visual-qc-workbench/`. That authenticated pilot predates qualified handoff, List V2, Detail V3, and browser physical-upload removal. The production route must not be used for physical intake under the Local HEAD procedure until a separately approved deployment and migration verification completes. Neither route is a field-accuracy claim.

## Ownership And Workflow

Milo is the only source of real visual photos. Codex operates this internal workbench as the data administrator. Overseas technicians neither upload photos nor use this route. The backend role value `reviewer` is retained only as a compatibility identifier for data-administrator permissions.

The current workflow supports the five compiled mainboard platforms:

1. Milo supplies a named photo package and its known board, side, stage, evidence role, and capture setup.
2. Codex stages and audits the immutable source package, runs physical acceptance, then transfers only an acceptance-qualified handoff through the controlled CLI.
3. Open the server case catalog, filter by board/side/state, and restore a selected original into the workbench.
4. Review brightness, exposure, sharpness, resolution, and the capture checklist evidence.
5. Let the server propose registration or pair four board/photo anchors as the fallback.
6. Add an independent check point for manual registration and review normalized projection error.
7. Confirm registration, annotate visible defects, and decide every human or model candidate.
8. Complete the final human QC result and create a Golden only for a Milo-confirmed normal board.
9. Export the governed manifest, COCO data, complete dataset bundle, or readiness audit as required.

Cases and source image blobs are recoverable from IndexedDB. Imported JSON requires the original image to be selected again and accepted only after its SHA-256 and dimensions match.

When a QC API is configured, the acceptance-qualified handoff supplies stable idempotency and immutable provenance while the browser polls existing persistent jobs and restores accepted cases from the server catalog. The workbench does not upload new physical captures; local image import remains a draft and inspection aid only. An automatic registration result remains a draft candidate until Codex checks the overlay and confirms it. A structured automatic failure returns to the same manual four-point process. Confirmed normal-board captures can enter Golden Sample versioning; repair captures can request a difference heatmap and receive `model_candidate` regions that remain pending until Codex confirms, rejects, or defers each one. Final `no_visible_anomaly` or `confirmed_anomaly` decisions are synchronized as immutable server QC review versions. Editing an annotation invalidates the synchronized-review marker and requires a new final review. IndexedDB remains the in-progress editing layer; the server owns accepted cases and evidence.

The server-side registration core in `scripts/visual_qc/` generates deterministic point-map proxies, returns draft automatic homography candidates with technical evidence, and falls back to the reviewed manual four-point method. Controlled handoff transport, persistent jobs, server review state, Golden Sample approval, difference-candidate review, and browser restoration are implemented locally. See `docs/visual-qc-auto-registration-2026-07-20.md` and `docs/visual-qc-server-api-2026-07-20.md`.

Historical local cases remain `VISUAL-QC-CASE-V1`. New server-connected drafts use `VISUAL-QC-CASE-V2`, whose schema explicitly permits server synchronization, reviewed automatic registration, physical-board capture sessions, capture checklists, capture-setup Golden state, and difference-review state without silently changing V1 semantics.

## Data Boundary

- The KM4 Service Manual image is a proxy used to verify interaction, projective overlay, annotation, storage, and export behavior.
- Every image records `physical_capture` or `proxy_sample` as its evidence role. Proxy samples may exercise the tools but are rejected by the training gate even if their image quality is otherwise acceptable.
- Physical imports require all three capture confirmations. One capture session may contain only one board identity, stage, evidence role, and capture setup; both the intake validator and server enforce this.
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

Training-ready V2 data requires a valid image hash, a confirmed physical-capture checklist, acceptable image quality, reviewed registration, legal normalized coordinates, resolved board identity, reviewed human labels, a final human QC result, and a matching eligible server QC review. The data-administrator manifest is `VISUAL-QC-TRAINING-MANIFEST-V1`; its image route exposes only originals attached to an eligible latest QC review. `GET /datasets/coco` derives `VISUAL-QC-COCO-V1` directly from that manifest, and `GET /datasets/bundle` emits a deterministic ZIP with governed originals. Overseas technician access hides these tools and remains blocked by the API role check.

## Real Acceptance Gate

The next evidence milestone is one known KM4/F151 bare mainboard photographed on both sides. That sample must be used to recheck registration quality, visible component association, and annotation projection before any visual QC accuracy claim or model training begins.

Synthetic point-map transforms and the 21 reviewed Service Manual images may be used before that gate as explicit proxy evidence. They cannot become Golden Samples or field-accuracy evidence.
