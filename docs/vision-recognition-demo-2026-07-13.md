# Internal Vision Recognition Demo

## Purpose

This demo validates the first visual-assistance pipeline before physical mainboard photos are available. It uses 21 reviewed Service Manual references covering KM4, KL4, CLA5, KJ5, CM5, CM6, and X6880.

Open the local route:

`http://127.0.0.1:8898/assets/vision-recognition-demo/index.html`

## Capabilities

- Load an image locally by upload, drag and drop, or selecting a reviewed sample.
- Check resolution, brightness, contrast, clipping, and image sharpness.
- Extract a compact browser-side visual feature vector.
- Return the three closest unique model candidates with the matching reference role and source page.
- Keep all query-image processing in the browser; the demo does not upload images.

## Validation Scope

The demo is an internal material-based retrieval baseline, not a trained production classifier. Similarity values are retrieval scores, not calibrated recognition probabilities. The current references are manual structure images and installed-board images; they are not standardized isolated front/back physical-board photographs.

The demo therefore validates:

- reference-library loading;
- capture-quality feedback;
- model-candidate ranking;
- technician-facing interaction and responsive layout.

It does not yet validate field-photo robustness, board-side recognition, revision discrimination, component defects, or fault diagnosis. Those require standardized physical photos and later labeled repair cases.

## Verification

- Seven Node unit tests cover quality analysis, feature extraction, cosine similarity, exact-reference retrieval, and unique-model ranking.
- The Python validator confirms seven models, 21 approved references, and balanced structure/mainboard/subboard roles.
- Desktop and mobile browser checks cover sample selection, file upload, result rendering, responsive layout, image loading, console errors, and overflow.
