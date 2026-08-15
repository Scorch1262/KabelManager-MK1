# Übergabe-Dokument – Netzwerkplan-Projekt

Dieses Dokument ist dafür gedacht, in einem **neuen Chat** hochgeladen bzw.
eingefügt zu werden, damit die Entwicklung nahtlos an diesem Stand
weitergeführt werden kann – als **eigener, alternativer Zweig**, ohne den
ursprünglichen Chat/Entwicklungsstand zu beeinflussen.

Stand bei Übergabe: **Version 1.11.2** (siehe `CHANGELOG.md` für die
vollständige Historie aller Versionen 1.0.0 – 1.11.2).

---

## 1. Was ist das Programm?

Ein lokal laufender Webserver (Flask), der einen interaktiven,
frei platzierbaren **Netzwerkplan** bereitstellt: Switches, Router,
Server, PCs, Laptops, Raspberry Pis, Gateways, LAN-Dosen, Kameras,
Patchfelder usw. lassen sich auf einer Zoom-/Pan-fähigen Fläche
platzieren, benennen, mit Standort versehen, über farbige, frei
routbare Leitungen verbinden und mit klickbaren Schaltflächen zu
Webseiten/RDP/VNC/SSH-Zielen ausstatten. Dark-Theme im Stil von Anduril
Lattice, Verbindungslinien im Stil von harness.design.

Es gibt einen **Bearbeitungsmodus** (alles editierbar) und einen
**Nutzungsmodus** (nur Ansehen + Schaltflächen klicken + Leitungen/Orte
hervorheben, keine Änderungen möglich).

Die Anwendung wird per PyInstaller in eine **Windows-exe** und eine
**macOS-Datei** verpackt; ein GitHub-Actions-Workflow
(`.github/workflows/build-exe.yml`) baut beide automatisch bei jedem
Push bzw. Tag.

## 2. Technologie-Stack

- **Backend:** Python 3 / Flask (`app.py`) – reine REST-API
  (`GET/POST /api/config`) + Ausliefern der SPA. Kein Datenbankzugriff;
  alles wird als **eine JSON-Datei** (`config.json`, neben der exe/dem
  Skript) gespeichert und geladen.
- **Frontend:** Vanilla JavaScript (kein Framework), SVG für die
  Verbindungs-Ebene, absolut positionierte DIVs für die Elemente-Ebene.
  Kein Build-Schritt nötig – `static/app.js` läuft direkt im Browser.
- **Styling:** `static/style.css`, CSS-Variablen für das Farbschema.
- **Packaging:** PyInstaller (`--onefile`), GitHub Actions Matrix-Build
  (Windows + macOS), siehe `.github/workflows/build-exe.yml`.

## 3. Dateistruktur

```
netzwerkplan/
├── app.py                  Flask-Server (Config laden/speichern, IP ermitteln)
├── config.json              Beispiel-/Standardkonfiguration (menschenlesbar)
├── requirements.txt         Flask + PyInstaller
├── VERSION                  Aktuelle Versionsnummer (einzeilig, z. B. "1.11.2")
├── CHANGELOG.md              Vollständige Versionshistorie mit Details
├── README.md                 Nutzer-/Build-Dokumentation
├── .gitignore
├── templates/index.html      HTML-Grundgerüst (Toolbar, Modals)
├── static/style.css          Gesamtes Styling
├── static/app.js             Gesamte Anwendungslogik (~2000 Zeilen)
└── .github/workflows/build-exe.yml   CI: Windows-exe + macOS-Datei bauen
```

## 4. Wichtige Architektur-/Datenmodell-Details

### Element-Objekt (`config.elements[]`)
```jsonc
{
  "id": "el-...",
  "type": "switch" | "router" | "server" | "pc" | "laptop" |
          "raspberry_pi" | "gateway" | "lan_socket" | "camera" |
          "patchpanel" | "generic",
  "name": "...", "location": "...", "x": 0, "y": 0,
  "links": [ { "label": "Admin", "url": "https://..." }, ... ],
  // Nur bei Typen mit Ports (switch/router/patchpanel):
  "ports": 8, "port_side": "bottom"|"top"|"left"|"right",
  "port_mirror": false, "port_names": ["", "Name für Port 2", ...]
}
```
- `links` unterstützt **zwei Formate**: neues Objekt-Format
  `{label, url}` UND das alte reine URL-String-Array – Normalisierung
  über `normalizeLinks()` in `app.js`. **Beim Weiterentwickeln immer
  `normalizeLinks()` benutzen, nie `el.links` direkt als String-Array
  annehmen.**
- Nur `patchpanel` hat **zwei gegenüberliegende Portreihen** (parallele
  Nummerierung/Benennung, `hasDualSides()` in `app.js`). Switch/Router
  haben nur eine Seite.

