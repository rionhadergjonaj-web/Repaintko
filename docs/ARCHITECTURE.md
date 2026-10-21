# Architektur und Arbeitsstand

Stand: 21. Oktober 2026, Entwicklungsversion 13.1.0. Keine Veröffentlichung erfolgt.

## Desktop

Python 3.14, PySide6/Qt und Pillow. PyInstaller erzeugt eine Windows-EXE mit gebündelten Laufzeitdateien; der vollständige MSI-Installer wird zusätzlich in einem EXE-Setup ausgeliefert. Vorhandene Zeichen-, Ebenen-, GIF-, Video-, Browser-, Notiz-, Text- und Datenbankmodule bleiben erhalten.

## Webseite

Statisches HTML/CSS/JavaScript ohne Build-Framework, kompatibel mit GitHub Pages. Die GitHub Releases API liefert aktuelle Version, Download und Changelog. Fehlende Releases oder Netzwerkfehler haben einen verständlichen Fallback. Der manuell gestartete Pages-Workflow veröffentlicht ausschließlich die öffentlichen Webdateien.

## Update-System

Die eingefrorene App prüft beim Start im Hintergrund repaintko.com/version.json. Ein eingebauter öffentlicher Ed25519-Schlüssel prüft signierte Metadaten einschließlich Ablauf, Version, Downloadadresse, Dateigröße und SHA-256. Downloads werden erst nach vollständiger Prüfung freigegeben. Ein separater Updater prüft zusätzlich MSI-Produktkennung und Version, wartet auf das Schließen der App und startet Windows Installer. Vorher bleiben die vorhandenen Speicherabfragen aktiv. Offline-Fehler blockieren die App nicht. Die private Signaturdatei liegt außerhalb der Versionsverwaltung und ist mit Windows DPAPI geschützt.

## DrawTogether

LAN bleibt erhalten. Online-Verbindungen verwenden WSS über einen zentralen Python-WebSocket-Dienst. Der Server verwaltet Räume, Passwortprüfungen, Teilnehmer, Berechtigungen und die Reihenfolge von Änderungen. Beide Übertragungswege verwenden die bestehende SharedDrawing-Engine mit stabilen Ebenen-IDs und inkrementellen Pixeltransaktionen. Der aktive Layer bleibt pro Benutzer unabhängig. Cursor, Ebenenmetadaten, Undo/Redo und Wiederverbindung sind integriert. Netzwerk- und Bildverarbeitung laufen außerhalb des UI-Threads; Nachrichten und Warteschlangen sind begrenzt.

## Betriebsgrenzen

Der Server läuft als einzelne Instanz und hält Räume im Speicher. Verbindungsabbrüche werden wieder synchronisiert; nach einem Serverneustart ist eine Sitzung nicht wiederherstellbar. Hosting, DNS, öffentliche Tests und eine echte Update-Installation in einer Windows-Testumgebung stehen aus. Einzelheiten: TESTS.md und DEPLOYMENT.md.
