# Board Catalog Batch Acceptance

Catalog: `REPAIR-WORKBENCH-BOARDS-V1`

## Board Results

| Board | Status | Designators | SCH linked | Reviewed entities | Repair flows | Reference | Repair coverage |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| `km4-f151` | PASS | 1,172 | 672 | 7 | 3 | `photo_proxy` | `None` |
| `kl4-f201` | PASS | 1,221 | 710 | 3 | 1 | `photo_proxy` | `reviewed_flows` |
| `cm6-h8918` | PASS | 1,205 | 500 | 6 | 3 | `photo_proxy` | `reviewed_flows` |
| `ck6n-h6929` | PASS | 1,177 | 506 | 10 | 4 | `point_map_only` | `reviewed_flows` |
| `bg6m-f069m` | PASS | 1,115 | 604 | 10 | 0 | `point_map_only` | `source_unavailable` |
| `bg6h-f069` | PASS | 1,126 | 604 | 12 | 0 | `point_map_only` | `source_available_pending_review` |
| `xk67j-shared` | PASS | 1,040 | 505 | 13 | 1 | `reviewed_physical_photo_navigation` | `source_boundary_only` |

## Coverage Gates

| Gate | Result | Evidence |
| --- | --- | --- |
| Five or more board platforms | PASS | km4-f151, kl4-f201, cm6-h8918, ck6n-h6929, bg6m-f069m, bg6h-f069, xk67j-shared |
| Shared platform across sales models | PASS | cm6-h8918, bg6h-f069, xk67j-shared |
| Photo-proxy and point-map-only references | PASS | photo_proxy, point_map_only, reviewed_physical_photo_navigation |
| Reviewed-flow and reference-only repair coverage | PASS | reviewed_flows, source_available_pending_review, source_boundary_only, source_unavailable |
| Shared and independent point-map source layouts | PASS | independent_per_side, shared_multi_page |
| Source-named board sides | PASS | ck6n-h6929 |
| Confidence-limited location-only entities | PASS | km4-f151, kl4-f201, cm6-h8918, ck6n-h6929, bg6m-f069m, bg6h-f069, xk67j-shared |

## Scope Boundaries

- Visual defect recognition
- Physical photo registration accuracy
- CAD geometry
- Electrical connectivity inference
- Field repair effectiveness

**Sufficient for current source-to-2.5D pipeline: YES**
