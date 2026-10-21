"""Offline help articles. Catalogs are generated from the actual feature registries."""
from pathlib import Path
import re

def articles():
    pages=[]
    def add(key,group,title,text):pages.append(dict(key=key,group=group,title=title,text=text))
    add('update1200','Updates','12.0.0 · ReDrawko und Wallpaper pro Modus','## Neu in 12.0.0\n\n- **Wallpaper pro Modus:** Add-ons → Wallpaper+ → Einstellungen → „Wallpaper anzeigen in“. Paint und GIF sind getrennt auswählbar, außerdem Notizbuch, ReTexto, Video, ReBrowko, DrawTogether, ReDrawko und Hilfe. Die Auswahl bleibt gespeichert. Standardmäßig bleibt der bisherige Hintergrund in Paint und GIF aktiv. Deckkraft und Plus-Berechtigung gelten in allen ausgewählten Modi. Webseiten, Videobilder und Dokumentinhalte werden nicht verändert; der Wallpaper liegt hinter der Oberfläche.\n- **ReDrawko:** Unter Add-ons offline installieren; danach erscheint Modus → ReDrawko. Eigenständiger nativer Qt-Editor im Repaintko-Design ohne eingebundene Website. Auch ohne Plus verfügbar. Deinstallieren entfernt das Vorlagenpaket, nicht deine gespeicherten Diagramme.\n- **Diagramme:** 33 Formtypen für ERM, UML, Flussdiagramme und Netzwerke; per Ziehen oder Doppelklick einfügen. Verschieben, Größe, Drehung, Farbe, Schrift, Deckkraft, Ausrichten, Verteilen, Gruppieren, Ebenen, mehrere Seiten, Raster und Einrasten. Gesperrte Formen sind gegen Verschieben geschützt.\n- **Verbindungen:** Formen anklicken, gerade/rechtwinklige/gebogene Linien, Pfeile und ERM-Kardinalitäten. Anschlüsse folgen verschobenen Formen. Strg+Doppelklick auf eine Verbindung setzt einen Wegpunkt, der anschließend verschoben werden kann. Text und Beschriftungsposition sind bearbeitbar.\n- **ERM:** Tabellen mit Attributen, Datentypen, PK/FK/UQ-Markierungen und NULL-Angabe. Doppelklick auf die Tabelle öffnet die Attributliste. Sechs Vorlagen: leer, ERM-Bestellsystem, Flussdiagramm, UML, Netzwerk, Mindmap.\n- **Dateien:** .redrawko erhält alle nativen Diagrammdaten. PNG, SVG und PDF exportieren die aktuelle Seite. Rückgängig/Wiederholen, Zwischenablage, Duplizieren, Suchen/Ersetzen von Beschriftungen und lokale Wiederherstellung alle 30 Sekunden.\n\n**Umfang und Austausch:** ReDrawko ist kein vollständiger Nachbau sämtlicher draw.io-Funktionen. draw.io-Import/Export unterstützt grundlegende Formen, Verbindungen und Seiten; spezielle Bibliotheken, freie Verbindungen und komplexe Formatierungen werden nicht vollständig übernommen. Warnungen zeigen übersprungene/ersetzte Elemente beim Import. Für verlustfreies Weiterarbeiten das native .redrawko-Format verwenden. SQL-Import/Export dient einfachen CREATE-TABLE-Grundschemas, erzeugt keine FK-Constraints und führt kein SQL aus. Cloud-Kollaboration, Plugins und sämtliche draw.io-Spezialbibliotheken sind nicht enthalten.\n\n')
    add('update1300','Updates','13.0.0 · ReDataKo, SQL und EXE','# Repaintko 13.0.0\n\n## Installation\nRepaintko-Setup-13.0.0.exe öffnen. Bei vorhandener Installation Aktualisieren wählen. Neue Installationen fragen nach Nutzungsbedingungen und Zielordner. Das Programm startet anschließend über Repaintko.exe bzw. die Verknüpfung. Keine Python-Installation und keine .py-Startdatei erforderlich. Der Ordner _internal enthält Bibliotheken, Modelle und Bilder und gehört zur App. Der Installer enthält intern ein Windows-Installer-Paket und bleibt nicht digital signiert.\n\n## ReDrawko: Anschlüsse und SQL\nBeim Überfahren einer Form erscheinen vier dezente Pfeile. Einen Pfeil ziehen: die Vorschau folgt der Maus. An einem der vier blauen Anschlüsse einer anderen Form loslassen; ein grüner Ring zeigt das Einrasten. Verbindungen behalten die gewählte Seite auch beim Verschieben bei. Oben/unten und links/rechts verwenden passende Richtungen, rechtwinklige Umwege und Kurven. Escape bricht ab. Alt umgeht weiterhin das Raster.\n\nSQL-Import verwendet einen SQL-Parser für SQLite, MySQL und T-SQL-nahe DDL. Er übernimmt Spalten, Primärschlüssel, Defaults, zusammengesetzte Schlüssel, CREATE INDEX sowie FOREIGN KEY in CREATE TABLE oder ALTER TABLE. Erkannte Beziehungen werden verbunden und automatisch angeordnet. Export verwendet diese FK-Zuordnungen. In der Verbindungsbearbeitung lassen sich Quell- und Zielspalten zuordnen. Grafische Linien ohne Zuordnung erzeugen keinen erfundenen Fremdschlüssel. Fehlende referenzierte Tabellen werden gemeldet. Nicht übernommene Script-Anweisungen erscheinen als Importhinweis; der Import führt kein SQL aus. Access-nahe DDL ist kein vollständiger Access-SQL-Dialekt. Komplexe Trigger, Views, proprietäre Syntax und spätere Umbenennungen in CHECK-/Index-Ausdrücken müssen geprüft werden.\n\n## ReDataKo – optionales Plugin\nAdd-ons → ReDataKo → Installieren. Danach Modus → ReDataKo. Deinstallieren entfernt nur die Plugin-Aktivierung; eigene Datenbanken und SQL-Dateien bleiben erhalten.\n\n- SQLite-Dateien erstellen/öffnen; MySQL-Server verbinden und CREATE DATABASE vorbereiten; Access-Dateien erstellen/öffnen.\n- MySQL benötigt einen eigenen Server und Berechtigungen. Access benötigt Microsoft Access Database Engine / ACE mit 64-Bit-ODBC und ADOX. Die Datenbank-Engines von MySQL und Access werden nicht mitinstalliert.\n- Standardmäßig schreibgeschützt verbinden; MySQL verwendet standardmäßig TLS mit Zertifikatsprüfung. Zugangsdaten werden nicht gespeichert.\n- SQL öffnen, bearbeiten, speichern und mit F5 ausführen; eine markierte Auswahl wird separat ausgeführt. Ergebnisse zeigen bis zu 1.000 Zeilen je Anweisung. Der SQL-Editor ersetzt keine Access-Formular-/Berichtsverwaltung.\n- Tabellen ansehen (500 Zeilen pro Seite, Access: erste 500), Zeilen per Formular hinzufügen/bearbeiten/löschen, CSV importieren und geladene Zeilen exportieren. Bearbeiten/Löschen erfordert einen Primärschlüssel und prüft den vorherigen Zeileninhalt auf Konflikte.\n- Commit und Rollback. MySQL-DDL kann implizit committen. Beim Schließen/Verbindungswechsel wird vor dem Verwerfen unbestätigter Änderungen gefragt. Abfragen laufen im Hintergrund; Abbruch hängt vom Treiber ab.\n- Tabellen über einen Assistenten als SQL vorbereiten; Schema exportieren, SQLite-Datei-Backup nach Commit/Rollback, ERD aus dem verbundenen Schema öffnen. Access wird für die Diagrammdarstellung in ein vereinfachtes portables Typenschema übertragen; Schlüssel/Beziehungen bleiben erhalten.\n\n## Lokale KI\nDie bestehende lokale Qwen-KI unterstützt SQL-Entwürfe, Reparatur, Optimierung, Beziehungsvorschläge und Tabellenreihenfolge. Sie arbeitet ohne Cloud mit der Auswahl/dem Script (max. 6.000 Zeichen). Vorschläge werden angezeigt und vor Übernahme geparst; sie werden niemals automatisch auf Datenbanken ausgeführt. Eine syntaktische Prüfung garantiert keine fachliche Richtigkeit. Die geometrische Platzierung erfolgt reproduzierbar anhand des Beziehungsgraphen; die KI kann die Reihenfolge vorschlagen. Es wurde kein eigenes neues Modell trainiert.\n\n## Browserwechsel\nReBrowko → Als Standardbrowser einstellen öffnet nach Registrierung die Windows-Standard-Apps. Dort Repaintko auswählen; die App überschreibt die Windows-Auswahl nicht. HTTP-/HTTPS-Links werden an das bereits laufende Repaintko weitergereicht.\n\nChrome / Edge importieren übernimmt ausgewählte lokale Lesezeichen und Verlauf (bis 100.000 URLs); Lesezeichen-HTML wird ebenfalls unterstützt. Passwörter werden über den offiziellen CSV-Export des alten Browsers übernommen und im Windows-DPAPI-Tresor gespeichert. Vorhandene Passwörter werden nicht ersetzt. Nur HTTPS-Einträge werden unterstützt; übersprungene Einträge werden gezählt. Die CSV enthält Klartext und kann nach erfolgreichem Import entfernt werden. Cookies, Anmeldesitzungen, Erweiterungen und Passkeys werden nicht importiert. Die App liest oder entschlüsselt keine geschützten Chrome-/Edge-Passwortdatenbanken.\n\n## Plus-Designs\nFünf helle Plus-Designs: Perlmutt, Sakura, Gletscher, Salbei und Dünensand. Auswahl unter Ansicht → Design → Plus-Designs. Wallpaper+ unterstützt auch ReDataKo.\n')
    add('home','Start','Willkommen in der Hilfe','''# Repaintko entdecken
Wähle links eine Kategorie oder suche nach einem Wort wie **Deckkraft**, **GIF**, **Plus** oder **Speichern**. Die Suche durchsucht auch die Texte. Mit Zurück/Vor oben wechselst du zwischen gelesenen Artikeln. **Zur Arbeit** bringt dich zu deinem vorherigen Modus zurück.

![Vier Arbeitsbereiche](help:modes)

## Was möchtest du machen?
- [Ein Bild zeichnen und bearbeiten](help:draw)
- [Gemeinsam im LAN zeichnen: DrawTogether](help:together)
- [Dateien öffnen, einfügen und speichern](help:files)
- [Einzelne Bereiche zensieren](help:censor)
- [Eine GIF-Animation erstellen](help:gif)
- [Videos schneiden (Plus)](help:video)
- [Im Internet suchen: ReBrowko](help:browser)
- [Bbc-Zeiterfassung und Saldo berechnen](help:timesheet)
- [Notizen schreiben und behalten](help:notebook)
- [TXT, Markdown und lokale KI: ReTexto](help:retexto)
- [Add-ons und Wallpaper+](help:addons)
- [Repaintko Plus aktivieren](help:plus)
- [Alle Tastenkürzel](help:keys)
- [Update-Logs](help:updates)

Diese Hilfe läuft lokal und benötigt kein Internet. Sie beschreibt den eingebauten Funktionsumfang, einschließlich Grenzen und Besonderheiten.''')
    add('update1180','Updates','11.8.0 · Saldo, DrawTogether und Add-ons','## Neu in 11.8.0\n\n- **Bbc Gleitzeit Saldo:** Der Browserwert wird standardmäßig als Stand seit dem letzten Ausbadgen verstanden. Die laufende Arbeitszeit seit dem offenen Einbadgen zählt zusätzlich. -4:00 um 12:00 bedeutet Ziel 16:00, wenn die mindestens 30 Minuten Pause bereits erfüllt sind. Neu laden verschiebt dieses Ziel nicht. Längere tatsächliche Pausen zählen weiterhin vollständig.\n- **DrawTogether:** Derselbe Paint-Editor wie im Bildmodus, ohne Modus-Auswahl. Alle Pinsel, Füller, Formen, Text, Auswahl, Füllen, Pipette, Zensur, Bildimport, Fotoeffekte, Ebenen, Blattfarbe und Blattdeckkraft sind verfügbar. Plus-Funktionen benötigen weiterhin Plus auf dem jeweiligen PC. Dateiaktionen wirken auf die gemeinsame Zeichnung; Speichern erstellt eine lokale Datei.\n- **Flüssiger zeichnen:** Eigene Striche erscheinen sofort. Kleine geänderte Pixelbereiche werden gebündelt und im Hintergrund komprimiert. Der Host bestätigt die Änderungen in Reihenfolge. Unterschiedliche Bereiche/Ebenen lassen sich gleichzeitig bearbeiten. Bei konkurrierenden Änderungen derselben Pixel oder bei gleichzeitigem Umbau der Ebenen wird nichts blind überschrieben: Der lokale Entwurf bleibt erhalten und kann vor „Neu synchronisieren“ gespeichert werden. Rückgängig/Wiederholen betreffen eigene Aktionen und prüfen ebenfalls auf Konflikte.\n- **Add-on-Übersicht:** Wallpaper+ besitzt eine Karte mit Landschaftssymbol und Plus unten rechts. Je nach Zustand gibt es Installieren oder Deinstallieren; Einstellungen öffnet die Bildgalerie samt Deckkraftregler. Derzeit ist Wallpaper+ das verfügbare Add-on.\n\nAlle DrawTogether-Teilnehmer benötigen 11.8.0 oder eine kompatible neuere Version. Die lokale Sitzung bleibt verschlüsselt und funktioniert ohne Internet. Die bisherige Grenze von 16 Millionen Blattpixeln, 64 Millionen Ebenenpixeln und 32 Ebenen bleibt bestehen.\n\n')
    add('addons','Add-ons','Wallpaper+ installieren und einstellen','## Neu in 11.7.0: Add-ons und Wallpaper+\n\nÖffne oben **Add-ons**. Die Übersicht zeigt Wallpaper+ mit einem Landschaftssymbol und Plus unten rechts. Klicke auf **Installieren**, anschließend auf **Einstellungen** für die Bildauswahl. Installierte Add-ons kannst du mit **Deinstallieren** entfernen. Das Bildpaket gehört zum vollständigen Setup, wird aber erst durch diesen Klick im lokalen Benutzerordner eingerichtet. Es benötigt weder Internet noch Administratorrechte und enthält keinen ausführbaren Erweiterungscode. **Wallpaper+ aktiv** schaltet es ein oder aus. **Deinstallieren** entfernt die installierte Kopie; über Installieren lässt sie sich später wieder hinzufügen. Zeichnungen bleiben erhalten.\n\nDie Sammlung enthält genau **101 neue Wallpaper**: **20 einfarbige Hintergründe für alle**, **40 Anime-/Cartoon-Landschaften für Plus** und **40 fotorealistisch gestaltete Landschaften und ein echtes Oeschinensee-Foto für Plus**. Die 80 ursprünglichen Landschaften wurden mit dem eingebauten Imagegen-Werkzeug erzeugt; sie sind keine Fotos realer Orte. Das zusätzliche Oeschinensee-Panorama ist ein echtes Foto von Bob Tan (CC BY-SA 4.0). Quelle und Lizenz stehen beim Vorschaubild und in assets/WallpaperPlus-Credits.txt. Kategorien und Suche erleichtern die Auswahl. Alle dürfen die Vorschaubilder ansehen, die 81 Plus-Motive lassen sich nur nach der Plus-Aktivierung anwenden. Wähle ein Bild und klicke **Wallpaper anwenden** oder doppelklicke darauf.\n\n**Hintergrund-Deckkraft** regelt die Wallpaper von **0 bis 100 %**. Bei 0 % bleibt dein bisheriges Design sichtbar; bei 100 % ist das Wallpaper vollständig sichtbar. Auswahl, Aktivierung und Deckkraft bleiben nach dem Neustart erhalten. Das Wallpaper füllt den Hintergrund proportional aus; je nach Fensterform werden die Ränder beschnitten. Es wird nur beim Wechsel oder Ändern der Fenstergröße neu skaliert. Die Add-on-Verwaltung bleibt auch aus anderen Modi erreichbar; die Wallpaper selbst dekorieren den Bild-/GIF-Zeichenbereich.\n\nWallpaper liegen hinter dem Blatt und werden **nicht in Bilder oder GIFs exportiert**. Sie verändern weder Ebenen noch Blattdeckkraft. Wenn dein Blatt die ganze Fläche ausfüllt, verkleinere den Zoom, um mehr vom Hintergrund zu sehen. Die Originalauflösung der Landschaften bleibt erhalten; die 20 Farbflächen sind 1920 × 1080 Pixel groß. Die App prüft das Paket vor der Installation auf Vollständigkeit, Dateitypen und Prüfsummen. Abbrechen oder ein beschädigtes Paket lässt eine vorhandene Installation erhalten.\n\n')
    add('saldo1180','Bbc-Zeiterfassung','Saldo seit letztem Ausbadgen','Die Standard-Grundlage für Gleitzeit Saldo ist jetzt „Saldo seit letztem Ausbadgen“. Ein offener Arbeitsblock wird seit seiner Startzeit zusätzlich angerechnet; wiederholtes Neuladen verschiebt die Zielzeit nicht. Beispiel: -04:00 Saldo, Einbadgen 12:00, mindestens 30 Minuten Pause bereits erledigt → Ziel 16:00. Fehlen 30 Minuten Pause, wird 16:30 angezeigt. Nach einem neuen Ausbadgen enthält der neue Browser-Saldo den abgeschlossenen Block; er wird nicht doppelt gezählt. 8:12 und Saldo 0 bleiben getrennt auswählbar.')
    add('timesheet','Bbc-Zeiterfassung','Anmelden, Gehzeit und Saldo','## Neu in 11.6.0: Bbc-Zeiterfassung\n\nUnter **Ansicht → Saldo berechnen** die offizielle Bbc-Anmeldeseite öffnen und selbst anmelden. Anschließend den heutigen Tag in der Zeiterfassung wählen. Die Anzeige steht rechts neben Spotify; über das Uhrsymbol öffnest du Anmeldung und Einstellungen erneut. Die bestehende ReBrowko-Anmeldesitzung wird verwendet. Eine Anmeldung in Chrome oder Codex wird nicht übertragen.\n\nWähle **8:12 Stunden**, **Saldo 0** oder **beide Ziele**. Für das Tagesziel werden die heutigen Beginn-/Ende-Buchungen addiert. Mindestens **30 Minuten Pause insgesamt** sind eingeplant. Längere gebuchte Pausen zählen vollständig; fehlt Pause, wird die fehlende Zeit zusätzlich eingeplant. Weitere spätere Pausen verschieben die Gehzeit. Im ausge\xadbuchten Zustand erscheint die noch nötige Arbeitszeit statt einer angenommenen Rückkehrzeit.\n\nFür Saldo 0 wählst du **Gleitzeit Saldo**, **Gleitzeit aktuell** oder einen eigenen Übertrag. Zusätzlich musst du festlegen, ob der gewählte Saldo **vor heute** gilt oder **die Arbeit bis zum Laden der Seite bereits enthält**. Die Website bezeichnet „Gleitzeit aktuell“ als Prognose; Repaintko kann daraus allein nicht sicher ableiten, ob heutige offene Buchungen schon enthalten sind. Bei unbekannter Bedeutung bleibt das Null-Ziel offen. Kläre die Bedeutung gegebenenfalls mit der zuständigen Zeiterfassung. Bei Übertrag vor heute lautet die Rechnung: Tagesziel minus Übertrag minus heutige Arbeitszeit. Bei aktuellem Saldo wird nur das verbleibende Minus ausgeglichen. Fehlende Mindestpause kommt jeweils dazu.\n\nDie Seite wird im Hintergrund ungefähr jede Minute neu geladen, solange keine Formularänderungen oder Fehlzeiten erkannt werden. Sichtbare Formulare werden nicht automatisch neu geladen. Nach drei Minuten ohne neue Seitenladung werden Zeiten als veraltet behandelt. Bei anderem Datum, Fehlzeiten, unklaren/überlappenden Buchungen oder geänderten Feldern wird nicht geraten. Tagesziel ist fest 8:12; Sondertage bitte direkt im Extranet prüfen. Repaintko verändert oder übermittelt keine Buchungen und reicht keinen Monat ein. Saldo und Buchungswerte werden nur im Arbeitsspeicher gehalten. Einstellungen und die vom Browser gespeicherte Anmeldesitzung bleiben lokal erhalten. Abschalten über denselben Menüpunkt stoppt die Aktualisierung.\n\n')
    add('retexto','ReTexto','Textdateien, Markdown und KI','''# ReTexto
Öffne **Modus → ReTexto · Texteditor**. Das Bild bleibt erhalten. ReTexto arbeitet mit normalen Textdateien; das interne **Notizbuch** ist ein separater Modus.

## Dateien und Tabs
Datei → Neu / Öffnen / Speichern / Speichern unter / Alle speichern. Dateien können aus dem Explorer hineingezogen werden. Das × schließt einen Tab; ungespeicherte Änderungen verlangen eine Entscheidung. Beim Moduswechsel bleiben Tabs erhalten. Nach Programmende werden Tabs nicht wiederhergestellt: wichtige Texte speichern.

## Bearbeiten und Ansicht
Bearbeiten bietet Rückgängig, Wiederholen, Zwischenablage, Alles auswählen, Suchen, Ersetzen, Alle ersetzen, Vorwärts-/Rückwärtssuche mit Umlauf, ganze Wörter und Groß-/Kleinschreibung, Gehe zu Zeile und Datum/Uhrzeit (F5). Ansicht bietet Zeilenumbruch, Schrift, Zoom und Markdown-Vorschau. Datei bietet Seitenlayout und Drucken. Unten stehen Zeile/Spalte/Zeichenzahl sowie wählbare Kodierung und Zeilenumbrüche. UTF-8 ist für neue Texte empfohlen. Maximal 64 MB pro Datei. Externe Änderungen werden vor dem Überschreiben gemeldet.

## Markdown
Ansicht → Markdown-Vorschau zeigt den Text formatiert daneben. Das Markdown-Menü fügt Markierungen für Fett, Kursiv, Überschriften, Listen, Code und Links ein. Speichere als .md. Bilder und Links werden in der Vorschau nicht aus dem Internet geladen/geöffnet.

## Rechtschreibung
Extras → Rechtschreibung prüfen → Sprache → Text prüfen. Wähle eine Fundstelle und einen Vorschlag oder schreibe eine eigene Korrektur. Übernehmen korrigiert nur diese Stelle und prüft erneut. Verwendet Windows-Wörterbücher; fehlende Sprache in den Windows-Spracheinstellungen installieren. Bis 200.000 Zeichen und 500 Fundstellen pro Prüfung.

## Lokale KI
Extras → Lokale KI-Texthilfe: Umschreiben, Zusammenfassen, Rechtschreibung/Grammatik verbessern oder Text verfassen. Markiere vorher einen Ausschnitt, sonst wird der gesamte Text verwendet. Maximal 6.000 Zeichen Text und 2.000 Zeichen Auftrag. Bei Text verfassen wird nur dein Auftrag verwendet. Die mitgelieferte KI läuft auf deinem PC; Texte werden nicht hochgeladen. Berechnung ist abbrechbar. Prüfe den Vorschlag, bearbeite ihn bei Bedarf und wähle Ersetzen oder Einfügen. Strg+Z macht die Übernahme rückgängig. Die kleine lokale KI kann Fehler machen, Details auslassen und lange Antworten abschneiden (640 Tokens). Keine Cloud-KI oder automatische Textänderung.

## Kürzel
Strg+N/O/S: Neu/Öffnen/Speichern; Strg+Umschalt+S: Speichern unter; Strg+W: Tab schließen; Strg+P: Drucken; Strg+F/H: Suchen/Ersetzen; F3/Umschalt+F3: nächste/vorige Fundstelle; Strg+G: Zeile; F5: Datum/Uhrzeit; Strg++/−/0: Zoom. Die üblichen Zwischenablage- und Rückgängig-Kürzel gelten ebenfalls.''')
    add('together','DrawTogether','Gemeinsam zeichnen im LAN','''# DrawTogether
Öffne **Datei → DrawTogether**. Trage deinen Benutzernamen ein. Das eigene Bild bleibt beim Wechsel erhalten.

![Drei Benutzer, gemeinsame Ebenen](help:together)

## Server hosten
Wähle **Server hosten**, einen Namen und optional ein Passwort. Leer bedeutet: Jeder im erreichbaren LAN kann beitreten. Du kannst eine Kopie deines Bildes mit Ebenen verwenden oder ein neues Blatt anlegen. Der Server läuft auf deinem PC; Repaintko muss geöffnet bleiben. **Server schließen** beendet die Sitzung für alle.

## Beitreten
Die Liste sucht automatisch alle vier Sekunden im gleichen LAN/WLAN. Server auswählen → **Server beitreten**. Nur geschützte Server fragen nach einem Passwort. Keine IP-Eingabe und kein Internet nötig. Beide Geräte brauchen eine passende Windows-Firewall-Freigabe für Repaintko bzw. dessen Python-Laufzeit im privaten Netzwerk. Gast-WLAN und Client-Isolation können die Verbindung blockieren. Pro PC ist ein Host auf dem Discovery-Port 45873 möglich.

## Gemeinsam zeichnen
Hier steht derselbe Editor wie im normalen Bildmodus bereit, ohne Modus-Auswahl: alle Pinsel, Füller, Formen, Text, Füllen, Auswahl, Pipette, Zensur, Fotoeffekte, Bildimport und Ebenenwerkzeuge. Eigene Striche erscheinen sofort; Änderungen werden im Hintergrund gebündelt übertragen. Alle sehen denselben bestätigten Bildstand. Die Benutzer stehen unter der Zeichenfläche. Über Ebenen öffnest du das normale Ebenenfenster. Klicke deine Ebene an: Nur deine aktive Auswahl ändert sich. + erstellt, − löscht nach Rückfrage, ↑/↓ sortiert, Doppelklick oder Umbenennen ändert den Namen. Häkchen und Ebenendeckkraft gelten für alle. Auf ausgeblendeten oder inzwischen gelöschten Ebenen werden Striche abgewiesen; der Hinweis erscheint unten. Zoomen per Prozentfeld oder Strg+Mausrad; Einpassen passt das Blatt ins Fenster.

## Unterbrechungen
Während einer Unterbrechung pausiert Zeichnen. Repaintko verbindet sich automatisch neu, lädt den aktuellen Stand und überträgt unbestätigte Aktionen erneut, ohne sie doppelt anzuwenden. Das funktioniert, solange derselbe Host läuft. Nach einem Host-Neustart erneut über die Liste beitreten. Bei Sitzungsende bleibt dein letzter empfangener Stand zum Speichern verfügbar.

## Speichern und verlassen
**Zeichnung speichern** oder Strg+S: als PNG oder als .repaintko mit Ebenen. Speichern sichert deinen aktuellen lokalen Entwurf; warte auf die Synchronisierung, wenn auch die neuesten Änderungen aller Teilnehmer enthalten sein sollen. Jede Person kann eine eigene Kopie speichern. Vor Verlassen oder Schließen gibt es eine Rückfrage; mit Abbrechen kannst du vorher speichern. Über **Bild / GIF** wechselst du zu deinem eigenen Dokument, während die Sitzung weiterläuft. **Modus → DrawTogether** bringt dich zurück. Ohne Speichern wird beim Programmende keine Sitzung dauerhaft aufbewahrt.

## Grenzen
Maximal 32 Teilnehmer inklusive Host, 32 Ebenen, 16 Millionen Pixel pro Blatt und 64 Millionen Ebenenpixel insgesamt. Fotoeffekte samt ihrer Grundlage werden mitgenommen. Rückgängig/Wiederholen bearbeiten eigene Aktionen. Bei Änderungen derselben Pixel oder gleichzeitigem Ebenenumbau kann ein Konflikt entstehen: Der lokale Entwurf bleibt erhalten; speichere ihn bei Bedarf und wähle Neu synchronisieren. Alle Teilnehmer benötigen Version 11.8.0 oder eine kompatible neuere Version. Verbindung und Passwortprüfung sind verschlüsselt; die erste automatische Suche ist für vertrauenswürdige LANs vorgesehen.''')
    add('draw','Bild & Zeichnen','Zeichenfläche und Werkzeuge','''# Zeichnen und bearbeiten
1. Datei → Neu öffnet ein neues Blatt. Wähle Breite und Höhe oder eine Auflösungsvorlage.
2. Wähle links ein Werkzeugsymbol. Der Name erscheint beim Darüberfahren. Oben gibt es zusätzlich eine Werkzeugliste.
3. Unter Optionen stellst du Strichstärke, Stift-Deckkraft und Farben ein.
4. Zeichne mit gedrückter linker Maustaste. Rechts benutzt du Farbe 2.

![Werkzeugübersicht](help:tools)

## Alle Werkzeuge
| Werkzeug | Verwendung |
|---|---|
| Pinsel | Durchgehender runder Strich. |
| Füller | Schräge breite Feder. Die Strichrichtung erzeugt dünne oder breite Linien. |
| Bleistift | Präziser Strich; auch hier ist die Größe einstellbar. |
| Airbrush | Versprüht kleine Farbpunkte. Mehrfaches Malen verdichtet die Farbe. |
| Radierer | Entfernt Deckkraft auf der aktiven Ebene. Fotoeffekte bleiben erhalten. |
| Zensur | Verändert nur übermalte Bereiche; siehe Zensur-Katalog. |
| Füllen | Füllt zusammenhängende Pixel gleicher Farbe auf der aktiven Ebene. |
| Pipette | Übernimmt die sichtbare Farbe an der angeklickten Stelle. |
| Linie | Ziehe vom Start zum Endpunkt. |
| Rechteck / Rundrechteck / Ellipse / Dreieck | Aufziehen; Formstil bestimmt Kontur und Füllung. |
| Polygon | Eckpunkte anklicken, Enter schließt ab, Esc verwirft. |
| Text | Schrift wählen, aufs Blatt klicken und Text eingeben. |
| Auswahl | Rechteck aufziehen; innerhalb einer Auswahl ziehen, um Inhalt zu verschieben. |
| Lupe | Links vergrößern, rechts verkleinern. |

## Strich und Form
Strichstärke: 1–100 Pixel. Stift-Deckkraft: 0–100 %. Jeder Zeichenpinsel merkt sich seine Größe. Alle Zensurarten teilen die separate Zensurgröße. Ein einzelner halbtransparenter Strich verdunkelt sich an seinen Überlappungen nicht fortlaufend; neue Striche können sich überlagern.

Formstil: Nur Kontur, Kontur + Füllung oder Nur Füllung. Halte beim Ziehen einer Form die Umschalttaste für gleiche Breite/Höhe beziehungsweise eine diagonale Linie. Text verwendet die gewählte Windows-Schrift, 6–300 Pixel und optional Fett. Text wird als Bildpixel eingefügt, nicht als später editierbares Textfeld.

Eine ausgeblendete Ebene kann nicht bemalt werden. Blende sie im Ebenenbereich wieder ein.''')
    add('colors','Bild & Zeichnen','Farben, Blatt und Transparenz','''# Farben und drei Arten von Deckkraft
![Deckkraft erklärt](help:alpha)

- **Farbe 1**: linke Maustaste. **Farbe 2**: rechte Maustaste und Formfüllung. Farben tauschen vertauscht beide.
- Klicke eine Farbe an: Farbfläche und Farbtonregler auswählen oder RGB-Werte von 0 bis 255 bzw. einen Hex-Farbwert eingeben. Die kleinen Farbfelder sind Schnellfarben.
- **Stift-Deckkraft** beeinflusst neu gemalte Striche.
- **Ebenen-Deckkraft** blendet den gesamten Inhalt einer Ebene stärker oder schwächer ein.
- **Blattdeckkraft** betrifft nur den Hintergrund unter allen Ebenen.

Bild → Blattfarbe ändern oder Optionen → Blattfarbe ändern öffnet den Farbwähler. Optionen → Blattdeckkraft stellt 0–100 % ein. Das Schachbrett bedeutet Transparenz, es wird nicht als Muster exportiert.

Weiße Flächen in einem Foto sind Bildpixel und werden durch transparente Blattfarbe nicht entfernt. Dafür Radierer oder Plus → Transparent entfernen verwenden.

Für Transparenz PNG, WebP oder TIFF wählen. Datei → Mit transparentem Blatthintergrund speichern entfernt beim Export die Blattfarbe. JPEG und PDF erhalten einen weißen Untergrund. Ebenenprojekte behalten die Blatteinstellungen.''')
    add('selection','Bild & Zeichnen','Auswahl, Formen und Bildgröße','''# Bereiche bearbeiten
Mit Auswahl ein Rechteck ziehen. Innerhalb des Rechtecks ziehen verschiebt den Inhalt der aktiven Ebene. Strg+A wählt alles aus. Strg+C kopiert die Auswahl beziehungsweise das sichtbare Bild; Strg+X schneidet aus, Entf löscht die Auswahl. Strg+V öffnet die Platzierung als neue Ebene.

Bild → Zuschneiden beschränkt das Dokument auf die Auswahl. Bild → Größe ändern skaliert die Bildinhalte. Bild → Leinwandgröße ändert die Blattabmessungen. Breite/Höhe sind in Pixeln; Vorlagen sind Full HD, QHD, 4K und 8K. Es gilt die Grenze von 64 Millionen Leinwandpixeln.

Bild enthält außerdem 90° rechts, 90° links, Horizontal spiegeln, Vertikal spiegeln, Farben umkehren, Graustufen und Aktive Ebene leeren. Prüfe zuvor die aktive Ebene. Mit Strg+Z kannst du Änderungen zurücknehmen.

## Ansicht ohne Veränderung der Datei
Strg+Mausrad zoomt. Mittlere Maustaste gedrückt halten und ziehen verschiebt die Ansicht. Unten stehen Minus, Plus und Einpassen. Ansicht → 100 % zeigt die tatsächliche Pixelgröße. Pixelraster wird ab 800 % sichtbar, wenn aktiviert. Zoom verändert keine exportierten Pixel.''')
    add('layers','Bild & Zeichnen','Ebenen und Rückgängig','''# Ebenen verstehen
![Ebenen übereinander](help:layers)

Öffne Ebenen in der Werkzeugleiste. Oben in der Liste liegt vorne im Bild. Klicke eine Zeile, um die aktive Ebene zu wählen. Das Häkchen steuert die Sichtbarkeit. Die Deckkraft reicht von 0 bis 100 %.

| Taste | Wirkung |
|---|---|
| Neu | Leere Ebene ergänzen. |
| Duplizieren | Kopie der aktiven Ebene. |
| Nach oben / unten | Reihenfolge und damit Überdeckung ändern. |
| Umbenennen | Verständlichen Namen vergeben. |
| Löschen | Aktive Ebene entfernen. |
| Nach unten vereinen | Mit der darunterliegenden Ebene zusammenführen. |

Bis zu 32 Ebenen und insgesamt 128 Millionen Ebenenpixel. Große Bilder verbrauchen dieses Budget schneller. Speichere als **.repaintko**, um Ebenen und Effekte weiterbearbeiten zu können. PNG/JPG und andere Bildexporte enthalten das sichtbare Gesamtergebnis.

Strg+Z nimmt Änderungen zurück, Strg+Y wiederholt sie. Das Speicherbudget für Bildverlauf beträgt 480 MB nach der internen Größenberechnung; die Anzahl ist von der Auflösung abhängig. Im GIF-Modus hat jeder Frame seinen eigenen Bildverlauf. Der Video-Editor besitzt separat bis zu 100 Rückgängig-Schritte.''')
    add('files','Dateien','Öffnen, Einfügen, Drag-and-drop','''# Bilder ins Programm holen
**Datei → Öffnen** ersetzt das aktuelle Dokument nach einer eventuellen Speicherabfrage. Unterstützt werden PNG, JPG/JPEG, BMP, WebP, TIFF, GIF, PDF und Repaintko-Projekte. Bilder werden in Originalauflösung eingelesen; Einpassen verkleinert nur die Anzeige. Eine GIF-Datei öffnet im Bildmodus ihr erstes Bild.

**Datei → Bild einfügen**, Strg+V und gezogene Bilder werden auf einer neuen Ebene platziert. In der Vorschau das Bild ziehen oder X/Y eingeben, dann Platzieren. Abbrechen/Esc lässt das Dokument unverändert. Die Leinwand kann innerhalb der Grenzen nach rechts/unten wachsen.

Beim Einfügen externer Bilder wird, falls möglich, auf vierfache Gesamtpixelzahl vergrößert (doppelte Breite und Höhe), sonst auf zweifache Pixelzahl, sonst Originalgröße. Das erfindet keine echten Details. Öffnen und die interne Zwischenablage behalten die Originalauflösung.

Bilder aus Explorer oder Browser ins Zeichenfenster ziehen. Unterstützt sind direkte Bilddaten, Bildadressen, HTML-Bildverweise und eingebettete Bilder. Ein Bild pro Vorgang. Internetbilder: maximal 40 MB und 64 Millionen Pixel; Laden ist abbrechbar. Falls eine Webseite nur einen Link oder geschützte Inhalte liefert: dort Bild kopieren und in Repaintko Strg+V. Anmeldedaten des Browsers werden nicht übernommen.

Gezogene Projekte/PDFs werden geöffnet statt als normale Bilder platziert. Quellen werden weder verschoben noch gelöscht.''')
    add('save','Dateien','Speichern, Kopie, Projekte und PDF','''# Das richtige Format wählen
| Möglichkeit | Zweck |
|---|---|
| Speichern · Strg+S | Aktuelles Bild speichern; im GIF-Modus GIF exportieren. Im Video-Modus bedeutet diese Taste Teilen! |
| Speichern unter · Strg+Umschalt+S | Neuen Namen/Dateityp wählen. Im Video-Modus Schnittprojekt speichern. |
| Als Kopie speichern · Strg+Alt+S | Separate Datei, ohne den aktuellen Dateipfad zu wechseln. |
| Projekt mit Ebenen speichern | .repaintko behält Ebenen, Effekte und Blatteinstellungen. Alte .repainko-Projekte bleiben lesbar. |
| PNG / WebP / TIFF | Bild mit möglicher Transparenz. |
| JPG | Fotoformat ohne Transparenz. |
| Druckdatei (PDF) | Sichtbares Bild als PDF ausgeben. |

Bei mehreren Ebenen ersetzt der Bildexport kein editierbares Projekt. Das Sternchen im Fenstertitel zeigt ungespeicherte Änderungen. Beim Schließen auf die Speicherabfrage achten.

## PDF öffnen
Datei → Öffnen, PDF wählen, gewünschte Seite und Auflösung auswählen. Nur diese Seite wird als Bild importiert, keine editierbaren PDF-Texte. Das PDF bleibt unverändert. Höhere Auflösung benötigt mehr Speicher.

## Andere Modi
GIF speichern exportiert alle Frames. Es gibt kein editierbares GIF-Projektformat. Videoschnitt als .repaintvideo speichern; die Quelldateien zusätzlich aufbewahren. MP4 ist der fertige Film, kein Schnittprojekt.''')
    add('effects','Effekte & Zensur','Fotoeffekte anwenden','''# Fotoeffekte
Wähle eine sichtbare Ebene und öffne Fotoeffekte. Links einen Effekt anklicken, Stärke einstellen, Vorschau prüfen und Übernehmen wählen. Standardstärke setzt den Regler auf den Vorgabewert. Abbrechen verwirft die Änderung.

Vor dem Öffnen kannst du eine Auswahl markieren. Im Dialog wählst du Ganzes Bild oder Auswahl; die Wirkung bleibt auf diesen Bereich begrenzt.

Original anzeigen hilft beim Vergleich. Die Detailansicht zeigt einen Ausschnitt in 1:1. Die verkleinerte Vorschau dient der Geschwindigkeit; Übernehmen berechnet die volle Bildauflösung.

Unterschiedliche Effekte lassen sich kombinieren. Derselbe Fotoeffekt wird aktualisiert, nicht immer wieder auf sich selbst gerechnet. Effekte gehören zur aktiven Ebene. Radieren lässt die Effekte bestehen.

Die folgenden Einträge zeigen die tatsächlichen Effektbeschreibungen und Reglerbereiche:''')
    from effects import EFFECTS
    pages[-1]['text']+='\n\n'+'\n\n'.join(f'### {e.group} · {e.title}\n{e.description}\n\nStärke: {e.minimum} bis {e.maximum} {e.unit}; Standard: {e.default} {e.unit}.' for e in EFFECTS.values() if e.group!='Zensur')
    add('censor','Effekte & Zensur','Zensurpinsel und alle Blur-Arten','''# Einzelne Bereiche zensieren
1. Werkzeug Zensur oder Effekte → Zensurpinsel wählen.
2. In Optionen Modus, Größe (8–400 Pixel) und Stärke (2–80) einstellen.
3. Nur die zu verändernden Bereiche mit gedrückter Maustaste übermalen. Der Kreis zeigt den Pinselbereich.
4. Ergebnis vergrößert prüfen. Strg+Z nimmt den Strich zurück.

Alle Zensurarten teilen die Pinselgröße. Schwarze Balken sind nicht enthalten. Höhere Stärke und große Bilder benötigen mehr Rechenzeit. Künstlerische Verzerrungen garantieren keine sichere Anonymisierung; kontrolliere das sichtbare Ergebnis vor dem Teilen.

## Arten''')
    from censor import CENSOR_MODES
    descriptions=['Quadratische Pixelblöcke.','Mosaikartige grobe Farbflächen.','Weiche verschwommene Details.','Dreht und zieht den Bereich spiralförmig.','Lange schnelle horizontale Streifen.','Feine horizontale Wischlinien.','Malerische verwischte Farbflecken.','Vertikale Wischbewegung.','Diagonale Bewegung nach rechts.','Diagonale Bewegung nach links.','Kombinierte kreuzförmige Wischrichtungen.','Mehrere strahlenförmige Richtungen.','Gleichmäßig gemittelter Bereich.','Weichzeichnung mit dreieckiger Gewichtung.','Rund wirkende Linsenweichzeichnung.','Nach außen verlaufende Zoombewegung.','Drehende Verwischung.','Unregelmäßige Streuung wie Frostglas.','Wellenförmige Verzerrung.','Wasserartige Verformung.','Tunnelartiger Zoom-Eindruck.','Horizontal versetztes Doppelbild.','Vertikal versetztes Doppelbild.','Sanftes, weiches Bild.','Helle verschwommene Überlagerung.','Dunkle verschwommene Überlagerung.','Diffus wie durch Milchglas.']
    pages[-1]['text']+='\n\n'+'\n\n'.join(f'### {n}\n{d}' for n,d in zip(CENSOR_MODES,descriptions))
    add('ai','Repaintko Plus','Objekte lokal entfernen','''# KI entfernen (Plus)
Nach der Aktivierung Effekte → KI entfernen (Plus) öffnen. Bearbeitet wird die aktive sichtbare Ebene.

![Entfernen in drei Schritten](help:ai)

1. Objekt oder Person vollständig rot übermalen. Schatten bei Bedarf einschließen. Rechtsklick entfernt Markierungen. Pinselgröße: 3–200. Markierung löschen beginnt neu.
2. **Hintergrund ergänzen (lokale KI)** oder **Transparent entfernen** auswählen.
3. Vorschau berechnen, mit Original zum Vergleichen prüfen.
4. Als neue Ebene übernehmen: Original bleibt ausgeblendet erhalten. Abbrechen verändert nichts. Strg+Z macht die Übernahme rückgängig.

Die KI wird mitgeliefert und läuft lokal auf der CPU. Der erste Aufruf lädt das Modell. Große entfernte Bereiche können sichtbare Fehler oder erfundene Details enthalten. Das Objekt wird mit dem Pinsel markiert, nicht automatisch erkannt. Die KI berechnet einen 512 × 512 großen Ausschnitt um die Markierung; die Gesamtauflösung bleibt erhalten.

Transparent entfernen löscht Deckkraft innerhalb der Markierung. Darunterliegende Ebenen können sichtbar werden. PNG/WebP/TIFF mit transparentem Blatt verwenden, wenn das Loch exportiert werden soll. Für das Ergebnis muss Platz für eine zusätzliche Ebene frei sein.''')
    add('plus','Repaintko Plus','Plus aktivieren und erkennen','''# Repaintko Plus aktivieren
![Aktivierung](help:plus)

1. Zur Bildbearbeitung zurückkehren.
2. **Datei → Repaintko Plus aktivieren …** wählen.
3. Deinen erhaltenen Access-Key eingeben und bestätigen. Achte auf die vollständige Schreibweise.
4. Bei erfolgreicher Prüfung wird das Logo blau und bekommt ein Pluszeichen. Plus-Designs, lokale Objektentfernung und Video-Editor werden freigeschaltet.

Die Aktivierung wird für das aktuelle Windows-Benutzerkonto gespeichert und bleibt bei Updates erhalten. Sie erfolgt lokal, ohne Konto/Server. Diese Hilfe zeigt keinen Aktivierungsschlüssel an.

## Desktop-Symbol
Datei → Desktop-Symbol aktualisieren aktualisiert die vorhandene Verknüpfung. Beim öffentlichen Desktop kann Windows Administratorrechte verlangen. Beim normalen Programmstart soll keine erneute Abfrage erscheinen. Wird keine Verknüpfung gefunden, kann der Installer sie reparieren.

## Was braucht kein Plus?
Normale Bildbearbeitung, GIF-Editor, ReBrowko und Standard-Designs. Die normalen Funktionen bleiben nach Aktivierung verfügbar.''')
    add('gif','Modi','GIF-Editor: Frames und Animation','''# GIF-Editor
Modus → GIF-Editor aktivieren. Das aktuelle Bild wird als erster Frame kopiert; das normale Bild bleibt separat erhalten. Ein Klick auf einen Frame lädt ihn in die Zeichenfläche. Pinsel, Ebenen und Effekte funktionieren pro Frame.

![Frames und Zwiebelschicht](help:gif)

| Bedienung | Ergebnis |
|---|---|
| + Frame | Neues leeres Bild mit transparenter Blattdeckkraft. |
| Duplizieren | Kopie inklusive Blatteinstellungen. |
| Bilder als Frames | Dateien proportional in gemeinsame Framegröße einpassen. |
| Löschen | Gewählten Frame entfernen. |
| Pfeile links/rechts | Frame-Reihenfolge ändern. |
| FPS | 1–50 Bilder pro Sekunde. Mehr FPS bedeutet schnellere Wiedergabe. |
| Zwiebel-Symbol | Vorherigen Frame mit 26 % Deckkraft hinterlegen. Nur Zeichenhilfe. |
| Vorschau | Animation in Schleife abspielen. |
| GIF speichern / Strg+S | Alle Frames als GIF exportieren. |

Vorschau: Minus/Plus, Prozentfeld, 100 %, Einpassen und Strg+Mausrad. Zoom bleibt beim Framewechsel erhalten. Beim ersten Frame gibt es keine vorherige Zwiebelschicht. Sie wird weder exportiert noch in der Wiedergabe gezeigt.

Maximal 200 Frames und 128 Millionen Ebenenpixel. Alle Frames haben dieselbe Größe. GIF hat höchstens 256 Farben pro Frame und nur vollständig transparente oder deckende Pixel; Halbtransparenz wird bei 50 % getrennt. Zeiten werden auf 10 ms gerundet. Kein editierbares Animationsprojekt und kein Import einer bestehenden GIF-Animation als Framefolge. Beim Verlassen auf die Speicherabfrage achten.''')
    add('video','Modi','Video-Editor: Clips, Schnitt und Export','''# Video-Editor (Plus)
Modus → Video-Editor (Plus) ersetzt die Arbeitsfläche im selben Fenster. ← Bild / GIF kehrt zurück; der Schnitt bleibt während der Sitzung erhalten.

![Videoschnitt](help:video)

1. Clips hinzufügen: bis zu 100 Videos. Reihenfolge mit Clip nach links/rechts ändern.
2. In der Zeitleiste die gewünschte Stelle anklicken. **Strg+S teilt am Abspielkopf**, auch wenn zuvor ein anderer Clip gewählt war.
3. Im Reiter Clip In/Out in Sekunden der Quelldatei setzen. Clip-Einstellungen anwenden bestätigt. Duplizieren, Entfernen und Umsortieren verändern keine Quelldatei.
4. Geschwindigkeit 0,25×–4×, Lautstärke 0–200 %, Stummschalten pro Clip einstellen.
5. Wiedergabe berechnet eine Vorschau mit Bearbeitungen und Ton. Vorher zeigt das Verschieben des Abspielkopfs die Quelle. −/+ 1 Frame hilft beim Positionieren.
6. Projekt speichern als .repaintvideo. MP4 exportieren erstellt den fertigen Film.

## Ausgabe und Projekt
HD 1280 × 720, Full HD 1920 × 1080, 4K 3840 × 2160 oder Hochkant 1080 × 1920. FPS: 24, 25, 30, 50 oder 60. MP4 verwendet H.264 und AAC. Die Vorschau ist 640 × 360 bei höchstens 30 FPS und verändert die Exportauflösung nicht.

Vorschau/Export können abgebrochen werden. Lange Filme und 4K benötigen Rechenzeit und temporären Speicher. Das Schnittprojekt enthält Verweise auf Quellen, nicht die Videos. Beim Umziehen Projekt und Quellen gemeinsam kopieren. Fehlende Quellen werden gemeldet.

Eine sequenzielle Videospur mit Originalton. Zusätzliche Musikspuren, frei überlagerte Videos und Texttitel sind nicht enthalten. Bis zu 100 Rückgängig-Schritte. [Effekte, Keyframes und Übergänge](help:video-fx).''')
    add('video-fx','Modi','Videoeffekte, Keyframes und Übergänge','''# Video gestalten
## Effekte
Clip wählen → Effekte. Von/Bis sind Zeiten innerhalb dieses Clips nach der Geschwindigkeitseinstellung. Effekt hinzufügen fügt den Zeitbereich hinzu. Gewählten Effekt entfernen löscht ihn. Violette Markierungen zeigen Effektbereiche.

## Keyframes
Eigenschaft wählen, Zeit vom Abspielkopf übernehmen oder eingeben, Wert setzen, Keyframe setzen / ersetzen. Ein Punkt zur gleichen Zeit ersetzt den Wert; zwischen Punkten wird linear interpoliert. Gelbe Markierungen zeigen Punkte. Gewählten Keyframe entfernen löscht einen Eintrag.

- Zoom: 1×–4×.
- Position X/Y: 0–1, verschiebt bei Zoom über 1 den sichtbaren Ausschnitt.
- Helligkeit: −0,8 bis +0,8.
- Lautstärke: 0–2, zusätzlich zur Clip-Lautstärke.

Beim Teilen bleiben die Zeitbereiche und interpolierten Werte erhalten.

## Übergänge
Linken Clip wählen → Übergang → Typ und Dauer → Übergang anwenden. Keine bedeutet normaler Schnitt. Höchstens die halbe Länge beider beteiligter Clips; die Überlappung verkürzt die Gesamtlänge. Ton wird mit überblendet. Am letzten Clip ist kein Übergang möglich. Grüne Balken zeigen die Überlappung.
''')
    from video_engine import EFFECTS as VE,TRANSITIONS
    pages[-1]['text']+='\n## Alle Videoeffekte\n'+', '.join(VE)+'.\n\n## Alle Übergänge\n'+', '.join(TRANSITIONS)+'.'
    add('notebook','Modi','Notizbuch: interne Notizen',"""# Dein Repaintko-Notizbuch
Modus → Notizbuch öffnet deine Notizen im selben Fenster. Kein Plus und kein Internet erforderlich.

- **+ Neue Notiz** legt einen Eintrag an. Maximal 100 Notizen insgesamt.
- Oben den Titel bearbeiten, darunter beliebig mehrzeiligen Text schreiben. Texte sind einfache Notizen ohne Bildanhänge.
- Die Suche links durchsucht Titel und Inhalt. Klicke einen Eintrag zum Öffnen.
- Änderungen werden nach einer kurzen Schreibpause automatisch gespeichert. Der Status unten zeigt, ob das Speichern erfolgreich war. Speichern versucht es sofort.
- Löschen entfernt die gewählte Notiz erst nach Bestätigung dauerhaft.
- Neu laden liest den zuletzt gespeicherten Text ein; ungespeicherte Änderungen werden nur nach Bestätigung verworfen.
- ← Bild / GIF kehrt zur Bearbeitung zurück. Hilfe → Zur Arbeit führt wieder ins Notizbuch.

Die Notizen bleiben beim Neustart und bei Updates erhalten. Sie liegen intern im lokalen Repaintko-Benutzerdatenordner, unter Notizbuch/notizen.sqlite3, nicht als einzeln exportierte Dokumente. Es gibt keine Exportfunktion und keine Cloud-Synchronisierung. Die Daten werden also weiterhin lokal auf deinem PC gespeichert, nicht im Internet. Sie sind keine verschlüsselte Passwortablage; dafür den ReBrowko-Passwortmanager verwenden.

Bei 100 Notizen zuerst eine löschen. Wenn Speichern fehlschlägt, bleibt der Text im Editor; Wechsel und Schließen werden verhindert. Bei Änderungen in einem zweiten Repaintko-Fenster wird ein Konflikt gemeldet. Kopiere deinen noch ungespeicherten Text zur Sicherheit, bevor du Neu laden verwendest.
""")
    add('browser','Modi','ReBrowko: Google und Internet','''# ReBrowko
Modus → ReBrowko · Internet. Der Browser öffnet im vorhandenen Fenster und benötigt kein Plus. Zeichnung und Schnitt bleiben erhalten.

- Suchwörter ins obere Feld schreiben und Enter oder Suchen drücken: Google-Suche.
- Webadresse eingeben, z. B. https://www.google.com/.
- Links-/Rechtspfeil: zurück bzw. vor im Seitenverlauf.
- Google: Startseite öffnen.
- Neu laden: Seite aktualisieren und Internet erneut prüfen.
- ← Bild / GIF: zurück zur Bearbeitung.

Ohne erreichbares Internet oder wenn Google nicht erreichbar ist, erscheint ein Hinweis. Die Suche bleibt gesperrt. Die Verbindung wird regelmäßig geprüft, solange der Modus sichtbar ist.

## Tabs, Verlauf und Anmeldungen (ab 11.2.0)
+ Tab öffnet eine neue Seite. Das X schließt einen Tab; Tabs lassen sich durch Ziehen umsortieren. Links mit neuem Fenster öffnen als Tab. Bis zu 30 Tabs. Strg+T: neu, Strg+W: schließen, Strg+L: Adressleiste, Strg+Tab / Strg+Umschalt+Tab: wechseln.

Verlauf oder Strg+H zeigt bis zu 2000 besuchte Seiten samt Google-Suchen. Suchen, einen Eintrag doppelklicken oder Öffnen wählen. Verlauf löschen entfernt die Einträge.

Die Internetprüfung beginnt bereits beim Start von Repaintko und wird alle 30 Sekunden wiederholt. Der Browsermodus muss dafür nicht geöffnet sein. Webseiten werden erst beim Öffnen des Modus geladen.

Cookies und Website-Speicher bleiben für dein Windows-Benutzerkonto erhalten. So können Anmeldungen Neustarts überstehen; Webseiten können trotzdem eine neue Anmeldung verlangen. Cookies löschen meldet dich bei vielen Webseiten ab. Tabs werden beim Neustart nicht wiederhergestellt.

## Passwortmanager
Auf einer HTTPS-Seite das Loginformular ausfüllen und vor dem Absenden **Login speichern** anklicken. Benutzername und Passwort prüfen oder manuell eingeben, dann Speichern bestätigen. Es gibt keine automatische Aufnahme aller Tastatureingaben. **Login ausfüllen** wählt einen gespeicherten Benutzer und setzt die Werte ausschließlich auf derselben HTTPS-Webseite einschließlich Port ein. Die Anmeldung musst du selbst bestätigen. Bei mehrstufigen Formularen den Vorgang auf der nächsten Stufe wiederholen. Fremde eingebettete Formulare werden nicht ausgelesen.

**Passwörter** zeigt gespeicherte Webseiten/Benutzernamen und erlaubt das Löschen eines Eintrags. Passwörter werden mit Windows-DPAPI für dein Windows-Benutzerkonto verschlüsselt. Bei Verschlüsselungsfehlern wird nicht im Klartext gespeichert. Keine Cloud-Synchronisierung und kein Import anderer Browser. Verlauf, Cookies und gespeicherte Passwörter werden getrennt gelöscht.

Downloads sind aktuell nicht verfügbar. Manche Webseiten oder Anmeldungen können eingebettete Browser ablehnen. Suchanfragen und Webseitenaufrufe gehen an Google beziehungsweise die jeweilige Webseite. ReBrowko ist kein Google-Produkt.

**Bekannter Prüfstand:** Der Browser-Start brach in der Entwicklungs-Testumgebung ab. Die tatsächliche Darstellung von Google-Ergebnissen konnte dort nicht bestätigt werden. Falls Repaintko beim Öffnen von ReBrowko beendet wird, vorerst einen externen Browser verwenden und den Fehler melden.''')
    add('appearance','Oberfläche','Designs, Panels und Spotify','''# Oberfläche anpassen
Ansicht → Design enthält Standard- und Plus-Designs. Die Wahl bleibt gespeichert und verändert nur die Oberfläche, niemals Bildpixel. Ohne gültige Plus-Aktivierung werden Plus-Designs gesperrt. Verlauf und Sternpunkte sind Dekoration des Arbeitsbereichs.

Auf kleinen Bildschirmen können Seitenleisten eingeklappt sein. Optionen, Werkzeuge und Ebenen in der Werkzeugleiste oder Ansicht blenden sie wieder ein. Das Programm unterstützt Fenster ab 640 × 440 Pixel. Zoom/Einpassen nutzen, statt das Bild selbst zu verkleinern.

## Spotify
Wenn die Spotify-Desktop-App eine Mediensitzung an Windows meldet, erscheint der Block mit Titel/Interpret, Spielzeit, Dauer und Fortschritt. Vorheriger Titel, Wiedergabe/Pause und Nächster Titel steuern Spotify. Spotify entscheidet, ob Zurück zum Liedanfang springt und welche Wechsel erlaubt sind. Während eines Befehls sind Tasten kurz gesperrt; Fehler stehen im Tooltip.

Ohne erkannte Sitzung bleibt der Block verborgen. Der Webplayer wird nicht erkannt. Keine separate Kontoverknüpfung nötig. Voraussetzung ist eine verfügbare Windows-Medienschnittstelle. Keine Zeitangabe wird erfunden, wenn Spotify sie nicht meldet.''')
    from qt_app import THEMES,PLUS_DESIGNS
    pages[-1]['text']+='\n\n## Alle Designs\n'+ '\n'.join(f'- {v[0]}'+(' · Plus' if k in PLUS_DESIGNS else '') for k,v in THEMES.items())
    add('keys','Nachschlagen','Tastenkürzel und Maussteuerung','''# Tastenkürzel nach Modus
| Kürzel | Bild / GIF | Video |
|---|---|---|
| Strg+N | Neues Bild | – |
| Strg+O | Öffnen | Projekt öffnen über Schaltfläche |
| Strg+S | Bild speichern / GIF exportieren | Clip am Abspielkopf teilen |
| Strg+Umschalt+S | Speichern unter | Schnittprojekt speichern |
| Strg+Alt+S | Als Kopie speichern | – |
| Strg+Z / Strg+Y | Rückgängig / Wiederholen | Rückgängig / Wiederholen |
| Strg+C / Strg+X / Strg+V | Kopieren / Ausschneiden / Einfügen | – |
| Strg+A / Entf | Alles auswählen / Auswahl löschen | – |
| Strg+I | – | Clips hinzufügen |
| Strg+E | – | MP4 exportieren |
| Leertaste | – | Wiedergabe / Pause |
| F1 | Hilfe öffnen | Hilfe öffnen |

## Maus und weitere Tasten
Links zeichnen mit Farbe 1, rechts mit Farbe 2. Mittlere Maustaste zieht die Ansicht. Strg+Mausrad zoomt. Lupe: links größer/rechts kleiner. Umschalt beim Formenzeichnen begrenzt die Seitenverhältnisse. Polygon: Enter abschließen, Esc verwerfen. In der KI-Markierung entfernt Rechtsklick Markierungen. In ReBrowko startet Enter im Adressfeld die Suche. In der Hilfe durchsucht das Suchfeld alle Artikel.''')
    add('troubles','Nachschlagen','Probleme und Grenzen','''# Wenn etwas nicht wie erwartet funktioniert
| Problem | Prüfen |
|---|---|
| Zeichnen geht nicht | Aktive Ebene sichtbar? Stift-/Ebenen-Deckkraft über 0? Richtiges Werkzeug? |
| Transparenz wird weiß | PNG/WebP/TIFF verwenden; Blattdeckkraft und Exportoption prüfen. Weiß im Foto ist echter Inhalt. |
| Bild wirkt klein oder unscharf | Ansicht → 100 %. Einpassen verkleinert nur die Anzeige. Hochskalieren erzeugt keine neuen Details. |
| Seitenteile fehlen | Optionen/Werkzeuge/Ebenen wieder einblenden. |
| Effekt wirkt aufs falsche Bild | Aktive Ebene prüfen. Fotoeffekte und Videoeffekte sind getrennte Systeme. |
| Datei zu groß | 64 Mio. Leinwandpixel, 128 Mio. Ebenenpixel; kleinere Auflösung oder weniger Ebenen. |
| Langsame Zensur / KI / Video | Stärke/Größe reduzieren oder kleinere Vorschau verwenden; lange Berechnung abwarten/abbrechen. |
| Browserbild lässt sich nicht ziehen | Bild kopieren und Strg+V; geschützte URLs können scheitern. |
| Plus fehlt nach Wechsel des Kontos | Aktivierung gilt pro Windows-Benutzer. Schlüssel erneut eingeben. |
| GIF-Farben sehen anders aus | Formatgrenze: 256 Farben und harte Transparenz. |
| Videoquellen fehlen | Originaldateien an vorherige Stelle zurücklegen oder Projekt mit Quellen umziehen. |
| Google geht nicht | Verbindung prüfen, Neu laden; bekannten Browser-Prüfstand im ReBrowko-Artikel beachten. |

## Installieren, aktualisieren, reparieren
Repaintko schließen, MSI starten. Neue Installation: Bedingungen akzeptieren und Ordner auswählen. Bestehende ältere Version: Aktualisieren. Gleiche Version: Reparieren. Deinstallation über Windows → Einstellungen → Apps. Installer enthält Python und Bibliotheken. Das Paket ist nicht digital signiert.

## Fehler beschreiben
Version, betroffenen Modus, letzte Schritte, Dateiformat und Fehlermeldung notieren. Ein Screenshot hilft. Speichere wichtige Arbeit regelmäßig als Projekt und zusätzlich als Bild/Video.''')
    add('updates','Versionen','Update-Logs: Übersicht','''# Versionshistorie
Wähle links unter Versionen einen Eintrag. Die folgenden Logs stammen aus den dokumentierten Versionsnotizen im Programmordner. Für frühere Ausgaben vor 6.0.0 liegen keine vollständigen, verlässlich zugeordneten Logs vor; dafür werden keine Versionsnummern erfunden.

## 11.1.0 · Hilfezentrum
Neue Hilfe im vorhandenen Fenster: Kategorien, Volltextsuche, interne Links, Leseverlauf, bebilderte Erklärungen, Funktionskataloge und dokumentierte Versionshistorie. Offline verfügbar über Hilfe oder F1.''')
    readme=(Path(__file__).parent/'README.md').read_text(encoding='utf-8')
    for match in re.finditer(r'^## Neu in ([^\n]+)\n(.*?)(?=^## |\Z)',readme,re.M|re.S):
        title,body=match.groups()
        if title.startswith('11.1.0'):continue
        key='release-'+re.match(r'[\d.]+',title).group()
        add(key,'Versionen',title,'# '+title+'\n\n'+body.strip())
        pages[[p['key'] for p in pages].index('updates')]['text']+=f'\n\n[{title}](help:{key})'
    return pages
