# Plan + Tasks: Profil-Sidebar und Reasoning

Spec: `profile-sidebar-and-reasoning.md` · Branch: `feat/profile-sidebar` (Worktree `~/Development/hermes-webui-profile-sidebar`)

## Plan

### Teil A (nur `static/sessions.js`, `static/panels.js`, `static/style.css`)
- `_showAllProfiles` bleibt als Variable (viele Aufrufer), ist aber fest `true`.
  Toggle, localStorage-Key `hermes-show-all-profiles`, Storage-Event-Handler und der Profilname in `metaBits` entfallen.
- Neue reine Funktion `_groupSessionsByProfile(sessions, profileNames, activeProfile)` → `[{key, label, profile, items, isActive}]`.
  Sie ist testbar und ersetzt den Block "Group sessions by date". Der Gruppenschlüssel ist `profile:<name>`,
  und die Gruppen werden wie bisher über `g.key` statt `g.label` eingeklappt.
  Die Rückgabe enthält `{label, items}` und passt damit zur bestehenden Render-Schleife, zur Virtualisierung und zu `flatSessionRows`.
- Profilnamen kommen aus `_profilesCache` (`/api/profiles`). Ist der Cache leer, wird einmal `_profileDropdownFetchFresh()` geholt und danach neu gerendert.
  Zusätzlich werden Profile aus `s.profile` aufgenommen, damit keine Session verloren geht.
- Das 5er-Limit wird nach dem Gruppieren angewendet (die aktive Session bleibt sichtbar).
  Bei aktiver Suche gilt kein Limit. "Mehr anzeigen" nutzt ein In-Memory-Set.
- `⋯`-Menü nach dem Muster von `_showProjectContextMenu`. Der Button "+ Profil hinzufügen" ruft `openProfileCreate()` auf.
  Nach `create` und `delete` in `panels.js` folgt `renderSessionList()`.
- Der Filter "aktiv" blendet leere Gruppen aus, sobald Suche, Projekt-Chip oder CLI-Tab aktiv sind.
- Texte sind wie die Nachbar-Toggles ("Show N archived") hartkodiertes Englisch, damit die Locale-Parität nicht berührt wird.

### Teil B (Diagnose zuerst, dann gezielter Fix)
1. Rohen Run-Stream vom Gateway mitschneiden (`POST /v1/runs` mit Claude und `reasoning_effort: high`, dann `GET /v1/runs/{id}/events`).
2. Je nach Befund Key-Mapping in `api/gateway_chat.py`, Persistierung beim Settle oder "Provider-Limit" dokumentieren.

## Tasks

- [x] T0 Worktree/Branch anlegen, Spec kopieren
- [x] T1 `_groupSessionsByProfile` + Test `tests/test_profile_sidebar_grouping.py`
- [x] T2 `_showAllProfiles` fest an, Toggle/Storage/metaBits entfernt
- [x] T3 Render-Block ersetzt (Header, Aktiv-Markierung, Collapse-Key, 5er-Limit, "Show N more")
- [x] T4 `⋯`-Menü, "+ Add profile", Refresh nach create/delete
- [x] T5 CSS
- [x] T6 Bestehende Tests angepasst (1611, 673, 856, long_history_perf: Datumsgruppen/Toggle entfernt)
- [x] T7 Browser-Check (Wegwerf-Instanz :8788, Headless-Chromium): Gruppen, Reihenfolge, leere Profile, Einklappen + Reload,
  "Show more", Menü, Klick auf fremdes Profil wechselt das Profil, "+ Add profile" öffnet das Formular
- [x] T8 Teil B Diagnose (siehe unten)

## Befund Teil B (Diagnose, kein WebUI-Fix)

Gateway `hermes-agent 0.21.5`, Claude (`claude-opus-5-5`, `claude-sonnet-5-5`), `reasoning_effort: high`:

1. **`/v1/runs` (Live-Konfiguration, `USE_RUNS_API=true`)**: Der Event-Stream enthält nur `message.delta` und `run.completed`,
   nie `reasoning.available`. Ursache im Gateway: `api_server_runs._execute_run` übergibt bei kanonischen Admissions nur
   `stream_delta_callback`, `tool_start_callback` und `tool_complete_callback` an `observe_api_turn`.
   `reasoning_callback` wird nicht registriert, obwohl `session_api_turn._OBSERVER_KEYS` ihn kennt.
   Das lässt sich in der WebUI nicht beheben. Es braucht einen Fix im Agent (Upstream-Issue).
2. **`/v1/chat/completions` (Legacy-Pfad, `USE_RUNS_API=false`)**: Das Gateway sendet `delta.reasoning_content`,
   und die WebUI mappt es bereits (`_gateway_sse_reasoning_delta`, Persistierung über `STREAM_REASONING_TEXT`).
   Ohne WebUI-Kontext hat Claude bei einer Rechenaufgabe 3 von 3 Mal gedacht (12 bis 16 Chunks).
   Mit WebUI-Systemprompt oder Kontext-Präfix waren es 0 von 5 (WebUI selbst: 0 von 4). Ob das Adaptive Thinking von Claude
   (das Modell entscheidet selbst) oder ein Gateway-Effekt ist, bleibt offen.
3. Die UI-Seite braucht keine Änderung: Das Backend liefert hier nichts, was die Karte nicht schon verarbeiten würde.
   Nicht geprüft wurden Persistierung und Reload mit einem Claude-Run, der wirklich Reasoning liefert.
