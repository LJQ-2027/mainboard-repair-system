# Frontend Console Redesign

## Design read

This product is an internal engineering knowledge workbench for overseas repair technicians, L4 technical support, Chinese technical staff, and manufacturing center collaborators.

It should feel like a durable diagnostic console and repair knowledge system, not a marketing page, AI demo, or slide-like project report.

## Direction

Use a professional light-mode operations console:

- Diagnostic Workbench is the default entry.
- Sidebar navigation is organized by real work areas, not by every underlying page.
- Top area becomes a compact command and status bar.
- Large empty overview panels are removed from the default path.
- Knowledge, model, fault, SOP, case, and signal data are surfaced as related diagnostic assets.
- AI remains an assistive layer, not the visual protagonist.

## Navigation rule

The sidebar should expose only primary work destinations:

- Diagnostic Workbench
- Knowledge Center
- Model Materials
- Fault Packages
- SOP and Cases
- Readiness Board

Utility tools such as historical diagnosis, SN material lookup, and log analysis can stay as compact secondary actions.

Detailed pages such as MTK signal lookup, L4 report insights, gap requests, SOP drafts, and case templates should be reached from diagnostic results or their parent pages, not from the main sidebar.

## Visual rules

- Use restrained neutral surfaces with one engineering blue accent.
- Prefer structured rows, panels, status bars, and tables over large decorative cards.
- Keep typography compact and clear for long office use.
- Every clickable control must have readable hover, active, and focus states.
- Avoid purple-blue AI gradients, glassmorphism, decorative blobs, oversized hero layouts, emoji icons, and template-like three-card feature rows.

## QA expectations

After implementation, verify:

- Desktop route opens and the diagnostic workbench is the first active screen.
- Mobile layout has no horizontal overflow.
- Sidebar navigation, top search, diagnostic input, selects, quick actions, and buttons remain usable.
- Active, hover, and focus states keep sufficient text/background readability.
- Browser console has no runtime errors on the primary path.
