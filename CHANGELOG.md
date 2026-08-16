# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden hier dokumentiert.

## [3.1.1] – Kritischer Bugfix: Verbindungen dockten bei individuell platzierten Pins am falschen Punkt an; Pins jetzt rotierbar

1. **Bugfix (kritisch): Leitungen gingen bei Platine/Raspberry Pi nicht
   vom tatsächlichen Anschlusspunkt aus.** Ursache: Jede Seite der
   individuell platzierten Pins (`buildIndividualPinsLayer()` in
   `static/app.js`) saß in einer eigenen `position: absolute`-Zeile. Da
   `computePortRelOffsets()` die Andockposition über
   `dot.offsetLeft`/`dot.offsetTop` relativ zum **nächsten positionierten
   Vorfahren** ermittelt, wurde dabei fälschlich diese Zeile statt des
   Elements selbst als Bezugsrahmen verwendet – der Eigen-Versatz der
   Zeile (z. B. `top:-8px`) ging verloren und Leitungen dockten
   verschoben an, statt exakt am Pin. Behoben, indem jeder Pin-Punkt
   direkt (ohne Zwischen-Ebene) innerhalb der einzigen
   `.individual-pins-layer` positioniert wird – nach exakt derselben
   Formel wie `port_point()` im PDF-Export (`app.py`), wodurch Webansicht
   und PDF jetzt auch hier pixelgenau übereinstimmen (numerisch
   verifiziert, siehe Testabschnitt unten). **Betraf ausschließlich
   Platine und Raspberry Pi** (die einzigen Typen mit individueller
   Pin-Platzierung); alle anderen Elementtypen (gemeinsamer
   Anschluss-Riegel) waren nicht betroffen.
2. **Individuell platzierte Pins (Platine, Raspberry Pi) sind jetzt
   ebenfalls rotierbar.** Neuer „⟳"-Button am Element dreht alle Pins
   gemeinsam um eine Seite weiter (unten → links → oben → rechts,
   dieselbe Reihenfolge wie beim bisherigen Rotieren-Button), statt jede
   Seite einzeln im Bearbeiten-Dialog umstellen zu müssen. Ein Spiegeln-
   Button erscheint bei diesen Typen bewusst nicht (ergibt bei frei
   zuweisbaren Einzelseiten keinen zusätzlichen Nutzen).
3. Getestet: DOM-Strukturprüfung (keine zusätzliche positionierte
   Zwischen-Ebene mehr vorhanden), numerischer Abgleich der berechneten
   Pin-Positionen gegen die unabhängig implementierte Python-Formel
   (`port_point()`, exakte Übereinstimmung der Mittelpunkte), sowie
   End-to-End-Verifikation per PDF-Rendering (Sensorplatine mit 4 Pins
   auf allen 4 Seiten, Verbindung dockt sichtbar exakt am linken Pin an).

## [3.1.0] – PDF-Leitungsführung 1:1 zur Webansicht, Pin/Port-Umbenennung, viele neue Elementtypen, Kabel-Bündel, MQTT

- **PDF-Export folgt jetzt exakt derselben Leitungsführung wie die
  Webansicht.** Bisher wurden im PDF nur die gleichen Punkte gerade
  verbunden; jetzt bildet `build_smooth_path_segments()` in `app.py` die
  Bezier-Kurven-Berechnung aus `buildSmoothPath()` in `static/app.js`
  mathematisch exakt nach (inkl. der Anti-Verknoten-Austrittsrichtung an
  Ports/Pins und der Catmull-Rom-aehnlichen Tangenten an Wegpunkten) –
  numerisch auf viele Nachkommastellen identisch getestet.
- **"Ports" heißen jetzt "Pins"** – außer bei echten Netzwerkgeräten
  (Router, Ethernet Switch sowie Legacy-Netzwerktypen wie Switch/
  Patchfeld), wo es weiterhin "Ports" heißt (`portWord()`/`isNetworkDevice()`
  in `static/app.js`, `port_word()`/`is_network_device()` in `app.py`).
  Betroffen: Beschriftungen im Bearbeiten-Dialog, Tooltips an den
  Anschluss-Punkten, Dreh-/Spiegeln-Buttons, Verbindungsmodus-Statustext,
  Netzliste.
- **Ortsvorschläge**: Das Ortsfeld schlägt jetzt "Schaltschrank 1/2",
  "Maschine A", "Feldebene" sowie bereits im Plan verwendete Standorte vor
  (Datalist) – "Serverraum" (Netzwerkplan-Relikt) wurde entfernt.
- **Kabel-Bündel**: Mehrere Verbindungen lassen sich im
  Verbindungs-Dialog einem gemeinsamen "Kabel" zuordnen (neues Feld
  "Kabel-Bündel", per Dropdown ein bestehendes Kabel waehlen oder ein
  neues anlegen). Verbindungen im selben Kabel werden mit einer
  gemeinsamen, halbtransparenten Kabel-Hülle in Kabelfarbe UND
  Kabel-Namen dargestellt – sowohl in der Webansicht als auch im
  PDF-Export. Neues Top-Level-Feld `config.cables[]`
  (`{id, name, color}`), Verbindungen bekommen ein optionales
  `cable_id`-Feld. Die Netzliste (CSV) hat eine neue Spalte "Kabel".
- **Spannungsversorgung und Batterie** haben jetzt mindestens 2 Pins
  (Default "+"/"-").
- **Relay**: Kontaktart auswählbar (Schließer/Öffner/Wechsler), daraus
  ergibt sich automatisch die passende Pin-Anzahl (4/4/5, davon immer 2
  Spulen-Pins) mit sinnvollen DIN-nahen Standard-Pinnamen
  (11/12/14-Klemmenbezeichnungen). Anzeige-Icon ist jetzt ein kleines
  Schaltplansymbol (Spule + Kontaktanordnung), das sich je nach
  Kontaktart unterscheidet.