### Verbindungs-Objekt (`config.connections[]`)
```jsonc
{
  "id": "conn-...", "from": "el-id", "to": "el-id",
  "from_port": null | 0, "from_port_side": "a" | "b",
  "to_port": null | 0, "to_port_side": "a" | "b",
  "color": "#3ad6ff", "thickness": 4, "label": "...",
  "label_at": null | {"x":0,"y":0},
  "waypoints": [ {"x":0,"y":0}, ... ]
}
```
- `from_port`/`to_port` = `null` → Leitung dockt am Element-Mittelpunkt
  an (Elemente ohne Ports).
- `from_port_side`/`to_port_side` = `"a"` (primäre/konfigurierte Seite)
  oder `"b"` (nur bei Patchfeldern relevant – gegenüberliegende Seite).
  Fehlt das Feld (alte Configs), wird `"a"` angenommen.
- `waypoints` = manuell gesetzte, frei verschiebbare Kurvenpunkte.
  Rendering über `buildSmoothPath()` – erzeugt **immer** eine weiche
  Kurve (auch mit Wegpunkten), mit Anti-Verknoten-Verhalten an Ports
  (Leitung tritt senkrecht zur Portseite aus).
- `label_at` = frei platzierte Position der Bezeichnung (sonst
  automatisch auf der Linienmitte).

### Sonstiges
- `config.view` = Zoom/Pan/Raster-Einstellungen.
- `config.mode` = zuletzt aktiver Modus (`edit`/`use`).
- `config.server` = Host/Port des Flask-Servers.

## 5. Wichtige Bugs, die bereits behoben wurden (NICHT wieder einführen!)

1. **`#elementLayer` braucht `pointer-events: none`** (CSS), sonst
   blockiert die vollflächige, transparente Element-Ebene JEDEN Klick
   auf die darunterliegende SVG-Verbindungs-Ebene. `.net-element`
   selbst setzt `pointer-events: auto` gezielt zurück. (Fund: v1.6.1)
2. **`buildSmoothPath()` braucht einen Bounds-Check** für
   `points[i + 2]` in der letzten Kurven-Teilstrecke – sonst stürzt die
   Funktion bei JEDER Verbindung ohne Wegpunkte zu einem Element ohne
   Port ab (z. B. Server, PC, Kamera), was die komplette Render-Schleife
   abbricht und alle nachfolgenden Verbindungen unsichtbar macht.
   (Fund: v1.10.1 – sehr kritischer Bug, unbedingt Regressionstest
   dafür behalten, siehe Abschnitt 6.)
3. **CSS-Spezifität bei Formularfeldern in Modals:** Die allgemeine
   Regel `.modal select, .modal input[type="text"] { width: 100%; }`
   hat durch die Element-Selektor-Komponente eine höhere Spezifität als
   einzelne Klassen wie `.link-edit-scheme`. Neue, schmalere Felder in
   Modals müssen **mehrfach verschachtelt qualifiziert** werden (z. B.
   `.links-edit-list .link-edit-bottom .link-edit-scheme`) und sollten
   `flex: 0 0 <px>` statt losem `width` nutzen, sonst werden sie von der
   allgemeinen Regel überschrieben. (Fund: v1.11.2)
