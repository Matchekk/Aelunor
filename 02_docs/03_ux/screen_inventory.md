# Screen Inventory

## Aktive v1-Screens

| Screen | Route | Dateien |
| --- | --- | --- |
| Session Hub | `/v1/hub` | `features/session/SessionHubWorkspace.tsx` |
| Campaign Route Gate | `/v1/campaigns/:id/...` | `app/routing/RouteGate.tsx` |
| Claim | campaign workspace vor Setup/Play | `features/claim/ClaimWorkspace.tsx` |
| Setup Overlay | bei offenem Welt-/Charakter-Setup | `features/setup/SetupWizardOverlay.tsx` |
| Play | campaign play workspace | `features/play/CampaignWorkspace.tsx` |
| Boards Modal | query-state surface | `features/boards/BoardsModal.tsx` |
| Drawers | character/npc/codex | `features/drawers/DrawerHost.tsx` |
| Context Modal | context query result | `features/context/ContextModal.tsx` |
| Settings | global dialog | `shared/ui/SettingsDialog.tsx` |

## Legacy

`app/static/` liefert weiterhin `/`. Diese UI ist nicht der aktive Produktpfad und soll nicht fuer neue Features erweitert werden.
