# Visual QC Registration Benchmark

This report contains proxy engineering evidence only. It does not establish field QC accuracy.

## Synthetic point-map transforms

- Cases: 20
- Automatic candidates: 20
- Manual fallback: 0
- Mean normalized corner error: 0.000812214291121979
- Maximum normalized corner error: 0.0014629799484178253

## Reviewed Service Manual proxies

- Reviewed images: 21
- Comparable attempts: 4
- Not comparable: 17
- Status counts: {"manual_required": 4, "not_comparable": 17}

## Evidence boundary

- Synthetic and Service Manual images never count as physical-board accuracy evidence.
- Automatic registration remains a draft candidate until human review.
- Failure returns the reviewed manual four-point workflow.
- A known bare-board front/back physical photo set remains the real acceptance gate.
