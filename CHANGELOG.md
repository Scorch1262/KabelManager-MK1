# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden hier dokumentiert.

## [1.1.0] – Anlegen von Verbindungen und Design an den Netzwerkplan angeglichen

- **Klick-basierter Verbindungsmodus (wie im Netzwerkplan):** Statt eines
  reinen Dropdown-Dialogs wird eine Verbindung jetzt genau wie im
  Netzwerkplan-Vorbild angelegt: Button „Verbindung“ aktiviert den
  Verbindungsmodus, danach werden Start- und Zielpunkt (ein bestimmter
  Anschluss oder das Element selbst) direkt im Plan angeklickt. Der
  gewählte Startpunkt wird gruen hervorgehoben; Escape bricht jederzeit
  ab. Erst danach öffnet sich der Dialog zur Wahl von Einzelkabel oder
  Standard-Verkabelung, bereits mit den angeklickten Anschlüssen
  vorbelegt.
- **Eigene „✎“-Bearbeiten-Buttons direkt im Plan:** Jedes Element und jede
  Leitung zeigt jetzt im Bearbeitungsmodus einen eigenen „✎“-Button direkt
  auf der Zeichenfläche (wie im Netzwerkplan) zum sofortigen Öffnen des
  Bearbeiten-Dialogs, ohne den Umweg über die Werkzeugleiste.
- **„⟳“ (Seite drehen) und „⇋“ (spiegeln) direkt am Element:** Elemente mit
  Anschlüssen zeigen jetzt zusätzliche Buttons zum Drehen der
  Anschlussseite (unten → links → oben → rechts) und zum Spiegeln der
  Anschlussreihenfolge, analog zum Netzwerkplan.
- **Weiche Leitungsführung:** Verbindungen, die an einem konkreten
  Anschluss beginnen oder enden, verlassen das Element jetzt senkrecht zur
  Anschlussseite und verlaufen als weiche Kurve zum Ziel (statt einer
  geraden Linie), wie im Netzwerkplan-Vorbild.
- **Design angeglichen:** Abgerundete Elementrahmen, dunkleres
  Canvas-Farbschema, Hover-Cursor über Buttons/Elementen sowie ein
  Status-Hinweistext im Verbindungsmodus, angelehnt an das Erscheinungsbild
  des Netzwerkplan-Programms.
- Keine Änderung am Datenformat der Konfigurationsdateien.

## [1.0.0] – Erste Version

- Lokales Desktop-Programm (Tkinter) zur Planung von Verkabelungen –
  kein Webserver, kein Browser.
- Frei platzierbare Elemente (Steckverbinder, Platine/PCB, Sensor, Aktor,
  Stromversorgung, Verteiler, Sonstiges) mit Name, Typ, Standort und
  frei benennbaren Anschlüssen (Pins) an wählbarer Seite.
- Zoom/Pan, Raster und Einrasten.
- Einzelkabel mit frei wählbarer Farbe, Stärke und Bezeichnung.
- Standard-Verkabelungen (Bündel) als Vorlage: UART, I2C, SPI, LIN, SENT,
  Ethernet (Cat5e/6, T568B), Analog Video (FPV), DJI Air Unit, CAN-Bus,
  PWM – inklusive sinnvoller Vorschlags-Kabelfarben je Ader (z. B. I2C:
  SDA = grün, SCL = gelb).
- Standard-Bündel werden im Normalfall als eine dicke Sammelleitung
  dargestellt; ein Klick klappt alle enthaltenen Adern einzeln in ihrer
  Farbe auf, erneuter Klick klappt wieder zu.
- Kabelfarben-Konfiguration (`kabelfarben_config.json`) neben der exe,
  frei editierbar (im Programm über einen Editor-Dialog oder von Hand).
  Änderungen wirken sich nur auf neu angelegte Kabel des jeweiligen
  Standards aus.
- Gesamtes Verkabelungsnetz wird menschenlesbar in
  `verkabelung_config.json` neben der exe gespeichert.
- PDF-Export des kompletten Plans im Querformat (A4 quer).
- Netzlisten-Export als Excel-Tabelle (Von-Anschluss, Nach-Anschluss,
  Kabelfarbe je Einzelader; Standard-Bündel werden automatisch
  aufgelöst).
- Bearbeitungsmodus und Nutzungsmodus (nur Ansehen/Zoomen/Bündel
  auf-/zuklappen, keine Änderungen).
- GitHub-Actions-Workflow zum automatischen, parallelen Bauen einer
  Windows-`.exe` und einer macOS-Ausführbaren-Datei per PyInstaller
  (Artefakt bei jedem Push, gemeinsames Release bei `v*`-Tags).