- **Motor**: Bauart auswählbar (Gleich-/Wechselstrommotor = 2 Pins,
  bürstenloser Motor/BLDC = 3 Pins "U/V/W", Schrittmotor = 4 Pins
  "A+/A-/B+/B-"), jeweils mit passendem Schaltplan-Icon.
- **Platine**: frei waehlbare Anzahl an Pins, deren Seite (oben/unten/
  links/rechts) sich pro Pin einzeln festlegen laesst (statt eines
  gemeinsamen Portriegels fuer alle Anschluesse auf einer Seite).
- **Raspberry Pi**: kann jetzt optional GPIO-Pins, USB- und LAN-
  Anschlüsse einzeln hinzufügen (gleiches Prinzip wie bei der Platine,
  zusätzlich mit einer Art-Auswahl Pin/USB/LAN je Anschluss). Ohne
  hinzugefügte Anschlüsse verhält sich der Raspberry Pi wie bisher
  (Verbindungen docken am Element-Mittelpunkt an).
- **Neue Elemente**: Ethernet Switch (echtes Netzwerkgerät, 8 Ports),
  Schalter, Taster, Poti – jeweils mit eigenem Schaltplan-Symbol als
  Anzeigebild.
- **MQTT-Versand über Schaltflächen**: Eine verknüpfte Aktion an einem
  Element kann jetzt das Schema `mqtt://` nutzen; im Bearbeiten-Dialog
  erscheinen dann zusätzliche Felder für Topic und Payload. Ein Klick auf
  die Schaltfläche sendet die Nachricht über den neuen Server-Endpunkt
  `POST /api/mqtt/publish` (Paket `paho-mqtt`, neu in `requirements.txt`;
  fehlt es, liefert die Schaltfläche eine verständliche Fehlermeldung
  statt eines Absturzes). Erfolgs- und Fehlerfall gegen einen echten
  Mosquitto-Testbroker verifiziert.
- Neue Standard-`config.json` mit einem Beispiel, das die neuen
  Möglichkeiten zeigt (Relay als Wechsler, Schrittmotor, Platine mit
  individuell platzierten Pins, Raspberry Pi mit USB-/LAN-Anschluss,
  MQTT-Schaltfläche, Kabel-Bündel).
- **Abwärtskompatibilität** durchgehend erhalten und getestet: Elemente
  ohne `relay_type`/`motor_type` (aus v3.0.0) fallen auf die jeweilige
  Standard-Bauart zurück; Konfigurationen ohne `cables`-Feld (aus v3.0.0
  oder älter) funktionieren unveraendert; Legacy-Netzwerktypen (`switch`,
  `patchpanel`, `gateway`, ...) aus der Netzwerkplan-Aera behalten ihre
  Ports samt "Port"-Wortwahl. Kein bestehendes JSON-Feld wurde umbenannt
  oder entfernt.
- Getestet per jsdom (60 Regressionstests: 48 neue Funktionstests + 12
  Abwärtskompatibilitäts-Tests) sowie numerischem Abgleich der
  PDF-Kurvenmathematik gegen die tatsächliche JS-Implementierung
  (identische Kontrollpunkte auf > 10 Nachkommastellen). PDF-Ausgabe
  zusätzlich visuell per Rasterung (PyMuPDF) auf beiden
  Hintergrundvarianten geprüft.

## [3.0.0] – Umstellung von "Netzwerkplan" auf "Verkabelungsplan" + PDF-/Netzlisten-Export

**Achtung: Major-Version-Sprung.** Das Programm ist inhaltlich kein reiner
Netzwerkplan mehr, sondern ein allgemeiner Verkabelungsplan (z. B. für
Schaltschränke, Maschinen- und Antriebsverkabelung). Bestehende
`config.json`-Dateien aus **allen** bisherigen Versionen (inkl. v1.0.0)
laden weiterhin fehlerfrei – siehe "Abwärtskompatibilität" unten.

- **Umbenennung:** Titel, Kopfzeile und Server-Konsolenausgabe heißen jetzt
  "Verkabelungsplan" statt "Netzwerkplan". Die erzeugte Windows-exe /
  macOS-Datei sowie die GitHub-Actions-Artefakte/-Releases heißen ab jetzt
  `Verkabelungsplan` statt `Netzwerkplan`.
- **Neue Elementtypen** (ersetzen die bisherige Netzwerk-Palette):
  Stromversorgung, Batterie, Motor, Antrieb, Platine, Steuergerät,
  Klemmleiste, Delay, Raspberry Pi, Kamera, Router, Relay, Sonstiges.
  Steuergerät, Klemmleiste, Router und Relay haben wie zuvor
  Switch/Router/Patchfeld konfigurierbare Ports; die Klemmleiste hat wie
  zuvor das Patchfeld zwei gegenüberliegende, parallel nummerierte
  Portreihen (Vorder-/Rückseite).
- **PDF-Export** (neuer Button „⭳ Export" in der Werkzeugleiste, in
  Bearbeitungs- **und** Nutzungsmodus verfügbar): Der komplette Plan lässt
  sich als PDF **im Querformat** exportieren, wahlweise mit **schwarzem**
  oder **weißem** Hintergrund. Der Export läuft serverseitig (Python-Paket
  `reportlab`, neu in `requirements.txt`) und funktioniert daher auch
  offline in der gepackten exe. Elemente, Ports, farbige Leitungen
  (inkl. gesetzter Wegpunkte) und Bezeichnungen werden automatisch auf
  eine Querformat-Seite eingepasst.
