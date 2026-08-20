# KJ6 / KM4 / KM4s engineering-source intake

Received from Milo on 2026-07-31 from the desktop folder
`package/KJ6、KM4和KM4s`.

## Accepted new sources

- `packages/KJ6-H897/`: exact H897 mainboard V1.2 placement and schematic.
- `packages/KM4S-H6932-SUB-ONLY/`: H6932 sub-board V1.0 placement and
  schematic only. This package does not establish that KM4s mainboard sources
  are available.

## Exact duplicates not copied

The four F151 files in the incoming folder are byte-identical to the canonical
KM4/F151 files already stored under the 2026-07-02 in-house Top20 package. The
intake manifest records their canonical paths and SHA-256 values instead of
adding duplicate binaries.

## Use boundary

- H897 may enter the existing normalized-coordinate board compiler after a
  dedicated board profile and side mapping are reviewed.
- H6932 may be used only for the KM4s sub-board unless exact mainboard sources
  arrive later.
- None of these files may be substituted for KM4n/XK67J V1.0.
- Engineering drawings are reference sources, not physical-photo or visual-QC
  accuracy evidence.
