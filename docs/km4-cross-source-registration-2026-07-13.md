# KM4/F151 Cross-Source Registration Baseline

## Route

`http://127.0.0.1:8898/assets/cross-source-registration/index.html`

## Implemented

- The F151 point-map plane is the normalized `0-1` geometry source.
- A reviewed four-anchor homography projects board coordinates onto the Service Manual installed-mainboard proxy image.
- Seven source-supported entities share stable identities across the proxy image, point map, schematic evidence, repair guidance, and Three.js 2.5D view.
- The 2.5D substrate uses an outline derived from the point map. Component footprints use normalized point-map geometry; visual heights are generic and explicitly not engineering dimensions.
- Selection is synchronized across view markers, the entity list, and 3D mesh picking.

## Current Entities

`U2001`, `U4000`, `X2100`, `U0600`, `J6101`, `VBAT1`, and `VBUS1`.

## Evidence Boundary

The available proxy photograph shows the board installed with shields. It supports board-context registration but does not expose most chip bodies. Markers for concealed entities therefore indicate the registered position below the shield, not visual component detection. Standardized physical front/back photographs are still required to validate field-photo registration and exposed-component correspondence.

## Verification

- Six Node tests cover normalized coordinates, homography, inverse projection, polygon projection, selection state, and picking.
- Three Python tests plus the standalone validator cover assets, anchors, normalized board outline and entity geometry, stable identities, and source links.
- Desktop `1440x900` and mobile `390x844` browser paths cover all three views, seven markers, synchronized selection, nonblank WebGL pixels, responsive overflow, and runtime errors.
- Screenshots: `output/playwright/km4-cross-source-photo.png`, `km4-cross-source-pointmap.png`, `km4-cross-source-desktop.png`, and `km4-cross-source-mobile.png`.
