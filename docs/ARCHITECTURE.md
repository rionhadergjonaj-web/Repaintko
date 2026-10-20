# Architektur und Arbeitsstand

Desktop: Python 3.14, PySide6/Qt, Pillow; eingefrorene Windows-EXE mit PyInstaller, vollständiger MSI-Installer und EXE-Bootstrapper. Vorhandene Module für Zeichenflächen, Ebenen, GIF, Video, Browser, Notizen, Text und Datenbanken bleiben erhalten.

Webseite: statisches HTML/CSS/JavaScript, ohne Build-Framework, GitHub Pages. Aktuelles öffentliches Release wird über die GitHub Releases API gelesen. Keine Installer im Git-Repository.

Geplant: signierte Update-Metadaten mit fest eingebautem öffentlichem Vertrauensschlüssel; Hintergrunddownload und separater Installationsprozess. Online-DrawTogether über WSS mit serverseitiger Raumverwaltung; vorhandene SharedDrawing-Transaktionen bleiben gemeinsame Grundlage für LAN und Online.

Noch offen: Implementierung des Updaters, Online-Backend und Client-Integration, vollständige Integrationstests und Freigabe zur Veröffentlichung. Keine produktive Bereitstellung erfolgt.
