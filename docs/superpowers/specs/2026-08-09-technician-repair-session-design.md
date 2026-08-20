# Technician Repair Session Design

## Decision

Turn the existing source-controlled repair-flow state into one recoverable technician repair session. The session wraps the current board/model/intent identity, exact flow state and allowed usability feedback without changing repair logic or inventing new technical guidance.

The first increment applies only to declared `reviewed_flow` paths. H897 case navigation and any `source_boundary_only` path remain reference/navigation experiences and cannot be promoted into executable sessions merely because a case or component is visible.

## User Path

1. The technician selects a known model and current problem in the existing pilot entry.
2. Entering a reviewed flow creates or resumes one session bound to the exact board, model, board version and flow id.
3. Every recorded measurement, branch choice, action confirmation, post-action check, completion and reset updates the session snapshot locally.
4. Refreshing or reopening the same exact intent offers the unfinished session automatically; a different board/model/flow cannot consume it.
5. At terminal completion or an explicit source boundary, the technician can export a privacy-reduced JSON record.

## Contract

`TECHNICIAN-REPAIR-SESSION-V1` records:

- stable session id, created/updated timestamps and `active`, `completed`, `stopped_at_source_boundary` or `abandoned` status;
- exact `board_key`, technician-selected model, board version, intent, entry flow id and active flow id;
- normalized snapshots for every reviewed flow reached during the same task: current step, path history, recorded measurements, action execution, post-action checks, terminal and closed state;
- optional pilot usability feedback already allowed by the existing privacy-reduced contract.

It excludes photos, IMEI, phone/customer identity, free-form diagnosis, repair causality, inferred defect, model output, server credentials and source document contents. Unknown fields are removed on load and export. Invalid or cross-identity records fail closed.

## Storage And Recovery

Sessions are stored in browser `localStorage` under a new versioned key. The store keeps at most 50 records and replaces only the same session id. The application recovers only the newest unfinished session whose board/model/version/entry-flow identity exactly matches the current URL intent and dataset.

Resetting a repair flow does not silently erase history: the current session becomes `abandoned`, then a new session begins. Completed or stopped sessions remain exportable but are never auto-resumed.

## UI

The existing repair panel gains one compact session strip rather than a new page or nested card. It shows session state, last-saved time, resume status, and an icon/text export command. Existing measurement and result controls remain the primary surface. Case-navigation-only and reference-only boards do not show session controls.

The existing pilot feedback section remains separate: it measures whether location and source material were useful, while the repair session records what happened in the deterministic flow. Neither becomes technical truth automatically.

## Failure Behavior

- Corrupt storage is ignored and replaced only after the next valid user action.
- Dataset identity or flow mismatch prevents recovery and shows no stale measurements.
- Storage quota failure leaves the in-memory repair flow usable and reports that persistence failed.
- Export always revalidates and privacy-reduces the record before creating a file.
- No session operation uploads data or changes the controlled server.

## Testing

- Unit tests cover creation, normalization, exact-identity recovery, state replacement, reset/abandonment, deterministic export, privacy reduction and malformed storage.
- Integration tests prove existing repair-state mutations produce session snapshots without changing repair decisions.
- Browser QA covers desktop and 390 px entry, measurement/choice persistence, refresh recovery, terminal completion, reset, export affordance, contrast, overflow and runtime errors.

## Acceptance Boundary

This increment is complete when one existing reviewed flow can be started, partially completed, refreshed, resumed, finished and exported with exact source-controlled state. It does not add a new repair step, diagnose a board, synchronize sessions to a server, upload technician data, or claim that H897 case navigation is an executable SOP.
