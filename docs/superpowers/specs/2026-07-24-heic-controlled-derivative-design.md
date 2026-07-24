# Controlled HEIC Derivative Design

## Goal

Admit Milo-supplied HEIC captures into the controlled visual source chain
without relabeling a decoded JPEG as the original image.

## Contract

Existing JPEG, PNG, and WebP packages remain
`VISUAL-QC-SOURCE-PACKAGE-V1`.

A package containing at least one HEIC source uses
`VISUAL-QC-SOURCE-PACKAGE-V2`. Each V2 entry retains the existing flat image
fields as the downstream working image and adds:

- `source_original`: original filename, canonical object path, MIME type,
  byte size, and SHA-256;
- `derivation`: `null` for an unchanged supported source, otherwise the
  decoder name/version, operation, primary-image selection, EXIF orientation
  handling, output format and fixed encoding parameters, plus input and
  output SHA-256 values.

HEIC originals are stored under `objects/source-originals/`. Working images
remain under `objects/originals/`, so intake, registration, handoff, and server
paths continue to consume browser/OpenCV-compatible images.

## Decoder And Output

The owner-side administration environment uses pinned `pillow-heif` and
Pillow. HEIC conversion:

1. opens the HEIC container through `pillow-heif`;
2. selects only the declared primary image;
3. applies EXIF orientation exactly once;
4. converts to 8-bit RGB;
5. writes JPEG with fixed quality, subsampling, progressive, optimize, and
   metadata settings;
6. reopens the output and records dimensions, MIME, byte size, and SHA-256.

The manifest records the actual decoder and Pillow versions. Byte identity is
required for repeated staging with the same package ID; a toolchain change
that changes bytes creates a package conflict instead of silently rewriting
history.

## Validation

Validation must fail closed when:

- the HEIC container or primary image cannot be decoded;
- source or working bytes do not match their canonical paths or hashes;
- derivation input/output hashes do not match the linked evidence;
- an unchanged image declares a derivation;
- a HEIC source lacks derivation evidence;
- the working image is not JPEG/PNG/WebP;
- proxy revocation matches either the original or working hash;
- a package, object, or derivative path crosses a symlink or Windows reparse
  boundary.

The source-library audit counts and checks source originals separately while
retaining its current package and working-object totals.

## Boundaries

- A derived JPEG is a working representation, not a new physical original.
- Decoding does not confirm board identity, side, defect, Golden status,
  registration accuracy, repair outcome, or training eligibility.
- Existing source packages are not migrated or rewritten.
- HEIC decoding remains an owner-side intake capability; the controlled
  server receives only the validated working image and manifest-bound
  provenance.