- **Netzlisten-Export** (CSV, ebenfalls über „⭳ Export"): Tabelle aller
  Verbindungen mit Von/Von-Typ/Von-Ort/Von-Anschluss,
  Nach/Nach-Typ/Nach-Ort/Nach-Anschluss, Farbe, Stärke und Bezeichnung –
  mit `;`-Trennzeichen und BOM, damit Excel Umlaute korrekt anzeigt.
- Beide Exporte senden den **aktuellen** Stand direkt aus dem Browser an
  den Server (auch noch nicht gespeicherte Änderungen sind enthalten) –
  ein vorheriges „Speichern" ist nicht nötig.
- Neue Server-Endpunkte: `POST /api/export/pdf` (Body: `{config, theme}`,
  `theme` = `"dark"`/`"light"`) und `POST /api/export/netlist` (Body:
  `{config}`).
- Neue Standard-`config.json` mit einem Verkabelungsplan-Beispiel
  (Netzteil → Steuergerät → Klemmleiste → Relay → Motor) statt des
  bisherigen Netzwerk-Beispiels.
- **Abwärtskompatibilität:** Die bisherigen Netzwerk-Elementtypen
  (`switch`, `router`, `gateway`, `server`, `pc`, `laptop`, `lan_socket`,
  `patchpanel`, `generic`) sind aus der Auswahl-Palette entfernt, bleiben
  aber als `type`-Wert in bestehenden Elementen unverändert erhalten und
  laden weiterhin fehlerfrei. `switch` und `patchpanel` behalten dabei
  sogar ihre Port-Funktionalität (inkl. Doppelseiten-Ports beim
  Patchfeld); Elemente mit einem nicht mehr in der Palette enthaltenen Typ
  werden mit der generischen „Sonstiges"-Darstellung angezeigt, bis sie im
  Bearbeiten-Dialog auf einen neuen Typ umgestellt werden. Kein bestehendes
  JSON-Feld wurde umbenannt oder entfernt.
- Getestet per jsdom (siehe HANDOVER.md Abschnitt 6): neue Palette,
  Legacy-Typen inkl. ihrer Ports/Doppelseiten, Verbindungen zwischen
  Legacy- und neuen Elementen (Regressionstest für den kritischen
  `buildSmoothPath`-Absturz aus v1.10.1), Sichtbarkeit des
  Export-Buttons im Nutzungsmodus sowie die tatsächlichen Export-Aufrufe
  (PDF/Netzliste) gegen einen gestubbten `fetch`. PDF-Ausgabe zusätzlich
  visuell per Rasterung (PyMuPDF) auf beiden Hintergrundvarianten geprüft.

## [1.11.2] – URL-Feld im Link-Editor tatsächlich breit (CSS-Spezifitäts-Bug behoben)

- **Ursache gefunden:** Die allgemeine Regel `.modal select { width: 100%; }`
  (für Felder wie „Typ") hatte durch die zusätzliche Element-Selektor-
  Komponente eine **höhere CSS-Spezifität** als die schmale
  `.link-edit-scheme`-Klasse für die Protokoll-Auswahl. Dadurch wurde das
  Protokoll-Dropdown (Web/RDP/VNC/SSH) trotz `width: 64px` auf 100%
  aufgeblasen; da es zusätzlich `flex-shrink: 0` hatte, konnte es sich
  nicht wieder verkleinern und quetschte das URL-Feld auf einen winzigen,
  unlesbaren Streifen zusammen – genau das im Screenshot gezeigte
  Verhalten.
- **Fix:** Die Regeln für Bezeichnung, Protokoll-Auswahl und URL sind
  jetzt dreifach verschachtelt qualifiziert
  (`.links-edit-list .link-edit-bottom .link-edit-scheme` usw.) und
  nutzen `flex: 0 0 64px` bzw. `flex: 1 1 auto` als Kurzschreibweise.
  Dadurch gewinnen sie zuverlässig gegen die allgemeine Modal-Feld-Regel,
  unabhängig von deren Position im Stylesheet.
- Mit berechneten CSS-Werten (nicht nur Selektor-Theorie) verifiziert:
  Protokoll-Auswahl bleibt exakt bei 64px (`flex-grow: 0`), das URL-Feld
  wächst (`flex-grow: 1`) und bekommt den verbleibenden Platz in voller
  Breite.
- Rein optische Änderung – keine Änderung am Datenformat.

## [1.11.1] – Link-Editor: Felder gestapelt statt nebeneinander (URL-Feld deutlich breiter)

- **Problem:** Im Link-Editor des Element-Dialogs standen Bezeichnung,
  Protokoll-Auswahl, URL und Entfernen-Button alle in einer Zeile
  nebeneinander. Dadurch blieb für die URL kaum Platz – bei längeren
  Adressen (z. B. `rdp://192.168.1.10:3390`) war im Feld kaum etwas
  lesbar.
- **Lösung:** Jede Webseite/Schaltfläche wird jetzt als kleine, zweizeilige
  Karte dargestellt:
  - **Obere Zeile:** Bezeichnung (volle Breite) + Entfernen-Button.
  - **Untere Zeile:** Protokoll-Auswahl (schmal) + URL (nimmt die
    verbleibende Breite fast vollständig ein).
- Dadurch ist die URL jetzt gut lesbar und bearbeitbar, auch bei
  längeren Adressen mit Port-Angabe.
- Rein optische Änderung – keine Änderung am Datenformat, bestehende
  `config.json`-Dateien funktionieren unverändert weiter.

## [1.11.0] – Wegpunkte bei Gruppen-Verschiebung mitnehmen, Hervorhebung nach Standort

- **Verbindungen bei Gruppen-Verschiebung mitnehmen:** Wird über den
  Auswahlrahmen (Shift + Ziehen) eine Gruppe von Elementen markiert und
  gemeinsam verschoben, werden jetzt auch die **Wegpunkte und die
  Bezeichnungs-Position** aller Verbindungen, deren **beide** Enden
  innerhalb der Auswahl liegen, exakt im gleichen Maß mitverschoben. Die
  Form/Linienführung bleibt dadurch beim Verschieben vollständig
  erhalten, statt zu verzerren. Verbindungen zu Elementen außerhalb der
  Auswahl bleiben unverändert an ihren Wegpunkten hängen (wie bisher).
- **Hervorhebung nach Standort:** Ein Klick auf die Standort-Angabe eines
  Elements hebt jetzt – genau wie bei Leitungen – **alle Elemente mit
  demselben Standort** hervor (leuchtender Rahmen) und dimmt alle
  anderen Elemente ab. Erneuter Klick auf denselben Standort, Klick auf
  leere Fläche, Moduswechsel oder Escape heben die Hervorhebung wieder
  auf. Funktioniert sowohl im Bearbeitungs- als auch im Nutzungsmodus.
- Keine Änderung am Datenformat.

## [1.10.4] – Deutlicherer Hinweis nach RDP-Download (Browser-Grenze, keine App-Einschränkung)

- **Wichtig zu wissen:** Kein Browser erlaubt es einer Webseite, eine
  heruntergeladene Datei selbstständig auszuführen (Sicherheitsgrund –
  sonst könnte jede Webseite beliebige Programme starten). Das betrifft
  **alle** RDP-Web-Lösungen gleichermaßen, auch Microsofts eigenen
  „RD Web Access"/Azure Virtual Desktop: Datei wird heruntergeladen, der
  Nutzer muss sie einmal anklicken, um die Remotedesktopverbindung zu
  starten. Das lässt sich technisch nicht umgehen.
- Damit dieser letzte, notwendige Klick nicht übersehen wird, zeigt die
  App nach dem RDP-Download jetzt eine deutlich sichtbare Einblendung
  (Toast) mit Anleitung, statt nur einer dezenten Meldung in der
  Statuszeile.
- **Tipp für „gefühlt automatisch":** Chrome/Edge zeigen nach dem ersten
  Download unten einen Pfeil neben der Datei – dort „Dateien dieses Typs
  immer öffnen" auswählen. Danach öffnet ein Klick auf den RDP-Button
  die Remotedesktopverbindung ohne weiteren Zwischenschritt.
- Keine Änderung am Datenformat.

## [1.10.3] – RDP-Schaltflächen funktionieren jetzt unter Windows

- **Ursache:** Windows registriert das Protokoll `rdp://` standardmäßig
  **nicht** als eigenständigen URI-Handler (anders als z. B. `mailto:`).
  Ein einfacher Link-Klick auf `rdp://192.168.1.10` führte deshalb zu
  nichts – der Button hat effektiv nichts geöffnet.
- **Lösung:** Ein Klick auf eine RDP-Schaltfläche erzeugt jetzt eine
  echte **`.rdp`-Datei** (Format der Windows-Remotedesktopverbindung) mit
  der hinterlegten Ziel-IP (inkl. optionalem Port, z. B.
  `rdp://192.168.1.10:3390`) und lädt sie herunter. Öffnet man die
  heruntergeladene Datei, startet Windows automatisch die
  Remotedesktopverbindung (`mstsc`) mit bereits eingetragener Zieladresse
  – der letzte Klick auf die heruntergeladene Datei lässt sich technisch
  nicht vermeiden, da Browser aus Sicherheitsgründen keine Dateien
  selbstständig ausführen dürfen.
- Der Button-Tooltip weist jetzt bei RDP-Links darauf hin, dass eine
  Datei heruntergeladen wird.
- VNC- und SSH-Links (`vnc://`, `ssh://`) funktionieren unverändert über
  einen direkten Link-Klick, sofern ein passender Client mit
  Protokoll-Registrierung installiert ist (z. B. RealVNC, MobaXterm).
- Keine Änderung am Datenformat – bestehende RDP-Links in `config.json`
  funktionieren automatisch mit der neuen Öffnungslogik.

## [1.10.2] – GitHub Actions baut jetzt auch eine ausführbare Datei für macOS

- **Kein Code der Anwendung geändert** – reine Build-/CI-Änderung.
- `.github/workflows/build-exe.yml` baut jetzt per Matrix-Strategie
  **parallel** eine Windows-`.exe` (auf `windows-latest`) und eine
  ausführbare Datei für macOS (auf `macos-latest`), jeweils mit korrektem
  Trennzeichen für `--add-data` (`;` unter Windows, `:` unter macOS).
- Beide Builds werden als eigene Artefakte hochgeladen
  (**Netzwerkplan-Windows** / **Netzwerkplan-macOS**).
- Bei einem Tag-Push (`v*`) wartet ein separater Release-Job auf beide
  Builds und hängt **beide** ausführbaren Dateien plus `config.json` und
  `README.md` an ein gemeinsames GitHub Release an (Dateien eindeutig
  benannt: `Netzwerkplan-Windows.exe` / `Netzwerkplan-macOS`, um
  Namenskonflikte beim gleichzeitigen Hochladen zu vermeiden).
- README um einen Hinweis zur macOS-Nutzung ergänzt (Gatekeeper /
  Quarantäne-Flag entfernen, da die Datei unsigniert ist).

## [1.10.1] – Kritischer Bugfix: Verbindungen verschwanden beim Laden bestehender Configs

- **Ursache gefunden und behoben:** Die in v1.10.0 eingeführte
  `buildSmoothPath()`-Funktion griff bei der letzten Kurven-Teilstrecke
  auf einen nicht existierenden Punkt zu (`points[i + 2]`), sobald eine
  Verbindung **keine Wegpunkte** hatte **und** ihre Zielseite **kein
  spezifischer Port** war – also bei praktisch jeder „normalen"
  Verbindung zu einem Server, PC, Laptop, einer Kamera usw. ohne Ports.
  Das führte zu einem Skriptfehler mitten in der Render-Schleife, wodurch
  diese Verbindung **und alle danach verarbeiteten Verbindungen** nicht
  mehr gezeichnet wurden – obwohl sie in der `config.json` weiterhin
  vollständig vorhanden waren (kein Datenverlust, nur ein
  Darstellungsfehler).
- Betroffen waren Konfigurationen aus **allen** älteren Versionen (nicht
  nur v1.9.0), sobald sie mindestens eine Verbindung ohne Wegpunkte zu
  einem portlosen Element enthielten.
- Der Fehler wurde mit einer echten Browser-Umgebungssimulation (jsdom)
  reproduziert und verifiziert behoben: Testkonfigurationen mit
  gemischten Verbindungstypen (mit/ohne Ports, mit/ohne Wegpunkte, altes
  und neues Link-Format) rendern jetzt alle Verbindungen vollständig.
- Keine Änderung am Datenformat – betroffene `config.json`-Dateien müssen
  nicht angepasst werden, es reicht das aktualisierte Programm.

## [1.10.0] – Hervorhebung im Nutzermodus, RDP-Schaltflächen, weiche Kurven, diverse Verbesserungen

**Wichtig: Abwärtskompatibilität.** Alle Änderungen dieser Version wurden
so umgesetzt, dass bestehende `config.json`-Dateien aus **allen**
bisherigen Versionen (auch das ursprüngliche v1.0-Format ohne Ports,
Wegpunkte, Portnamen usw.) unverändert weiter funktionieren. Es wurde kein
bestehendes Feld umbenannt oder entfernt.

- **Leitung im Nutzungsmodus hervorheben:** Ein Klick auf eine Leitung im
  Nutzungsmodus hebt sie jetzt vollständig hervor (Leuchteffekt, dickerer
  Strich), andere Leitungen werden zur besseren Unterscheidung abgedunkelt.
  Erneuter Klick auf dieselbe Leitung, Klick auf leere Fläche oder
  Moduswechsel heben die Hervorhebung wieder auf.
- **Wegpunkte wieder zuverlässig entfernbar:** Jeder Wegpunkt hat jetzt
  zusätzlich zum Ziehen-Griff einen eigenen, immer sichtbaren „✕"-Button
  direkt daneben – zuverlässiger als die bisherige
  Doppelklick-Erkennung, die in bestimmten Situationen ins Leere laufen
  konnte.
- **RDP/VNC/SSH-Schaltflächen:** Schaltflächen an Elementen lassen sich
  jetzt auch für Protokolle wie `rdp://`, `vnc://` oder `ssh://` anlegen
  (z. B. `rdp://192.168.1.10` für eine Remotedesktop-Verbindung). Der
  Link-Editor im Element-Dialog hat dafür eine Protokoll-Schnellauswahl
  (Web/RDP/VNC/SSH). Das Öffnen erfolgt zuverlässiger als zuvor (kein
  Popup-Blocker-Problem bei benutzerdefinierten Protokollen), die
  Schaltfläche zeigt zudem ein passendes Symbol.
- **Breiterer Element-Dialog:** Der Bearbeiten-Dialog für Elemente ist
  jetzt deutlich breiter, damit alle Felder der Webseiten-/Schaltflächen-
  Liste (Bezeichnung, Protokoll, URL, Entfernen) bequem nebeneinander
  Platz haben.
- **Verbindungen überall anklickbar:** Der klickbare Bereich entlang einer
  Leitung wurde nochmals vergrößert – eine Verbindung lässt sich an jeder
  Stelle der Linie anklicken, um den Bearbeiten-Dialog zu öffnen, nicht
  nur über den „✎"-Button.
- **Weiche Kurven durch Wegpunkte:** Manuell gesetzte Wegpunkte erzeugen
  jetzt durchgehend weiche, fließende Kurven (statt gerader Teilstrecken
  mit abgerundeten Ecken) – die Leitung verläuft dadurch deutlich
  natürlicher, während die bisherige Anti-Verknoten-Eigenschaft an Ports
  (senkrechter Austritt) erhalten bleibt.

## [1.9.0] – Patchfeld: Ports auf zwei gegenüberliegenden Seiten (parallel nummeriert/benannt)

- **Neu:** Das Element „Patchfeld" zeigt seine Ports jetzt automatisch auf
  **zwei gegenüberliegenden Seiten** gleichzeitig an (z. B. oben und unten,
  oder links und rechts) – mit **identischer Nummerierung und identischen
  Namen** auf beiden Seiten (Port 5 vorne = Port 5 hinten, gleicher Name).
  Das bildet die typische Vorder-/Rückseite eines physischen Patchfelds ab.
- Verbindungen lassen sich gezielt an der einen **oder** der anderen Seite
  eines Patchfeld-Ports andocken (z. B. interne Verkabelung auf der
  Rückseite, Patchkabel auf der Vorderseite) – beide Andockpunkte sind
  unabhängig voneinander anklickbar.
- Ein Portname wird nur **einmal** gepflegt (per Doppelklick auf einen der
  beiden Punkte oder im Element-Dialog) und gilt automatisch für beide
  Seiten – „parallele Benennung".
- „⟳" (Seite drehen) und „⇋" (spiegeln) wirken weiterhin auf beide Seiten
  gemeinsam, sodass die Nummerierung auf beiden Seiten stets exakt
  parallel bleibt.
- Andere Elementtypen mit Ports (Switch, Router) sind von dieser Änderung
  nicht betroffen und zeigen ihre Ports weiterhin nur auf einer Seite.
- Intern wurde die Portpositions-Logik von einer einzelnen Seite auf ein
  Achsen-/Slot-Modell umgestellt (technische Grundlage für beliebige
  zukünftige Mehrfach-Seiten-Elemente).
- `config.json`: Verbindungen haben jetzt zusätzlich `from_port_side` /
  `to_port_side` (`"a"` = primäre/konfigurierte Seite, `"b"` = die
  gegenüberliegende Seite bei Patchfeldern). Fehlt das Feld, wird `"a"`
  angenommen – bestehende Konfigurationen funktionieren unverändert weiter.

## [1.8.0] – Mehrere benennbare Webseiten-Schaltflächen je Element

- **Neu:** Ein Element kann jetzt mehrere Webseiten hinterlegt bekommen,
  von denen **jede eine eigene, frei benennbare Schaltfläche direkt auf
  dem Element** bekommt (z. B. „↗ Admin-Oberfläche", „↗ Grafana",
  „↗ Doku") – statt eines einzelnen generischen „Webseite"-Buttons mit
  Untermenü.
- Der Element-Dialog (✎) hat dafür eine neue Liste: pro Webseite ein Feld
  für **Bezeichnung** und ein Feld für die **URL**, mit „✕" zum Entfernen
  einzelner Einträge und „+ Webseite hinzufügen" für weitere. Bleibt die
  Bezeichnung leer, zeigt die Schaltfläche „Webseite 1", „Webseite 2" usw.
- Das bisherige Auswahl-Popup für mehrere Links (Nutzungsmodus) entfällt
  dadurch – jede Webseite ist jetzt direkt als eigene Schaltfläche
  sichtbar und mit einem Klick erreichbar.
- `config.json`: `links` je Element ist jetzt eine Liste von
  `{ "label": "...", "url": "..." }`-Objekten statt reiner URL-Strings.
  **Abwärtskompatibel:** Bestehende Konfigurationen mit dem alten Format
  (reine URL-Strings) funktionieren unverändert weiter und werden beim
  nächsten Bearbeiten automatisch in das neue Format überführt.

## [1.7.1] – Kürzerer Button-Text, Portnamen immer sichtbar

- Der Button „↗ Webseite öffnen" an jedem Element heißt jetzt kürzer
  „↗ Webseite".
- Portnamen werden jetzt **immer direkt hinter der Portnummer angezeigt**
  (z. B. „1 Uplink WAN"), statt nur beim Draufzeigen als Tooltip sichtbar
  zu sein. Der Port-Andockpunkt verbreitert sich dafür automatisch; der
  volle Name bleibt zusätzlich als Tooltip verfügbar.

## [1.7.0] – Portnamen, Rahmen-Mehrfachauswahl mit Gruppen-Verschieben

- **Neu – Portnamen:** Einzelne Ports von Switch/Router/Patchfeld können
  jetzt zusätzlich zur Portnummer einen eigenen Namen bekommen (z. B.
  „Uplink WAN", „Server-Rack A"). Zwei Wege dafür:
  - Schnell: Doppelklick direkt auf einen Port öffnet ein kleines
    Eingabefeld an der Klickposition.
  - Vollständig: Der Element-Dialog (✎) zeigt bei Switch/Router/Patchfeld
    jetzt eine scrollbare Liste mit einem Namensfeld je Port, die sich
    automatisch an die eingestellte Portanzahl anpasst.
  - Benannte Ports sind an einer farbigen Unterkante zu erkennen; der volle
    Name erscheint als Tooltip beim Draufzeigen.
- **Neu – Rahmen-Mehrfachauswahl:** Im Bearbeitungsmodus bei gehaltener
  Umschalttaste (Shift) auf leerer Fläche ziehen, um einen Auswahlrahmen
  aufzuziehen. Alle Elemente, die der Rahmen berührt, werden markiert
  (orange Umrandung). Anschließend an einem der markierten Elemente
  ziehen, um **alle markierten Elemente parallel/gemeinsam zu
  verschieben** (Rasterfang gilt weiterhin für jedes Element einzeln).
  Klick auf leere Fläche ohne Shift hebt die Auswahl wieder auf, ebenso
  die Escape-Taste.
- `config.json`: Elemente mit Ports erhalten optional das Feld
  `port_names` (Liste von Zeichenketten, indexgleich zu den Ports).
  Bestehende Konfigurationen ohne dieses Feld funktionieren unverändert
  weiter.

## [1.6.1] – Grundlegender Bugfix: Leitungen/Buttons waren gar nicht klickbar

- **Ursache gefunden und behoben:** Die Element-Ebene (`#elementLayer`)
  lag als vollflächiger, transparenter Layer *über* der gesamten
  Verbindungs-Ebene (SVG) im Canvas. Da diese Ebene keine
  `pointer-events: none` besaß, fing sie **jeden** Mausklick im Canvas ab –
  auch an Stellen ohne sichtbares Element. Dadurch kamen Klicks auf
  Leitungen, den „✎"-Bearbeiten-Button an Verbindungen, Wegpunkte und die
  Bezeichnung nie bei der darunterliegenden SVG-Ebene an. Das erklärt auch
  frühere Probleme mit dem Ändern von Namen und dem (inzwischen entfernten)
  Doppelklick-Verhalten.
- `#elementLayer` hat jetzt `pointer-events: none`, `.net-element`
  (und damit alle Kind-Elemente wie Buttons, Ports, Link-Button) setzt
  `pointer-events: auto` gezielt wieder zurück. Klicks auf leere Stellen
  fallen dadurch korrekt durch zur Verbindungs-Ebene.
- Betrifft alle Interaktionen mit Verbindungen: Leitung anklicken (Dialog),
  „✎"-Button (Kontextmenü), Wegpunkte ziehen/entfernen, Bezeichnung ziehen.
  Auch das Verschieben der Ansicht (Pan) durch Ziehen auf leerer Fläche ist
  davon betroffen und jetzt zuverlässiger.

## [1.6.0] – Zuverlässiger Bearbeiten-Button an Leitungen, IP-Anzeige an Elementen

- **Behoben:** Das Doppelklick-Kontextmenü aus v1.5.0 hat nicht zuverlässig
  funktioniert (Race Condition: Wenn der zweite Klick etwas später als das
  interne Zeitfenster kam, öffnete sich stattdessen bereits der
  vollständige Dialog und "schluckte" den Doppelklick). Die komplette
  Doppelklick-Erkennung an Leitungen wurde entfernt.
- **Neu – fester Bearbeiten-Button je Leitung:** Jede Leitung zeigt jetzt
  im Bearbeitungsmodus einen eigenen „✎"-Button (wie schon an den
  Elementen), der zuverlässig mit einem einzelnen Klick das Menü für Name,
  Farbe, „+ Wegpunkt hier" und „Entfernen" öffnet.
- Ein Klick auf die Leitung selbst öffnet weiterhin sofort (ohne Verzögerung)
  den vollständigen Dialog für Stärke und „Linie zurücksetzen".
- **Neu – IP-Anzeige an Elementen:** Jedes Element zeigt jetzt automatisch
  die aus der ersten hinterlegten Webseite extrahierte IP-Adresse bzw.
  den Hostnamen direkt auf der Karte an (z. B. „IP: 192.168.1.2"), ganz
  ohne den Bearbeiten-Dialog öffnen zu müssen. Funktioniert sowohl mit
  vollständigen URLs (`https://192.168.1.2/admin`) als auch mit reinen
  Host-/IP-Angaben ohne Schema.

## [1.5.0] – Verbindungs-Kontextmenü (Name, Farbe, Entfernen)

- **Behoben:** Die Rechtsklick-Schnellbeschriftung aus v1.4.0 funktionierte
  nicht zuverlässig und wurde vollständig entfernt.
- **Neu – Kontextmenü per Doppelklick:** Ein Doppelklick auf eine Leitung
  (oder auf ihre Bezeichnung) öffnet im Bearbeitungsmodus jetzt ein kleines
  Menü direkt an der Klickposition mit:
  - Textfeld für die **Bezeichnung** (Änderung wird sofort auf der Leitung
    live angezeigt),
  - **Farbauswahl** (Presets + freier Farbwähler),
  - Button **„+ Wegpunkt hier"**, um an dieser Stelle die Linienführung
    anzupassen,
  - Button **„Entfernen"**, um genau diese Leitung einzeln zu löschen
    (mit Sicherheitsabfrage).
- Das Menü schließt sich automatisch (und speichert dabei) bei Klick
  außerhalb, bei Escape oder bei Enter im Namensfeld.
- Der vollständige Verbindungs-Dialog (einfacher Klick auf die Leitung)
  bleibt zusätzlich verfügbar für Leitungsstärke und „Linie zurücksetzen"
  (alle Wegpunkte auf einmal entfernen) und besitzt ebenfalls einen
  „Löschen"-Button.
- Damit sind Leitungen jetzt auf zwei Wegen einzeln entfernbar: schnell
  über das neue Doppelklick-Kontextmenü oder über den vollständigen Dialog.

## [1.4.0] – Verbindungs-Bezeichnungen einfacher anlegen und platzieren

- **Rechtsklick zum Anlegen:** Ein Rechtsklick auf eine Leitung öffnet ein
  kleines Eingabefeld direkt an der Klickposition. Text eingeben, Enter
  drücken – fertig. Die Bezeichnung erscheint sofort genau dort, wo
  geklickt wurde (kein Umweg mehr über den vollständigen Dialog nötig).
- **Frei platzierbar:** Eine gesetzte Bezeichnung lässt sich anschließend
  per Ziehen an eine beliebige Stelle verschieben (auch abseits der
  Leitung, für bessere Lesbarkeit). Ist sie weiter von der Leitung entfernt
  platziert, zeigt eine dünne gestrichelte Führungslinie die Zuordnung.
- **Jederzeit nachbearbeitbar:** Rechtsklick direkt auf eine bestehende
  Bezeichnung öffnet dasselbe Eingabefeld zum Ändern des Texts. Der
  vollständige Verbindungs-Dialog (Klick auf die Leitung) bietet das
  Textfeld weiterhin zusätzlich an.
- Wird der Text geleert, verschwindet die Bezeichnung und ihre freie
  Position wird zurückgesetzt (danach wieder automatisch mittig auf der
  Leitung, sobald erneut ein Text gesetzt wird).
- `config.json`: Jede Verbindung hat jetzt zusätzlich das Feld `label_at`
  (`{x, y}` in Canvas-Koordinaten oder `null` für automatische Position auf
  der Leitungsmitte). Bestehende Konfigurationen ohne dieses Feld
  funktionieren unverändert weiter.

## [1.3.0] – Leitungsführung: weniger Verknoten, manuell anpassbar

- **Richtungsbasiertes Auto-Routing:** Leitungen, die an einem konkreten
  Port (Switch/Router/Patchfeld) beginnen oder enden, verlassen das
  Element jetzt senkrecht zur Portseite (z. B. nach unten, wenn die Ports
  unten liegen), statt immer in eine feste Richtung zu kurven. Dadurch
  laufen deutlich weniger Leitungen quer durchs Element oder durch andere
  Elemente hindurch.
- **Leitungen manuell verlegen:** Ein Doppelklick auf eine Leitung fügt an
  der geklickten Stelle einen frei verschiebbaren Wegpunkt hinzu. Beliebig
  viele Wegpunkte können gesetzt und per Ziehen verschoben werden, um die
  Leitung gezielt um andere Elemente oder Leitungen herumzuführen. Ein
  Doppelklick auf einen Wegpunkt entfernt ihn wieder.
- Die Linienführung wird als sanft abgerundete Kabelverlegung durch die
  Wegpunkte dargestellt (statt einer einzigen Kurve).
- Im Verbindungs-Dialog gibt es jetzt den Button „Linie zurücksetzen“, der
  alle manuell gesetzten Wegpunkte entfernt und zur automatischen
  Linienführung zurückkehrt.
- `config.json`: Jede Verbindung hat jetzt zusätzlich das Feld `waypoints`
  (Liste von `{x, y}`-Punkten in Canvas-Koordinaten, standardmäßig leer =
  automatische Linienführung). Bestehende Konfigurationen ohne dieses Feld
  funktionieren unverändert weiter (automatische Ergänzung beim Laden).

## [1.2.0] – Ports in einer Reihe, dreh-/spiegelbar, freie Leitungsfarben, aufgeräumter Nutzungsmodus

- **Ports in einer Reihe:** Alle Ports eines Switch/Router/Patchfelds liegen
  jetzt gemeinsam auf einer Seite des Elements in einer einzigen Reihe
  (nicht mehr umbrechend), statt in einem Raster verteilt zu sein.
- **Rotierbar:** Über den Button „⟳“ am Element lässt sich die Seite, auf
  der die Ports liegen, im Uhrzeigersinn durch unten → links → oben →
  rechts drehen.
- **Spiegelbar:** Über den Button „⇋“ lässt sich die Reihenfolge der Ports
  innerhalb der Reihe umkehren – beides zusammen erlaubt es, das Element so
  auszurichten, dass Leitungen möglichst kreuzungsfrei und gut lesbar
  verlaufen.
- **Klare Zuordnung Leitung↔Port:** Ein belegter Port färbt sich automatisch
  in der Farbe seiner Verbindung ein, sodass auf einen Blick erkennbar ist,
  welche Leitung an welchem Port hängt.
- **Freie Farbwahl für Leitungen:** Zusätzlich zu den Farb-Presets gibt es
  jetzt einen echten Farbwähler (Color-Picker) – sowohl beim Bearbeiten
  einer bestehenden Verbindung als auch direkt in der Werkzeugleiste beim
  Ziehen neuer Verbindungen.
- **Nutzungsmodus aufgeräumt:** Die Bedienelemente des Bearbeitungsmodus
  (Element-Palette, „Verbindung“-Button, Raster-/Einrasten-Kontrollkästchen,
  „Speichern“-Button, Farbwähler) werden im Nutzungsmodus jetzt vollständig
  ausgeblendet statt nur ausgegraut. Sichtbar bleiben nur der Moduswechsel
  und die Zoom-Steuerung.
- `config.json`: Elemente mit Ports erhalten zusätzlich die Felder
  `port_side` (`"bottom"`/`"top"`/`"left"`/`"right"`, Standard `"bottom"`)
  und `port_mirror` (`true`/`false`, Standard `false`). Bestehende
  Konfigurationen ohne diese Felder funktionieren unverändert weiter.

## [1.1.0] – Port-Andockpunkte für Switch, Patchfeld und Router

- Switches, Patchfelder und Router haben jetzt eine konfigurierbare Anzahl
  einzelner Ports (Standard: Switch = 8, Router = 4, Patchfeld = 24).
- Jeder Port ist ein eigener, nummerierter Andockpunkt am Element. Im
  Verbindungsmodus wird eine Verbindung bei diesen Elementen gezielt an
  einem konkreten Port begonnen bzw. beendet, statt am Element-Mittelpunkt.
- Andere Elementtypen (Server, PC, Laptop, Raspberry Pi, Gateway, LAN-Dose,
  Kamera, Sonstiges) verhalten sich unverändert (Verbindung am Element,
  kein Port erforderlich).
- Die Portanzahl ist im Bearbeiten-Dialog des Elements einstellbar (1–48).
  Wird sie verringert, werden Verbindungen zu nun nicht mehr existierenden
  Ports automatisch auf den Element-Mittelpunkt zurückgesetzt (bleiben
  erhalten, docken aber nicht mehr an einem konkreten Port an).
- `config.json`: Elemente mit Ports erhalten das Feld `ports` (Zahl),
  Verbindungen die Felder `from_port` / `to_port` (Portindex, 0-basiert,
  oder `null` für „kein bestimmter Port“ / Element-Mittelpunkt).
- Bestehende Konfigurationen aus v1.0.0 bleiben kompatibel: Fehlt `ports`
  bei einem Switch/Router/Patchfeld, wird automatisch die Standard-
  Portanzahl des Typs verwendet; fehlende `from_port`/`to_port` werden als
  „kein Port“ behandelt.

## [1.0.0] – Erste Version

- Frei platzierbarer Netzwerkplan mit Zoom/Pan, Raster und Einrasten.
- Elementtypen: Switch, Router, Server, PC, Laptop, Raspberry Pi, Gateway,
  LAN-Dose, Kamera, Patchfeld, Sonstiges – mit Name, Ort und verknüpften
  Webseiten (öffnen in neuem Tab).
- Farbige, unterschiedlich dicke Verbindungslinien zwischen Elementen
  (Bezier-Kurven im Stil von harness.design).
- Bearbeitungsmodus und Nutzungsmodus (nur Links öffnen, keine Änderungen).
- Dark-Theme im Stil von Anduril Lattice.
- Menschenlesbare `config.json` neben der exe (Ansicht, Elemente,
  Verbindungen, Server-Einstellungen).
- GitHub-Actions-Workflow zum automatischen Bauen der Windows-exe per
  PyInstaller (Artefakt bei jedem Push, Release bei `v*`-Tags).
