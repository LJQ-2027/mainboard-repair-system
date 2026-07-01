# Top20 Model Board Assets Design

## Goal

Prepare the project to receive Manufacturing Center's Top20 mainboard point-location images and board photos without waiting for the actual files.

## Scope

Included:

- A structured model asset registry in `knowledge-base/model-board-assets.json`.
- A source-material folder convention for model board images.
- A front-end `机型资料库` page that shows Top20 model readiness, available image slots, related L4 report signals, and material gaps.
- Empty-state language that clearly says the actual images are pending.

Excluded:

- Upload backend.
- Image annotation editor.
- BoardView parsing.
- Interactive point highlighting.
- AI image recognition.

## Data Model

Each model record contains:

- model name and aliases.
- priority source, such as L4 report ranking or Manufacturing Center Top20.
- board image slots: front board photo, back board photo, front point map, back point map, schematic/BOM optional.
- version and confirmation fields.
- related high-frequency faults and source ids.
- status: `pending_assets`, `partial_assets`, `ready_for_review`, or `ready_for_beta`.

## UX

The model library is an operational intake page, not a polished image viewer yet. It should answer:

- Which Top20 models are already registered?
- Which board images are missing?
- Which models overlap with L4 report priorities?
- What should Milo ask Manufacturing Center to provide next?

## Verification

- JSON parses.
- Front-end fetches `model-board-assets.json`.
- `机型资料库` page renders model cards, search, and status filter.
- Desktop and mobile P3 checks cover selected nav readability and no horizontal overflow.
