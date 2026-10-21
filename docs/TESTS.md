# Prüfstand der Plattform-Integration

Stand: 21. Oktober 2026. Keine öffentliche Veröffentlichung und keine Änderung der installierten App.

## Tatsächlich ausgeführt

- Bestehende Suite plus Plattformtests: 66 Tests bestanden (abschließender Lauf: 42,610 Sekunden).
- Echte TCP/TLS-LAN-Verbindungen: Discovery, Passwortschutz, Zertifikat-Pinning, mehrere Ebenen, gleichzeitiges Zeichnen, Wiederverbindung und Undo/Redo.
- Echte lokale WebSocket-Verbindungen: zwei Desktop-Clients, gemeinsame Pixel, Late Join, Wiederverbindung, Sequenz-Deduplizierung, Teilnehmerlimit, Passwortablehnung, Hostberechtigungen, Entfernen eines Teilnehmers und Raumende.
- Lokaler WSS-Server: vertrauenswürdiges Zertifikat akzeptiert, nicht vertrauenswürdiges Zertifikat abgewiesen.
- Online-Pixeltransaktionen auf zwei verschiedenen Ebenen; Undo einer Änderung erhält die Pixel des anderen Teilnehmers.
- Neun Update-Sicherheitstests: Signatur, Manipulation, fremder Schlüssel, Ablauf, Versionsvergleich, Download-Prüfsumme, bestehende Datei bei Fehlversuch erhalten, Abbruch ohne installierbare Teildatei.
- Gebaute RepaintkoUpdater.exe: gültige Signatur, Datei-Hash, MSI-Produktkennung und Version geprüft; manipulierte Metadaten abgewiesen. Dabei wurde kein Installer ausgeführt.
- Vollständiges MSI 13.1.0 entpackt: alle 3238 Dateien anhand SHA-256 geprüft.
- Setup-EXE 13.1.0 im Verify-only-Modus ausgeführt: eingebettetes MSI (1.611.702.272 Bytes) erfolgreich geprüft; kein Installationslauf.
- MSI 13.1.0: Bedingungen für Neuinstallation, Reparatur und Upgrade, verpflichtende Zustimmung zu Nutzungsbedingungen sowie eigener Installations- und Laufzeitordner geprüft; keine Installation ausgeführt.
- Gebaute Repaintko.exe: Starttest erfolgreich, neue DrawTogether-Oberfläche und Update-/Online-Module enthalten, Prüfung bei 800 × 600 Pixeln.
- Webseite im echten Browser betrachtet. JavaScript-Tests für Release-Auswahl, sichere Textanzeige, Offline-Fallback, fehlende Releases und Ablehnung fremder Asset-Adressen bestanden.

## Beobachtete Fehler und Grenzen

Der erste breite Lauf scheiterte an den Zugriffsrechten des temporären Sandbox-Ordners. TEMP/TMP auf den Projekt-Testordner umgestellt. Anschließend fehlte eine mitgelieferte Diagramm-Vorlage; diese ist ergänzt. Ein WSS-Handshake hatte in einem Gesamtlauf einen Timeout; der separate Test und der erneute Gesamtlauf bestanden. Dies wird nicht als Belastungstest gewertet.

Ein weiterer Gesamtlauf hatte einen vorübergehenden Windows-Zugriffsfehler beim atomaren Ersetzen einer temporären Textdatei. Alle acht betroffenen ReTexto-Tests bestanden separat; danach bestanden alle 66 Tests zusammen.

Ein früher Aktualisierungs-Build wurde erfolgreich erstellt, aber der Kopierschritt suchte die EXE im falschen PyInstaller-Ausgabeordner. Der Pfad wurde korrigiert und der anschließende echte EXE-Start bestanden.

## Noch nicht ausgeführt

- Installation, Rollback bei absichtlich fehlschlagender Installation und automatischer Neustart auf einer separaten Windows-Testmaschine/VM.
- Weltweiter Test gegen server.repaintko.com; Hosting und DNS sind nicht eingerichtet.
- Download eines veröffentlichten neuen Release-Assets; im Repository gab es bei der Browserprüfung noch kein öffentliches Setup.
- Container-Build auf Linux, Dauer-/Lasttest und mobile visuelle Browserprüfung.

Der Server hält Räume derzeit im Arbeitsspeicher. Verbindungsabbrüche werden innerhalb derselben Serverlaufzeit aufgefangen; ein Serverneustart stellt Räume nicht wieder her. Dies muss vor einem produktiven Betrieb berücksichtigt werden. Der Dienst ist für eine Instanz vorgesehen.
