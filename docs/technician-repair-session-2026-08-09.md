# Technician Repair Session

## Scope

`TECHNICIAN-REPAIR-SESSION-V1` adds recoverable task continuity to the existing source-controlled repair flows. It does not add a diagnostic model, a repair branch, an electrical tolerance, a server upload, or a new source of technical truth.

A session is bound to the exact `board_key`, selected model alias, board version, entry intent and entry flow. It snapshots only the declared repair-flow state: current step, history, finite measurements, terminal, action execution, post-action check and closed state. Unknown fields are removed during storage and export.

Only executable reviewed datasets receive session controls. XK67J remains `source_compiled_reference_only / source_boundary_only`, and H897 case navigation remains non-executable. Both can still provide source and location context without producing a formal repair session.

## Technician Behavior

- Starting an eligible flow creates or resumes the newest exact unfinished session.
- Every accepted measurement, choice, handoff, action record, post-action check and close updates local storage.
- Refreshing the same exact task restores the existing state; a different board, model or flow cannot consume it.
- Resetting an unfinished task marks the old record `abandoned` and starts a distinct record.
- Starting a new round after a completed or source-boundary result preserves that terminal result and starts a distinct active record.
- Export produces one privacy-reduced JSON file for the current session.
- Storage failure does not block the in-memory repair flow and is shown as a non-blocking save error.

Sessions remain browser-local and non-authoritative. They are not synchronized to the controlled server and do not update point maps, schematics, repair guides, cases, visual QC labels or training data.

## Verification

P0-P2 checks on 2026-08-09 covered the session contract, exact recovery, declared-graph replay, reachable handoff validation, malformed-data rejection, 50-record retention, deterministic export, existing repair branches, repeated reset/write-retry behavior and source-boundary gating. The complete Node suite passed 445 tests with zero failures. Independent review found one P1 and three P2 issues during development; all were fixed and the final re-review reported no remaining P1/P2.

P3 browser QA used the local technician entry and KM4 `no-power-small-current-page-10` path. Chrome extension health checks passed, but no controllable Chrome instance was connected, so the test used the Codex in-app Chromium backend. Desktop and 390 px checks covered entry selection, two measurement steps, refresh recovery, terminal action, execution record, post-action check, completion, same-flow re-entry, new-round history preservation, export trigger and XK67J reference-only gating. A deliberately forged local-storage action was rejected and the UI restarted from the declared first step. The mobile viewport had no horizontal overflow, the session/export controls fit their container, the export control measured 16.36:1 contrast, the adjusted disabled reset state measured 4.19:1, and the browser runtime log was empty. Temporary QA local-storage records were removed after the test.

Production `0594b06581ec41085b6e281159ee52b65ac80081` was deployed on 2026-08-09 through the controlled upgrade path. The byte-bound 71,964,281-byte archive passed all ten migration and rollback checks from production `7ed316c`, both PM2 services returned online, unauthenticated entry returned `401`, and the existing Visual-QC case/job counts were preserved. Production browser P4 loaded all 14 model aliases and completed the KM4 no-power path through measurement, refresh recovery, terminal action, post-action check, closure and local feedback at desktop and 390 px widths. XK67J reached its explicit missing-electrical-standard boundary without a formal session strip. There were no application warnings/errors or horizontal overflow. The browser backend did not expose a download event, so export correctness remains covered by the deterministic serialization/unit tests and the enabled production controls rather than a captured production file.

The controlled system and return path are ready for the first human trial. No Chinese-expert or overseas-technician field result has been received yet; operator QA is deployment evidence, not field usability evidence.
