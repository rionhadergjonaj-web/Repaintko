# Repaintko

Windows-Kreativstudio und statische Download-Webseite.

- `app/`: bestehende Desktop-App und neue Online-/Update-Komponenten.
- `server/`: DrawTogether-WebSocket-Backend.
- `web/`, `index.html`: GitHub-Pages-Webseite.
- `tools/`: lokale Release-Signierung und Windows-Build.
- `docs/`: Architektur, Wiederherstellung und Bereitstellung.

## Entwicklung

Python 3.14 verwenden. `python -m venv .venv`, dann Abhängigkeiten in dieser Umgebung installieren. `requirements-platform.txt` enthält die neuen Plattform-Abhängigkeiten. Für die vollständige Desktop-App werden zusätzlich ihre vorhandenen SQL-, PDF-, Video- und KI-Abhängigkeiten benötigt; große Modelle und Laufzeitdateien werden separat bereitgestellt und nicht eingecheckt.

Web-Vorschau: `python -m http.server 8877 --bind 127.0.0.1` im Repository-Stamm.
Backend lokal: `python -m server.main`. Der Standard bindet nur an Loopback. Öffentliche Bereitstellung erfordert einen TLS-Reverse-Proxy, siehe `docs/DEPLOYMENT.md`.
Tests: im Verzeichnis `app` mit `python -m unittest discover -s tests`. Unter eingeschränkten Windows-Umgebungen TEMP und TMP auf einen beschreibbaren Testordner setzen.

## Windows-Build

Zunächst `app/update_helper.py` mit PyInstaller als `dist/RepaintkoUpdater.exe` (onefile, windowed) bauen. Danach `tools/Repaintko.spec` ausführen. `REPAINTKO_ASSET_ROOT` muss auf den vorhandenen vollständigen Laufzeitordner mit models, text_ai_runtime, video_tools und addons zeigen. `REPAINTKO_EXTRA_PATHS` enthält bei Bedarf weitere Python-Paketverzeichnisse, getrennt durch Semikolon.

Installer und Modelle niemals in Git speichern. Installationsdateien gehören nach Freigabe in GitHub Releases. Die Pages-Workflowdatei veröffentlicht ausschließlich die explizit ausgewählten öffentlichen Dateien und muss manuell gestartet werden. Private Update-Schlüssel bleiben unter `.secrets/` und sind von Git und Docker ausgeschlossen.

## Entwicklungsstand

Das vollständige Setup 13.0.1 ist separat fertiggestellt. Die neue Plattform-Integration ist als 13.1.0 in Entwicklung. Noch keine öffentliche Serverbereitstellung, kein Push und kein Release dieser Integration. Die bisher installierte App bleibt unverändert.
