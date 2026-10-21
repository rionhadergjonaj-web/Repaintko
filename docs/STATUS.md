# Abschlussstand – Repaintko 13.1.0

Stand: 21. Oktober 2026. Lokal vorbereitet; noch keine öffentliche Freigabe.

## Umgesetzt

- Vollständiges Setup 13.0.1 abgeschlossen; zusätzlich vollständige App, MSI und Setup-EXE für die neue Plattformversion 13.1.0 gebaut.
- Responsive Download-Webseite in Dunkelblau/Violett mit Produktübersicht, DrawTogether, Changelog und automatischer Release-Auswahl.
- Hintergrund-Updateprüfung und Download, Ed25519-Signaturprüfung, SHA-256-Prüfung sowie separater MSI-Updater mit Speicherabfragen und Neustartpfad.
- Online-DrawTogether neben LAN: öffentliche und private Räume, Raum-ID, Teilnehmerlimit, Passwortprüfung, Hostverwaltung, Teilnehmerentfernung und Raumende.
- Gemeinsame Ebenen und inkrementelle Zeichentransaktionen, unabhängige Layer-Auswahl, Cursor, Undo/Redo, erneute Synchronisierung nach Verbindungsabbrüchen.
- Begrenzte Nachrichten, Warteschlangen und Verbindungen; TLS/WSS vorgesehen und lokal getestet.
- Container- und Bereitstellungsdateien, öffentlicher Pages-Workflow, signierte Versionsmetadaten und Wiederherstellungsanleitung.

## Wesentliche Dateien

Web: index.html, web/style.css, web/releases.js, web/favicon.svg, .github/workflows/pages.yml.

App: app/update_core.py, app/update_ui.py, app/update_helper.py, app/update_trust.py, app/draw_online.py sowie Anpassungen an draw_network.py, draw_together.py, draw_editor.py und qt_app.py.

Backend: server/main.py, server/rooms.py, server/Dockerfile und server/requirements.txt.

Build/Prüfung: tools/Repaintko.spec, tools/RepaintkoUpdater.spec, tools/Setup.spec, tools/build_msi.py, tools/msi_ui.py, tools/setup_bootstrap.py, tools/sign_release.py, tools/verify_msi.py und tools/test_installer.py. Plattformtests unter app/tests/; Webtests unter tools/test_website.cjs.

## Ergebnisse und Grenzen

66 automatisierte Tests bestanden. Alle 3238 Dateien aus dem tatsächlich eingebetteten MSI-Cabinet stimmen mit ihren SHA-256-Referenzen überein. Native App und separater Updater gestartet und geprüft. MSI-Installationsbedingungen geprüft. Details einschließlich zwischenzeitlicher Fehler stehen in TESTS.md.

Noch nicht nachgewiesen: echte Installation und Rollback/Neustart in einer separaten Windows-Testumgebung, Betrieb über einen öffentlichen Server, Linux-Container-Build und Lasttests. Die App auf diesem PC wurde nicht ersetzt. Signierte Update-Metadaten ersetzen keine Windows-Authenticode-Signierung.

Räume liegen im Arbeitsspeicher einer Serverinstanz. Ein Serverneustart verliert diese Sitzungen. Das Backend ist deshalb noch nicht als ausfallsicherer Produktionsdienst freigegeben.

## Nächste Freigaben und Schritte

1. Setup 13.1.0 auf einer Windows-Testmaschine prüfen; anschließend Update von einer älteren Version einschließlich Abbruch/Fehler und Neustart testen.
2. Zustimmung zum Push des lokalen Entwicklungsbranches und zur Veröffentlichung einholen. Bestehende Benutzeränderung Repaintko.html bleibt separat.
3. Nach Freigabe EXE und MSI als GitHub Release v13.1.0 hochladen. Erst danach version.json und Webseite veröffentlichen; vorher würde der Update-Link auf ein nicht vorhandenes Asset zeigen.
4. Vor produktiven Updates eine sichere Wiederherstellung des privaten Signaturschlüssels organisieren. Schlüssel niemals hochladen.
5. Hosting-Anbieter und Budget freigeben (vorbereitet: Render-Web-Service oder Linux-VPS). Eine dauerhaft laufende Instanz mit TLS/WebSocket-Unterstützung verwenden.
6. Erst nach Zustimmung server.repaintko.com verbinden und WSS einrichten. Keine Router-Portfreigaben bei Teilnehmern nötig.
7. Mit zwei Computern aus verschiedenen Netzwerken den öffentlichen Dienst testen; erst danach den Online-Modus als verfügbar bewerben.

Keine Veröffentlichung, Hosting-Bestellung oder DNS-/Firewall-Änderung wurde vorgenommen.