4. **Doppelklick-Erkennung ist unzuverlässig** bei gleichzeitig
   vorhandenem verzögertem Einzelklick-Handler (Race Condition zwischen
   `setTimeout`-Timer und `dblclick`-Event, wenn der zweite Klick später
   als das Zeitfenster kommt). Deshalb wurde die
   Doppelklick-Erkennung an Verbindungslinien komplett durch dedizierte,
   immer sichtbare Buttons ersetzt (✎-Button an Leitungen,
   „✕"-Button an Wegpunkten). **Neue Interaktionen nach Möglichkeit
   über dedizierte Buttons lösen, nicht über Klick-Timing-Heuristiken.**
   (Fund: v1.6.0 → v1.6.1 Root Cause, endgültig gelöst in v1.10.0)

## 6. Test-Methodik (wichtig – kein Browser in diesem Environment!)

In dieser Sandbox steht **kein echter Browser** zur Verfügung
(Puppeteer/Playwright-Chromium-Downloads sind durch die
Netzwerk-Domain-Beschränkung blockiert). Reine API-Tests über den
Flask-Testclient reichen **nicht aus**, um Rendering-Bugs im Frontend
zu finden – das hat mehrfach echte Bugs übersehen (z. B. Bug #2 oben).

**Bewährte Methode:** `jsdom` (Node-Paket) installieren und `app.js` in
einer echten DOM/SVG-Umgebung ausführen:

```bash
npm install jsdom --no-save   # im Verzeichnis /home/claude o.ä.
```

Muster für ein Test-Skript (siehe Chatverlauf für vollständige Beispiele
– wurden jeweils in `/tmp/test_*.js` erzeugt, sind NICHT Teil des
Repos):

1. `templates/index.html` laden und die Jinja-Syntax
   (`{{ url_for(...) }}`) durch statische Pfade ersetzen.
2. `static/app.js` als Text laden und den abschließenden `init();`-Aufruf
   per Regex durch eine Testinitialisierung ersetzen, die `config`
   direkt setzt (keinen `fetch()`-Request macht) und bei Bedarf weitere
   Test-Hooks auf `window` exponiert (z. B.
   `window.__testSetSelection = (ids) => { selectedElementIds = new
   Set(ids); renderElements(); };` – **wichtig:** modul-interne
   `let`-Variablen wie `config`, `mode`, `selectedElementIds` sind
   NICHT automatisch über `window.<name>` erreichbar; dafür müssen
   gezielt Test-Hooks im selben Scope ergänzt werden, die auf die
   Variable zugreifen).
3. Mit `new JSDOM(html, { runScripts: 'outside-only', pretendToBeVisual:
   true })` eine DOM-Umgebung erzeugen, `window.fetch` stubben, das
   gepatchte `app.js` per `dom.window.eval(...)` laden.
4. Testkonfiguration übergeben, rendern lassen, dann mit
   `document.querySelectorAll(...)` und `window.getComputedStyle(...)`
   prüfen, ob die erwartete DOM-Struktur/CSS-Werte tatsächlich
   entstehen (nicht nur, ob kein Fehler geworfen wird!).

Dieser Ansatz hat u. a. den kritischen `buildSmoothPath`-Absturz (Bug
#2) und den CSS-Spezifitätsfehler (Bug #3) zweifelsfrei nachgewiesen
und die Fixes verifiziert – **bei neuen Features/Fixes im Frontend
immer einen solchen Test schreiben, bevor der Fix als erledigt gilt.**

## 7. Standing Instructions (vom Nutzer für dieses Projekt festgelegt)

1. **Bei jeder Codeänderung** die aktuelle Versionsnummer ausgeben
   **und** einen Commit-Text liefern (siehe `VERSION`-Datei; Format:
   Semantic Versioning, `MAJOR.MINOR.PATCH`).
2. **Abwärtskompatibilität ist Pflicht:** Bestehende `config.json`-
   Dateien aus **allen** bisherigen Versionen (auch das ursprüngliche
   v1.0.0-Format ohne Ports/Wegpunkte/Portnamen/etc.) müssen nach jeder
   Änderung weiterhin fehlerfrei laden und speichern. Nie ein
   bestehendes Feld umbenennen oder entfernen – nur neue, optionale
   Felder mit sinnvollem Default-Verhalten bei Abwesenheit ergänzen.
3. Nach jeder Änderung: `VERSION` hochzählen, `CHANGELOG.md` und
   `README.md` (Versionsnummer + ggf. Bedienungshinweise) aktualisieren,
   Projekt neu als ZIP verpacken und über `present_files` bereitstellen.

## 8. Empfohlener Startpunkt für den neuen Chat

Kurzer Prompt-Vorschlag für die erste Nachricht im neuen Chat (Datei
`NEUER_CHAT_PROMPT.txt` liegt bei):

> Ich habe ein bestehendes Projekt "Netzwerkplan" (Flask + Vanilla JS,
> aktuell Version 1.11.2). Das komplette Projekt inkl. HANDOVER.md mit
> allen wichtigen Architektur-/Bug-/Testhinweisen liegt im Anhang.
> Bitte lies HANDOVER.md und CHANGELOG.md, bevor du an neuen Änderungen
> arbeitest, und halte dich an die dort beschriebenen Standing
> Instructions (Versionsnummer+Commit-Text bei jeder Änderung,
> Abwärtskompatibilität von config.json).

## 9. Offene Punkte / mögliche nächste Schritte (Stand Übergabe)

Keine akut offenen Bugs bekannt. Mögliche sinnvolle Weiterentwicklungen,
die im bisherigen Gespräch erwähnt, aber nicht umgesetzt wurden:
- Sortierbarkeit der Link-Liste (welcher Link als „IP-Quelle" für die
  IP-Anzeige am Element zählt, ist aktuell immer der erste Eintrag).
- Ein echter Puppeteer/Playwright-Test wäre wünschenswert, sobald ein
  Environment mit Internetzugriff auf Chromium-Downloads verfügbar ist,
  um die jsdom-Tests (die kein echtes Layout berechnen) durch echte
  Pixel-/Interaktionstests zu ergänzen.
