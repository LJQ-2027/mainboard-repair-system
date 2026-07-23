# Visual QC Automatic Registration Baseline

## Status

The first server-side visual registration core, including ORB/AKAZE processing, persisted asynchronous jobs, and reviewed manual fallback, is deployed in production revision `f278061`. Historical local-only cases retain `VISUAL-QC-CASE-V1`; server-connected workbench drafts use `VISUAL-QC-CASE-V2` with recovery, reviewed registration, Golden state, and difference-review state.

Later admission hardening is local only: qualified handoff provenance, Admin List V2, Admin Detail V3, and browser physical-upload removal are not deployed. Qualified handoff must not target production until a separately approved deployment and migration verification completes.

The implementation consists of:

- deterministic point-map proxy generation with rotation, perspective, crop, brightness, contrast, and shadow variation;
- automatic board-contour evidence;
- ORB feature registration with AKAZE fallback;
- RANSAC homography estimation;
- normalized board-to-image matrices compatible with the existing manual registration coordinate convention;
- technical evidence for keypoints, matches, inliers, coverage, reprojection error, projected shape, and detector attempts;
- structured failure reasons and explicit fallback to `reviewed_manual_four_point`;
- five-board synthetic and 21-image Service Manual proxy benchmarks.

## Runtime

Create an isolated Python environment and install the CPU-only worker dependency:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-visual-qc.txt
```

Run the deterministic benchmark:

```powershell
.\.venv\Scripts\python.exe scripts\benchmark_visual_qc_registration.py
```

Outputs:

- `reports/visual-qc-registration-benchmark.json`
- `reports/visual-qc-registration-benchmark.md`

## Candidate Contract

Automatic output uses `VISUAL-QC-REGISTRATION-CANDIDATE-V1`, defined in `knowledge-base/visual-qc-registration-candidate-schema.json`.

A technically valid result has:

- `status: candidate`;
- `method: automatic_feature_homography`;
- `review_status: draft`;
- a normalized `board_to_image_matrix`;
- `requires_human_review: true`;
- evidence describing how the matrix was obtained.

A failed result has:

- `status: manual_required`;
- no matrix and no automatic method;
- a structured failure code;
- `requires_manual_registration: true`;
- `fallback.method: reviewed_manual_four_point`.

Technical thresholds are candidate-generation safeguards, not industrial quality limits. A candidate does not become a reviewed registration until Codex, acting as the data administrator, accepts it in the internal workbench. Overseas technicians do not enter this review path.

## Benchmark Result

The committed five-board benchmark covers ten engineering-map sides with two deterministic transforms per side:

- 20 synthetic proxy cases;
- 20 automatic candidates;
- mean normalized corner error: about `0.000812`;
- maximum normalized corner error: about `0.001463`;
- zero synthetic cases forced into a false reviewed state.

The Service Manual benchmark accounts for all 21 reviewed images:

- 4 images are comparable as installed main-board proxies for a currently compiled board;
- all 4 safely require manual registration;
- 17 are explicitly not comparable because they are exploded/sub-board evidence or lack a current five-board reference.

This is expected conservative behavior. None of the 21 images counts as physical-board field accuracy evidence.

## Evidence Boundary

- `synthetic_proxy` validates transformation recovery and failure behavior.
- `service_manual_proxy` validates structural attempt handling and evidence classification.
- Neither role may become a Golden Sample.
- Neither role may be counted as real defect-recognition or field-registration accuracy.
- The first real acceptance gate remains one known KM4/F151 bare-board front/back physical photo set.

## Current Implemented Increment

The registration core is wrapped in the versioned FastAPI job contract with persisted job state, automatic candidates, reviewed four-point fallback, Golden Sample versioning, difference candidates, and final QC evidence. New physical cases enter only through the acceptance-qualified handoff; the browser restores existing server cases and cannot upload a new physical capture. The remaining acceptance increment requires the first known KM4/F151 bare-board front/back photo set, independent real check points, and reviewed physical evidence.
