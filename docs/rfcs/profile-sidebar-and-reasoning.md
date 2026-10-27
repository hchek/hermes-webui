# Spec: Sidebar nach Profilen gruppieren + Reasoning sichtbar machen

Status: Entwurf · Ziel: Fork von hermes-webui · Vorbild: Sidebar von Hermes Desktop

## Teil A: Sidebar nach Profilen gruppieren

### Ist-Zustand
- `renderSessionListFromCache()` (`static/sessions.js`, ca. Zeile 9884) gruppiert nach Datum
  (Pinned / Today / Yesterday / ...); der Einklapp-Zustand liegt in localStorage
  `hermes-date-groups-collapsed`, der Gruppenschlüssel ist `g.label`.
- Fremde Profile kommen nur über den Toggle "Show N from other profiles"
  (`_showAllProfiles`, `?all_profiles=1`); jede Session hat dann `s.profile`.
- Ein Klick auf eine Session eines anderen Profils wechselt das Profil schon
  (`_ensureSidebarSessionProfile`).
- Ein Profil wird über `openProfileCreate()` (`static/panels.js`) → `POST /api/profile/create` angelegt.
- Die Profilliste kommt von `GET /api/profiles`.

### Soll
```
▾ default                     ⋯
    Hermes WebUI Passwort…   21h
    Automatisierter Workfl…   2d
    … (5 neueste, dann "Mehr anzeigen")
▾ discord-bro                 ⋯
    Gestern erstellten Ent…  now
    …
▸ scjournal                   ⋯   (eingeklappt)
[ + Profil hinzufügen ]
```

### Anforderungen
1. Es gibt eine Gruppe pro Profil. Das aktive Profil steht oben, danach kommen die übrigen alphabetisch.
   Profile ohne Sessions erscheinen trotzdem (die Liste kommt aus `/api/profiles`).
2. Innerhalb einer Gruppe sind die Sessions nach Zeit sortiert, wie bisher über `_sessionSidebarSortCompare`.
   Es gibt keine Datums-Untergruppen mehr. Pinned Sessions stehen oben in ihrer Profilgruppe.
3. Eine Gruppe zeigt maximal 5 Sessions. Darunter steht "Mehr anzeigen", das die Gruppe vollständig aufklappt
   (der Zustand liegt nur im Speicher und wird nicht persistiert).
4. Ein Klick auf den Gruppen-Header klappt die Gruppe ein bzw. aus. Dafür wird der vorhandene Collapse-Mechanismus
   wiederverwendet, mit dem Schlüssel `profile:<name>` im selben localStorage-Objekt.
5. Das Header-Menü `⋯` enthält:
   - "Neuer Chat in diesem Profil": `switchToProfile(name)`, danach neuer Chat
   - "Zu Profil wechseln": `switchToProfile(name)`
6. Der Button "+ Profil hinzufügen" am Listenende ruft `openProfileCreate()` auf. Nach dem Anlegen
   wird `renderSessionList()` aufgerufen, damit die neue, leere Gruppe sofort erscheint.
7. Das aktive Profil wird im Header markiert (Akzentfarbe oder Punkt).
8. Die bestehenden Filter bleiben und wirken innerhalb der Gruppen:
   Suche, WebUI/CLI-Tabs, Projekt-Chips und Archiv.
   Gruppen ohne Treffer werden beim Filtern ausgeblendet.

### Umsetzung (minimal)
- Profilgruppierung ist der Standard: `?all_profiles=1` wird immer geladen. Der Toggle
  "Show N from other profiles" und der Profilname in `metaBits` entfallen, weil der Header ihn schon zeigt.
- In `renderSessionListFromCache()` wird der Block "Group sessions by date" ersetzt.
  Die Gruppen werden mit derselben Struktur `{label, items, isPinned}` aus `s.profile` gebaut.
  Damit funktionieren die Render-Schleife, die Virtualisierung und `flatSessionRows` unverändert weiter.
  Die Ergänzungen sind das `⋯`-Menü, das 5er-Limit und der Button "+ Profil".
- Das CSS wird von `.session-date-group` wiederverwendet. Neue Klassen gibt es nur für das Header-Menü und den Button.
- Der Datumsmodus wird entfernt und nicht als Option behalten. Bei Bedarf lässt er sich später als Setting nachrüsten.

### Prüfen
- Ein Test unter `tests/`, der prüft, dass die Gruppierung nach `profile` aus einer fixen Session-Liste
  die richtigen Gruppen in der richtigen Reihenfolge liefert, einschließlich leerem Profil und Pinned.
- Manuell: Gruppen aus- und einklappen, Reload (Zustand bleibt), Klick auf eine Session eines fremden Profils
  (Profil wird gewechselt), neues Profil anlegen (leere Gruppe erscheint).

## Teil B: Reasoning/Thinking anzeigen

### Befund
- Das Frontend ist fertig: `_thinkingCardHtml()` (`static/ui.js`) rendert eine einklappbare
  "Thinking"-Karte, die standardmäßig zu ist. Sie ist schaltbar über `/reasoning show|hide`
  (`settings.show_thinking`, das Setting steht bei dir auf `true`).
- Ältere Sessions mit glm-5.3-flash enthalten Reasoning (87 von 158 Assistant-Nachrichten).
  Neue Sessions über das Gateway-Backend (`HERMES_WEBUI_CHAT_BACKEND=gateway`)
  mit claude-opus-5-5 bzw. gpt-6-astra enthalten **0** Reasoning-Felder.
- Der Fehler liegt also beim Transport oder Speichern und nicht in der UI.
  `api/gateway_chat.py` mappt nur `reasoning.available` und `_thinking`-Events vom Gateway (`/v1/runs/{id}/events`).

### Aufgaben
1. **Diagnose:** Einen Run mit Claude und `reasoning_effort: high` direkt gegen das Gateway starten
   (`POST /v1/runs`, dann die Events roh mitschneiden). Prüfen, ob `reasoning.available` ankommt
   und ob es Text enthält.
   - Kein Event → Ursache im Gateway bzw. Agent: Der api_server sendet kein Reasoning, oder der Provider
     liefert keinen Thinking-Text, weil Anthropic/OpenAI das Thinking unterdrücken oder nur zusammengefasst ausgeben.
     Dann prüfen, ob sich ein Thinking-Summary beim Provider-Call aktivieren lässt.
     Falls nicht, ist das ein Provider-Limit und nichts, was die WebUI beheben kann.
   - Event kommt an, aber die WebUI zeigt nichts → in `_gateway_tool_progress_event` / `_gateway_reasoning_delta`
     prüfen, unter welchem Key der Text steht, und den Key ergänzen.
   - Live sichtbar, aber nach einem Reload weg → Reasoning wird am Run-Ende nicht in die
     Assistant-Nachricht geschrieben (`STREAM_REASONING_TEXT` → `message.reasoning`). Das beim Settle persistieren.
2. Das Verhalten der UI bleibt wie es ist: Die Karte ist standardmäßig eingeklappt und klappt per Klick auf.
   Es wird keine neue Einstellung gebaut.

### Akzeptanz
- Ein Chat mit Claude oder GPT über das Gateway zeigt eine eingeklappte "Thinking"-Karte pro Antwort.
- Die Karte ist nach einem Reload noch da.
- `/reasoning hide` blendet alle Karten aus.

## Nicht im Umfang
Drag & Drop von Sessions zwischen Profilen, Profil-Icons und Avatare, Sortierung der Profile per Drag.
