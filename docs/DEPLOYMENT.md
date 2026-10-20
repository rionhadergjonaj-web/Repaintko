# Bereitstellung – noch nicht ausgeführt

## Webseite

GitHub Pages veröffentlicht nur die statischen Webdateien: index.html, web/ und version.json. App, Server, Tests und private Dateien dürfen nicht im Pages-Artefakt liegen. Die Webseite liest die veröffentlichte Release-Liste und die von GitHub als aktuell markierte Veröffentlichung. Ohne Release bleibt der Link zur Veröffentlichungsübersicht erhalten.

## Multiplayer

Geeignet sind ein Render-Web-Service mit WebSocket-Unterstützung oder ein eigener Linux-VPS mit TLS-Reverse-Proxy. Render-Dokumentation: https://render.com/docs/websocket . Für einen ersten Betrieb einen dauerhaft laufenden Dienst verwenden; Schlafmodi unterbrechen Sitzungen. Kein Dienst wurde bestellt oder angelegt.

Container aus dem Repository-Stamm bauen: `docker build -f server/Dockerfile -t repaintko-draw .`.
Startprozess: `python -m server.main`. HOST=0.0.0.0, PORT entsprechend Hosting-Plattform. Genau eine Instanz/ein Prozess, solange die Raumverwaltung im Speicher liegt. Nicht horizontal skalieren, ohne gemeinsamen Raumzustand einzuführen.

TLS am Reverse-Proxy, WebSocket-Upgrades zulassen, mindestens 60 Sekunden Idle-Timeout. Ausschließlich WSS öffentlich anbieten. server.repaintko.com erst nach Freigabe auf den bereitgestellten Dienst zeigen lassen. Keine Spieler müssen Ports freigeben. Der Dienst verteilt keine Teilnehmer-IP-Adressen.

Aktuelle Grenzen: 8 Räume, 32 Teilnehmer je Raum, 16 Millionen Ebenenpixel je Raum, 32 MiB je Nachricht. Leere Räume bleiben 10 Minuten für Wiederverbindungen bestehen. Ein Serverneustart verliert derzeit Räume; Produktionsfreigabe erst nach Prüfung von Wiederherstellung, Last und Fehlerfällen. Private Räume erscheinen nicht in der öffentlichen Liste.

## Updates und Releases

EXE-Setup und MSI als GitHub-Release-Assets hochladen. URL-Schema: releases/download/vVERSION/Repaintko-Setup-VERSION.msi. `tools/sign_release.py INSTALLER VERSION` erzeugt signierte version.json. Erst nach erfolgreichem Asset-Upload diese Metadaten veröffentlichen. Die Signatur läuft nach 90 Tagen ab und muss bei unverändertem Release erneuert werden.

Der private Update-Schlüssel liegt ausschließlich in .secrets/update-signing.dpapi, verschlüsselt für den lokalen Windows-Benutzer. Er gehört niemals in Git oder Release-Artefakte. Öffentlicher Vertrauensschlüssel: app/update_trust.py. Eine gesicherte Schlüsselwiederherstellung muss vor dem produktiven Betrieb organisiert werden. Diese Update-Signatur ist keine Windows-Authenticode-Signatur und beseitigt keine SmartScreen-Warnung.

Der separate Updater muss als RepaintkoUpdater.exe gebaut und mit der App ausgeliefert werden. Vor Installation prüft er Signatur und MSI-Hash erneut. MSI übernimmt Installation/Rollback; die App wird bei Erfolg neu gestartet. Dokument-Speicherabfragen laufen vor dem Schließen. Ein echter Installationstest in einer Windows-Testumgebung steht noch aus.

## Freigaben

Vor Push, GitHub Release, Pages-Veröffentlichung, Hostingbestellung oder DNS-Änderung ist die Zustimmung des Eigentümers erforderlich. Bisher wurde nichts davon ausgeführt.
