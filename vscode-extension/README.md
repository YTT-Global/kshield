# KShield for VS Code

Inline security warnings as you type, powered by your local KShield backend — the same engine the pre-commit hook uses, just faster feedback.

## What it does

- Scans a file every time you save it (debounced, so rapid saves don't spam the backend).
- Shows findings as squiggles in the editor — red for CRITICAL/HIGH, yellow for MEDIUM, blue for LOW.
- Hover over a squiggle for the finding's description and an ELI5 explanation of the fix.
- Quick Fix (💡) actions let you apply the suggested patch or suppress a rule type globally, without leaving the editor.
- A status bar item shows whether the KShield backend is reachable.

## Requirements

The extension talks to the KShield backend over HTTP — it does not bundle or start it. Start the backend first:

```bash
kshield start
# or, from a clone of this repo:
cd backend && SQLITE_FALLBACK=true uvicorn app.main:app --port 8000
```

## Settings

| Setting | Default | Description |
|---|---|---|
| `kshield.enabled` | `true` | Enable/disable inline scanning. |
| `kshield.backendUrl` | `http://127.0.0.1:8000` | Base URL of the KShield backend. |
| `kshield.scanOnSave` | `true` | Scan automatically on save. |
| `kshield.debounceMs` | `800` | Delay before a save triggers a scan. |

## Commands

- `KShield: Scan Current File`
- `KShield: Apply Suggested Fix` (invoked via Quick Fix)
- `KShield: Suppress This Rule` (invoked via Quick Fix)
- `KShield: Check Backend Connection`

## Development

```bash
npm install
npm run compile   # or npm run watch
```

Then press F5 in VS Code (with this folder open) to launch an Extension Development Host.

## Known limitations

- Findings are keyed by line number only — if the backend restarts mid-edit, positions may shift until the next scan.
- Auto-apply only works for findings that include a `patch_diff` (currently Broken Access Control); other finding types surface a Quick Fix to suppress the rule instead.
- `.kshield.yml` per-repo suppression config (read by the CLI) is not yet read by the extension — tracked as a follow-up.
