# Repaintko 13.0.0

Bildbearbeitung mit eigener Python-/Qt-Oberfläche, ohne Tkinter.

## Neu in 13.0.0

Details siehe **NEU-13.0.0.md**: neue Anschluss-Pfeile, verbesserter SQL-Austausch, optionales ReDataKo-Plugin, lokale SQL-KI, Browsermigration und fünf helle Plus-Designs. Programm und Installer starten als EXE.

## Installieren und starten

**Repaintko-Setup-13.0.0.exe** installieren, danach **Repaintko** auf dem Desktop oder im Startmenü öffnen. Python, Qt und Pillow sind enthalten; eine zusätzliche Python-Installation ist nicht nötig. Neue Installationen verwenden standardmäßig `C:\Program Files\Repaintko`. Beim Aktualisieren bleibt der bisherige Installationsordner erhalten.

Bei einer Neuinstallation Nutzungsbedingungen akzeptieren und den Zielordner auswählen. Bei bestehender Installation bietet das Setup Reparieren bzw. Aktualisieren an. Deinstallation über Windows → Einstellungen → Apps. Eigene Bilder bleiben erhalten. Das Installationspaket ist nicht digital signiert.

Quellcode starten: Python 3.14, Pakete aus `requirements.txt`, dann `py repaintko.py` oder **Repaintko starten.bat**.

## Neu in 12.0.0

- **Wallpaper pro Modus:** Add-ons → Wallpaper+ → Einstellungen → „Wallpaper anzeigen in“. Paint und GIF sind getrennt auswählbar, außerdem Notizbuch, ReTexto, Video, ReBrowko, DrawTogether, ReDrawko und Hilfe. Die Auswahl bleibt gespeichert. Standardmäßig bleibt der bisherige Hintergrund in Paint und GIF aktiv. Deckkraft und Plus-Berechtigung gelten in allen ausgewählten Modi. Webseiten, Videobilder und Dokumentinhalte werden nicht verändert; der Wallpaper liegt hinter der Oberfläche.
- **ReDrawko:** Unter Add-ons offline installieren; danach erscheint Modus → ReDrawko. Eigenständiger nativer Qt-Editor im Repaintko-Design ohne eingebundene Website. Auch ohne Plus verfügbar. Deinstallieren entfernt das Vorlagenpaket, nicht deine gespeicherten Diagramme.
- **Diagramme:** 33 Formtypen für ERM, UML, Flussdiagramme und Netzwerke; per Ziehen oder Doppelklick einfügen. Verschieben, Größe, Drehung, Farbe, Schrift, Deckkraft, Ausrichten, Verteilen, Gruppieren, Ebenen, mehrere Seiten, Raster und Einrasten. Gesperrte Formen sind gegen Verschieben geschützt.
- **Verbindungen:** Formen anklicken, gerade/rechtwinklige/gebogene Linien, Pfeile und ERM-Kardinalitäten. Anschlüsse folgen verschobenen Formen. Strg+Doppelklick auf eine Verbindung setzt einen Wegpunkt, der anschließend verschoben werden kann. Text und Beschriftungsposition sind bearbeitbar.
- **ERM:** Tabellen mit Attributen, Datentypen, PK/FK/UQ-Markierungen und NULL-Angabe. Doppelklick auf die Tabelle öffnet die Attributliste. Sechs Vorlagen: leer, ERM-Bestellsystem, Flussdiagramm, UML, Netzwerk, Mindmap.
- **Dateien:** .redrawko erhält alle nativen Diagrammdaten. PNG, SVG und PDF exportieren die aktuelle Seite. Rückgängig/Wiederholen, Zwischenablage, Duplizieren, Suchen/Ersetzen von Beschriftungen und lokale Wiederherstellung alle 30 Sekunden.

**Umfang und Austausch:** ReDrawko ist kein vollständiger Nachbau sämtlicher draw.io-Funktionen. draw.io-Import/Export unterstützt grundlegende Formen, Verbindungen und Seiten; spezielle Bibliotheken, freie Verbindungen und komplexe Formatierungen werden nicht vollständig übernommen. Warnungen zeigen übersprungene/ersetzte Elemente beim Import. Für verlustfreies Weiterarbeiten das native .redrawko-Format verwenden. SQL-Import/Export dient einfachen CREATE-TABLE-Grundschemas, erzeugt keine FK-Constraints und führt kein SQL aus. Cloud-Kollaboration, Plugins und sämtliche draw.io-Spezialbibliotheken sind nicht enthalten.

## Neu in 11.8.0

- **Bbc Gleitzeit Saldo:** Der Browserwert wird standardmäßig als Stand seit dem letzten Ausbadgen verstanden. Die laufende Arbeitszeit seit dem offenen Einbadgen zählt zusätzlich. -4:00 um 12:00 bedeutet Ziel 16:00, wenn die mindestens 30 Minuten Pause bereits erfüllt sind. Neu laden verschiebt dieses Ziel nicht. Längere tatsächliche Pausen zählen weiterhin vollständig.
- **DrawTogether:** Derselbe Paint-Editor wie im Bildmodus, ohne Modus-Auswahl. Alle Pinsel, Füller, Formen, Text, Auswahl, Füllen, Pipette, Zensur, Bildimport, Fotoeffekte, Ebenen, Blattfarbe und Blattdeckkraft sind verfügbar. Plus-Funktionen benötigen weiterhin Plus auf dem jeweiligen PC. Dateiaktionen wirken auf die gemeinsame Zeichnung; Speichern erstellt eine lokale Datei.
- **Flüssiger zeichnen:** Eigene Striche erscheinen sofort. Kleine geänderte Pixelbereiche werden gebündelt und im Hintergrund komprimiert. Der Host bestätigt die Änderungen in Reihenfolge. Unterschiedliche Bereiche/Ebenen lassen sich gleichzeitig bearbeiten. Bei konkurrierenden Änderungen derselben Pixel oder bei gleichzeitigem Umbau der Ebenen wird nichts blind überschrieben: Der lokale Entwurf bleibt erhalten und kann vor „Neu synchronisieren“ gespeichert werden. Rückgängig/Wiederholen betreffen eigene Aktionen und prüfen ebenfalls auf Konflikte.
- **Add-on-Übersicht:** Wallpaper+ besitzt eine Karte mit Landschaftssymbol und Plus unten rechts. Je nach Zustand gibt es Installieren oder Deinstallieren; Einstellungen öffnet die Bildgalerie samt Deckkraftregler. Derzeit ist Wallpaper+ das verfügbare Add-on.

Alle DrawTogether-Teilnehmer benötigen 11.8.0 oder eine kompatible neuere Version. Die lokale Sitzung bleibt verschlüsselt und funktioniert ohne Internet. Die bisherige Grenze von 16 Millionen Blattpixeln, 64 Millionen Ebenenpixeln und 32 Ebenen bleibt bestehen.

## Neu in 11.7.0: Add-ons und Wallpaper+

Öffne oben **Add-ons** und klicke bei **Wallpaper+** auf **Installieren**. Das Bildpaket gehört zum vollständigen Setup, wird aber erst durch diesen Klick im lokalen Benutzerordner eingerichtet. Es benötigt weder Internet noch Administratorrechte und enthält keinen ausführbaren Erweiterungscode. **Wallpaper+ aktiv** schaltet es ein oder aus. **Deinstallieren** entfernt die installierte Kopie; über Installieren lässt sie sich später wieder hinzufügen. Zeichnungen bleiben erhalten.

Die Sammlung enthält genau **101 neue Wallpaper**: **20 einfarbige Hintergründe für alle**, **40 Anime-/Cartoon-Landschaften für Plus** und **40 fotorealistisch gestaltete Landschaften und ein echtes Oeschinensee-Foto für Plus**. Die 80 ursprünglichen Landschaften wurden mit dem eingebauten Imagegen-Werkzeug erzeugt; sie sind keine Fotos realer Orte. Das zusätzliche Oeschinensee-Panorama ist ein echtes Foto von Bob Tan (CC BY-SA 4.0). Quelle und Lizenz stehen beim Vorschaubild und in assets/WallpaperPlus-Credits.txt. Kategorien und Suche erleichtern die Auswahl. Alle dürfen die Vorschaubilder ansehen, die 81 Plus-Motive lassen sich nur nach der Plus-Aktivierung anwenden. Wähle ein Bild und klicke **Wallpaper anwenden** oder doppelklicke darauf.

**Hintergrund-Deckkraft** regelt die Wallpaper von **0 bis 100 %**. Bei 0 % bleibt dein bisheriges Design sichtbar; bei 100 % ist das Wallpaper vollständig sichtbar. Auswahl, Aktivierung und Deckkraft bleiben nach dem Neustart erhalten. Das Wallpaper füllt den Hintergrund proportional aus; je nach Fensterform werden die Ränder beschnitten. Es wird nur beim Wechsel oder Ändern der Fenstergröße neu skaliert. Die Add-on-Verwaltung bleibt auch aus anderen Modi erreichbar; die Wallpaper selbst dekorieren den Bild-/GIF-Zeichenbereich.

Wallpaper liegen hinter dem Blatt und werden **nicht in Bilder oder GIFs exportiert**. Sie verändern weder Ebenen noch Blattdeckkraft. Wenn dein Blatt die ganze Fläche ausfüllt, verkleinere den Zoom, um mehr vom Hintergrund zu sehen. Die Originalauflösung der Landschaften bleibt erhalten; die 20 Farbflächen sind 1920 × 1080 Pixel groß. Die App prüft das Paket vor der Installation auf Vollständigkeit, Dateitypen und Prüfsummen. Abbrechen oder ein beschädigtes Paket lässt eine vorhandene Installation erhalten.

## Neu in 11.6.0: Bbc-Zeiterfassung

Unter **Ansicht → Saldo berechnen** die offizielle Bbc-Anmeldeseite öffnen und selbst anmelden. Anschließend den heutigen Tag in der Zeiterfassung wählen. Die Anzeige steht rechts neben Spotify; über das Uhrsymbol öffnest du Anmeldung und Einstellungen erneut. Die bestehende ReBrowko-Anmeldesitzung wird verwendet. Eine Anmeldung in Chrome oder Codex wird nicht übertragen.

Wähle **8:12 Stunden**, **Saldo 0** oder **beide Ziele**. Für das Tagesziel werden die heutigen Beginn-/Ende-Buchungen addiert. Mindestens **30 Minuten Pause insgesamt** sind eingeplant. Längere gebuchte Pausen zählen vollständig; fehlt Pause, wird die fehlende Zeit zusätzlich eingeplant. Weitere spätere Pausen verschieben die Gehzeit. Im ausge­buchten Zustand erscheint die noch nötige Arbeitszeit statt einer angenommenen Rückkehrzeit.

Für Saldo 0 wählst du **Gleitzeit Saldo**, **Gleitzeit aktuell** oder einen eigenen Übertrag. Zusätzlich musst du festlegen, ob der gewählte Saldo **vor heute** gilt oder **die Arbeit bis zum Laden der Seite bereits enthält**. Die Website bezeichnet „Gleitzeit aktuell“ als Prognose; Repaintko kann daraus allein nicht sicher ableiten, ob heutige offene Buchungen schon enthalten sind. Bei unbekannter Bedeutung bleibt das Null-Ziel offen. Kläre die Bedeutung gegebenenfalls mit der zuständigen Zeiterfassung. Bei Übertrag vor heute lautet die Rechnung: Tagesziel minus Übertrag minus heutige Arbeitszeit. Bei aktuellem Saldo wird nur das verbleibende Minus ausgeglichen. Fehlende Mindestpause kommt jeweils dazu.

Die Seite wird im Hintergrund ungefähr jede Minute neu geladen, solange keine Formularänderungen oder Fehlzeiten erkannt werden. Sichtbare Formulare werden nicht automatisch neu geladen. Nach drei Minuten ohne neue Seitenladung werden Zeiten als veraltet behandelt. Bei anderem Datum, Fehlzeiten, unklaren/überlappenden Buchungen oder geänderten Feldern wird nicht geraten. Tagesziel ist fest 8:12; Sondertage bitte direkt im Extranet prüfen. Repaintko verändert oder übermittelt keine Buchungen und reicht keinen Monat ein. Saldo und Buchungswerte werden nur im Arbeitsspeicher gehalten. Einstellungen und die vom Browser gespeicherte Anmeldesitzung bleiben lokal erhalten. Abschalten über denselben Menüpunkt stoppt die Aktualisierung.

## Neu in 11.5.0: DrawTogether

Datei → DrawTogether öffnet den integrierten LAN-Zeichenmodus im vorhandenen Fenster. Jeder wählt einen Benutzernamen. Server hosten: Name, optionales Passwort (leer = offen), Kopie des aktuellen Bildes mit Ebenen oder neues Blatt. Server beitreten: automatische Liste im gleichen IPv4-LAN/WLAN, ohne IP-Eingabe. Suche per UDP-Broadcast auf Port 45873, Daten per TLS/TCP auf einem dynamischen Port. Keine Internet-, Konto- oder Cloud-Verbindung. Pro PC kann ein Server auf dem Discovery-Port laufen. Windows-Firewall: Repaintko bzw. die mitgelieferte Python-Laufzeit für private Netzwerke zulassen; Gast-WLAN/AP-Isolation/VPN kann die Suche verhindern. Es werden keine Firewall-Regeln automatisch geändert.

Pinsel, Füller, Radierer und Linie mit frei wählbarer Farbe, Größe (1–200) und Deckkraft. Aktionen werden gesammelt etwa alle 16 ms übertragen. Der Host ordnet und validiert alle Aktionen; jeder Client erhält dieselbe Reihenfolge. Die Anzeige wird bis zu 30-mal pro Sekunde aktualisiert. Stabile Ebenenkennungen verhindern, dass Umsortieren oder die Auswahl eines anderen Benutzers den Ziel-Layer ändern. Erstellen, Löschen, Umbenennen, Reihenfolge, Sichtbarkeit und Ebenendeckkraft werden synchronisiert; aktive Ebene und Zoom sind lokal. Nach dem Löschen einer Ebene werden verspätete Aktionen auf diese Ebene sichtbar zurückgewiesen. Kein globales Rückgängig, keine Fotoeffekte, Auswahlverschiebungen oder anderen Bildmodus-Werkzeuge in der Live-Sitzung. Das ursprüngliche Bild bleibt beim Wechsel unverändert; vorhandene Effekte werden beim Hosten als gerenderte Ebenenpixel übernommen.

Neue Teilnehmer erhalten einen vollständigen Ebenenstand. Bei Unterbrechungen pausiert Zeichnen und die Verbindung wird alle zwei Sekunden erneut versucht. Der bestätigte Zustand wird neu geladen; noch unbestätigte Aktionen werden mit fortlaufenden Kennungen erneut gesendet, ohne doppelte Anwendung. Wiederverbindung gilt für denselben laufenden Host; nach einem Host-Neustart neu beitreten. Nicht bestätigte Änderungen dürfen vor dem Speichern nicht mehr ausstehen. Host kann Sitzung beenden, Teilnehmer verlassen; letzter empfangener Stand bleibt nach Serverende speicherbar. Strg+S / Zeichnung speichern exportiert eine lokale PNG-Datei oder ein Repaintko-Projekt mit Ebenen. Vor Verlassen/Beenden erfolgt eine Rückfrage. Ein reiner Moduswechsel lässt die Sitzung im Hintergrund weiterlaufen; über Modus → DrawTogether zurückkehren.

Bis zu 32 gleichzeitige Verbindungen (einschließlich Host-Client), 32 Ebenen, 16 Millionen Blattpixel und zusammen 64 Millionen Ebenenpixel. Langsame Clients werden bei überfüllter Warteschlange getrennt und synchronisieren neu, statt die Gruppe anzuhalten. Netzwerk, Suche, TLS-Start, Darstellungsvorbereitung und Speichern laufen außerhalb des UI-Threads. Passwörter werden nicht übertragen oder auf Platte gespeichert: PBKDF2-SHA256 (200.000 Durchläufe), zufällige Challenge und HMAC; zusätzlich TLS ab 1.2. Das Sitzungscertifikat wird beim Verbindungsaufbau gegen den Fingerabdruck aus der LAN-Suche geprüft und bei Wiederverbindung unverändert erwartet. Die erste LAN-Suche ist nicht durch eine öffentliche Zertifizierungsstelle beglaubigt; DrawTogether ist für vertrauenswürdige lokale Netze gedacht. Python-cryptography und seine Lizenzen sind in draw_vendor enthalten.

## Neu in 11.4.0: ReTexto

Modus → ReTexto öffnet einen Texteditor im bestehenden Fenster. Eigene Tabs für TXT, Markdown und andere Textdateien, Neu/Öffnen/Speichern/Speichern unter/Alle speichern, Drag-and-drop, Rückgängig/Wiederholen, Ausschneiden/Kopieren/Einfügen, Suchen/Ersetzen/Alle ersetzen, Weitersuchen, Gehe zu Zeile, Uhrzeit/Datum, Zeilenumbruch, Schriftart, Zoom, Seitenlayout und Drucken. Die Statusleiste zeigt Zeile, Spalte und Zeichenzahl. Dateien bis 64 MB; UTF-8, UTF-8 mit BOM, UTF-16 LE/BE mit BOM und Windows-1252 sowie CRLF/LF/CR. Beim Speichern werden gemischte Zeilenumbrüche auf die gewählte Variante vereinheitlicht. Geänderte Dateien werden atomar gespeichert. Externe Änderungen lösen eine Rückfrage aus. Ungespeicherte Texte bleiben beim Moduswechsel erhalten; beim Schließen gibt es Speichern/Verwerfen/Abbrechen. Keine automatische Wiederherstellung nach Programmabsturz.

Markdown bietet eine geteilte Vorschau und Einfügehilfen für Fett/Kursiv/Überschrift/Liste/Code/Link. Die gespeicherte Datei bleibt reiner Text. Vorschau lädt keine externen Bilder und öffnet keine Links. Rechtschreibung unter Extras verwendet lokale Windows-Wörterbücher; Sprache auswählbar, Fundstellen und Vorschläge mit einzelner Übernahme. Fehlende Wörterbücher lassen sich über die Windows-Spracheinstellungen installieren. Prüfung bis 200.000 Zeichen / 500 Fundstellen; keine fortlaufende Grammatikprüfung.

Extras → Lokale KI-Texthilfe bietet Umschreiben, Zusammenfassen, Rechtschreibung/Grammatik verbessern und Text verfassen. Qwen2.5-1.5B-Instruct (Q4_K_M) und llama.cpp CPU sind enthalten. Keine Anmeldung, API-Schlüssel oder Textübertragung. Verwendet Auswahl oder ganzen Text bis 6.000 Zeichen und bis 2.000 Zeichen Auftrag; maximal 640 Ausgabe-Tokens. Vorschlag lässt sich bearbeiten, ersetzen oder am Cursor einfügen und rückgängig machen. KI kann Fehler machen oder Details auslassen. Berechnung läuft im Hintergrund und ist abbrechbar; Geschwindigkeit hängt vom PC ab. Das Modell benötigt ungefähr 1,1 GB auf der Festplatte und zusätzlichen Arbeitsspeicher. Modelllizenz Apache 2.0, llama.cpp MIT; Lizenzen und Prüfsummen liegen in text_ai_runtime.

Tastenkürzel in ReTexto: Strg+N/O/S, Strg+Umschalt+S, Strg+W/P, Strg+Z/Y/X/C/V/A, Strg+F/H, F3/Umschalt+F3, Strg+G, F5 und Strg++/−/0. Die Menüs zeigen die Kürzel an. ReTexto ist kein vollständiger Nachbau aller aktuellen Windows-Notepad-Funktionen: keine Cloud-/Copilot-Anbindung und keine Tab-Wiederherstellung. Das interne Notizbuch bleibt ein eigener Modus.

## Neu in 11.3.0: Notizbuch

Modus → Notizbuch öffnet bis zu 100 interne Textnotizen im bestehenden Fenster, ohne Plus oder Internet. Titel, Text, Suche, neue Notizen und Löschen mit Bestätigung. Automatisches Speichern nach kurzer Schreibpause sowie vor Wechsel/Schließen. Keine Exportfunktion. SQLite speichert die Daten im Repaintko-Benutzerdatenordner unter Notizbuch/notizen.sqlite3, getrennt vom Installationsordner, damit Updates sie erhalten und keine Administratorrechte nötig sind. Es handelt sich um lokale Dateien auf diesem PC, nicht um Cloud-Speicherung. Speicherfehler bleiben sichtbar und verhindern den Wechsel/Schließen, solange Änderungen nicht gespeichert sind. Gleichzeitige Änderungen in mehreren Fenstern werden erkannt statt unbemerkt überschrieben. Neu laden verwirft ungespeicherte Änderungen erst nach Bestätigung.

## Neu in 11.2.0: ReBrowko mit Tabs und gespeicherten Daten

Die Internetprüfung startet automatisch beim Programmstart und läuft alle 30 Sekunden im Hintergrund. Chromium und Webseiten werden erst im Browsermodus geladen. Bis zu 30 Tabs, neue Fenster als Tabs, Schließen und Umsortieren. Strg+T neuer Tab, Strg+W schließen, Strg+L Adressleiste, Strg+H Verlauf, Strg+Tab/Strg+Umschalt+Tab wechseln. Der durchsuchbare Verlauf behält bis zu 2000 Seiten einschließlich Google-Suchen und lässt sich löschen.

Cookies und Website-Speicher bleiben im lokalen Profil für das Windows-Benutzerkonto erhalten. Webseiten können dennoch eine erneute Anmeldung verlangen; manche blockieren eingebettete Browser. Passwörter werden über Login speichern aus einem sichtbaren Formular übernommen oder manuell eingegeben und erst nach Bestätigung gespeichert. Die Datei wird mit Windows-DPAPI pro Benutzer verschlüsselt, ohne Klartext-Fallback. Login ausfüllen verlangt eine Benutzerauswahl und füllt nur auf exakt derselben HTTPS-Origin (Host und Port); es meldet nicht automatisch an. Mehrstufige und fremde eingebettete Formulare können manuelle Eingaben benötigen. Passwörter lassen sich im Manager löschen; Cookies und Verlauf sind separat löschbar. Keine Synchronisierung oder Übernahme von Passwörtern anderer Browser. Die Daten liegen im lokalen Repaintko-Benutzerdatenordner unter ReBrowko. Tabs werden beim Programmneustart nicht wiederhergestellt.

## Neu in 11.1.0: Hilfezentrum

Hilfe oder F1 öffnet das Offline-Handbuch im bestehenden Fenster: Kategorien, Volltextsuche, Bilder, Artikelverlauf, Anleitungen für alle Modi und dokumentierte Update-Logs ab 6.0.0. Zur Arbeit führt zum vorherigen Modus zurück.

## Neu in 11.0.0

Modus → ReBrowko · Internet öffnet einen Browser im bestehenden Fenster, auch ohne Plus. Suchbegriffe verwenden die echte Google-Suche. Webadressen, Zurück, Vor und Google-Startseite stehen bereit. Ohne erreichbares Internet/Google wird ein Hinweis angezeigt; ↻ prüft erneut. Bild, GIF und Videoschnitt bleiben beim Wechsel erhalten. Webseiten und Suchanfragen werden wie in einem Browser an die jeweiligen Anbieter übertragen. Die Browsersitzung ist nur im Arbeitsspeicher; Downloads sind in dieser Version nicht verfügbar. ReBrowko ist kein Google-Produkt und garantiert keine Anmeldung bei allen Webseiten.

## Neu in 10.1.0

Füller mit schräger breiter Feder für richtungsabhängig dünne und breite Striche, eigener Größe und einstellbarer Deckkraft. Die Werkzeugleiste verwendet kompakte Symbole mit Namen als Tooltip.

## Neu in 10.0.1

Der Video-Editor ersetzt die Arbeitsfläche im bestehenden Fenster. Über „← Bild / GIF“ oder Modus → Zurück zum Bild / GIF wechselst du zurück. Bild, GIF und Videoschnitt bleiben beim Wechsel erhalten. Die Tastenkürzel gelten für den jeweils sichtbaren Editor.

## Neu in 10.0.0: Video-Editor für Repaintko Plus

Modus → Video-Editor (Plus) öffnet den nichtdestruktiven Videoschnitt. Die Quelldateien bleiben unverändert. Bis zu 100 Clips lassen sich hinzufügen, schneiden, duplizieren, löschen und umsortieren. In/Out beschneiden einen Clip; Geschwindigkeit reicht von 0,25× bis 4×, Lautstärke von 0 bis 200 %, Stummschalten ist pro Clip möglich. Strg+S teilt den Clip am Abspielkopf. Strg+Umschalt+S speichert das Schnittprojekt als .repaintvideo. Strg+I importiert, Strg+E exportiert, Strg+Z/Y macht Schnittänderungen rückgängig bzw. wiederholt sie (100 Schritte). In Bild- und GIF-Modus bleibt Strg+S Speichern.

12 Bildeffekte können auf beliebige Zeitbereiche innerhalb eines Clips gelegt werden. Keyframes für Zoom, Position X/Y, Helligkeit und Lautstärke werden linear interpoliert. Zoom reicht von 1× bis 4×; Position ist bei vergrößertem Bild sichtbar. 20 Übergänge zum nächsten Clip: Überblenden, Wischen links/rechts/oben/unten, Schieben links/rechts/oben/unten, Kreis, Rechteck, Distanz, Durch Schwarz, Durch Weiß, Radial, Sanft links/rechts/oben/unten und Auflösen. Audio wird bei Übergängen ebenfalls überblendet. Die Überlappung verkürzt die Gesamtlänge; ihre Dauer ist auf die halbe Länge beider Clips begrenzt.

Die Zeitleiste zeigt Effekte violett, Keyframes gelb und Übergänge grün. Nach Änderungen zeigt Scrubbing zunächst die Quelle; Wiedergabe berechnet eine Vorschau mit allen Bearbeitungen und Ton (640 × 360, bis 30 FPS). Vorschau und Export laufen im Hintergrund und sind abbrechbar. Große Projekte benötigen Zeit und temporären Speicher. Der Video-Export erzeugt MP4 mit H.264 und AAC; Ausgabe: HD, Full HD, 4K oder Hochkant Full HD bei 24/25/30/50/60 FPS. Vorschauqualität verändert die Exportauflösung nicht.

Ein .repaintvideo-Projekt speichert Schnittdaten und relative Verweise auf Quelldateien, nicht die Videos selbst. Zum Umziehen Projekt und Quellen gemeinsam kopieren. Fehlende Quellen werden beim Öffnen gemeldet. MP4-Export ersetzt kein editierbares Projekt. Diese Version hat eine sequenzielle Videospur mit Originalton; zusätzliche Musikspuren, Titeltexte, freie Überlagerungen und professionelle Farbkorrektur sind nicht enthalten. FFmpeg und ffprobe sind im Installer enthalten, samt Lizenz und Herkunft unter video_tools. Es werden keine Videodateien hochgeladen. Dokumentation der Filter: https://ffmpeg.org/ffmpeg-filters.html

## Neu in 7.0.2: Vorschau-Zoom

GIF-Vorschau mit Plus/Minus, Prozent-Eingabe, 100 %, Einpassen und Strg+Mausrad. Scrollleisten erlauben das Betrachten vergrößerter Bilder. Der Zoom bleibt während der Wiedergabe und beim Wechsel der Frames auf der Zeichenfläche erhalten. FPS-Beschriftung und Eingabe stehen direkt nebeneinander. Vorschau-Zoom und Zwiebelschicht verändern keine exportierten Pixel.

## Neu in 7.0.1: Zwiebelschicht

GIF-Modus und neue leere/importierte Frames starten mit 0 % Blattdeckkraft. Duplizieren übernimmt die Einstellungen des duplizierten Frames; das normale Bild bleibt unverändert. Die reine Zwiebel-Schaltfläche neben GIF speichern blendet den vorherigen Frame mit 26 % Deckkraft hinter dem aktuellen ein. Beim ersten Frame gibt es keine Vorschau. Die Zeichenhilfe wird weder exportiert noch in der Wiedergabe gezeigt und verändert keine Bildpixel.

## Neu in 7.0.0: GIF-Editor

Unter Modus → GIF-Editor wechseln. Das aktuelle Bild wird als erster Frame kopiert; das normale Bild bleibt separat erhalten. Unten Frames hinzufügen, duplizieren, Bilder importieren, löschen oder mit den Pfeilen umsortieren. Ein Klick auf einen Frame lädt ihn auf die normale Zeichenfläche mit Ebenen, Pinseln und Effekten. Rückgängig gilt pro Frame. FPS sind von 1 bis 50 einstellbar; Vorschau spielt die Animation in einer Schleife ab. GIF speichern oder Strg+S exportiert alle Frames als endlos wiederholte GIF-Datei. Beim Verlassen des Modus wird nach ungespeicherten Änderungen gefragt.

Alle Frames müssen dieselbe Größe haben. Importierte Bilder werden proportional eingepasst. Maximal 200 Frames und 128 Millionen Ebenenpixel insgesamt. GIF speichert höchstens 256 Farben pro Frame und nur harte Transparenz; halbtransparente Pixel werden bei 50 % getrennt. GIF-Zeiten sind in 10-ms-Schritten gerundet. GIF-Export reduziert die Ebenen auf das sichtbare Ergebnis; editierbare Animation-Projektdateien und das Einlesen bestehender Animationen sind in dieser Version nicht enthalten. Öffnen einer GIF-Datei im normalen Bildmodus öffnet deren erstes Bild.

## Neu in 6.2.5: Spotify-Steuerung

Der Spotify-Block sitzt jetzt in der Zeile mit Öffnen/Speichern und dem Logo. Unter dem Fortschrittsbalken stehen Vorheriger Titel, Wiedergabe/Pause und Nächster Titel. Die Befehle gehen ausschließlich an die erkannte Spotify-Sitzung. Während eines Befehls sind die Tasten kurz gesperrt; bei Ablehnung zeigt der Block einen Hinweis im Tooltip. Spotify bestimmt, ob Zurück zunächst zum Liedanfang springt und welche Titelwechsel verfügbar sind.

## Neu in 6.2.4: Spotify-Anzeige

Wenn die Spotify-Desktop-App einen Titel an Windows meldet, erscheint oben mittig Titel/Interpret mit Spielzeit, Gesamtdauer und Fortschrittsbalken. Pausen werden angezeigt. Ohne Spotify-Mediensitzung bleibt die Leiste verborgen. Alle Informationen werden lokal über Windows gelesen, ohne Konto-Verknüpfung, Internetzugriff oder Administratorabfrage. Der Spotify-Webplayer wird nicht erkannt. Voraussetzung: Windows 10 ab 1809 oder Windows 11 mit verfügbarer Windows-Medienschnittstelle. Bei fehlender Zeitinformation wird keine Dauer erfunden. Seit 6.2.5 kann die Anzeige Spotify auch steuern.

Technik: [Windows-Mediensitzungen](https://learn.microsoft.com/en-us/uwp/api/windows.media.control.globalsystemmediatransportcontrolssessionmanager) und [Zeitinformationen](https://learn.microsoft.com/en-us/uwp/api/windows.media.control.globalsystemmediatransportcontrolssessiontimelineproperties). Abfrage im Hintergrund alle zwei Sekunden, lokale Fortschrittsanzeige viermal pro Sekunde. Der unsichtbare Leseprozess endet mit Repaintko; es erscheint kein PowerShell-Fenster.

## Neu in 6.2.3: Designs und Blattdeckkraft

20 weitere Designs unter Ansicht → Design: 10 Standard (Olivenhain, Kupfer, Jeansblau, Salbei, Kirschholz, Petrol, Iris, Sandstein, Titan, Brombeere) und 10 Plus (Sonnenuntergang, Kometenschweif, Zauberwald, Lagune, Sakura bei Nacht, Wüstendämmerung, Eiskristall, Veilchennebel, Glühwürmchen, Ozeannacht).

Bild → Blattdeckkraft oder Optionen → Blattdeckkraft stellt den Hintergrund von 0 bis 100 % ein. Fotos und Zeichnungen behalten ihre eigene Deckkraft. Transparenz erscheint als Schachbrett. Projekte speichern die Einstellung; PNG/WebP/TIFF erhalten den Alpha-Kanal. JPG und PDF erhalten einen weißen Untergrund. Die separate Option „Mit transparentem Blatthintergrund speichern“ entfernt den Blatthintergrund weiterhin vollständig.

## Neu in 6.2.2: ruhiger Programmstart

Beim Öffnen fordert Repaintko keine Administratorrechte für das Desktop-Symbol mehr an, auch nicht nach Updates oder bei nicht speicherbaren Einstellungen. Ein bereits korrektes Symbol bleibt unverändert. Eine Änderung mit Administratorrechten ist weiterhin über Datei → Desktop-Symbol aktualisieren oder bei der Plus-Aktivierung möglich.

## Neu in 6.2.1: mehr Verlauf und neue Designs

Der Rückgängig-Verlauf hat jetzt das dreifache Speicherbudget: 480 statt 160 MB nach der bisherigen Größenberechnung. Bei gleicher Bildgröße bleiben entsprechend mehr Schritte verfügbar; die genaue Anzahl hängt von der Auflösung ab. Wiederholen und Änderungen nach Rückgängig funktionieren wie bisher.

Unter **Ansicht → Design → Standard-Designs** stehen drei zusätzliche Designs zur Verfügung: **Schieferblau**, **Kakao** und **Pflaume**. Zusammen mit den bisherigen Designs sind es elf frei verfügbare Designs.

**Ansicht → Design → Plus-Designs** enthält zehn exklusive Designs: **Abendrot · Nacht**, **Sternennacht**, **Nordlicht**, **Kosmos**, **Mondlicht**, **Glut**, **Tiefsee**, **Roséquarz**, **Polarlicht** und **Obsidian Gold**. Diese Designs verwenden dezente Farbverläufe. Sternennacht, Kosmos, Mondlicht, Polarlicht und Obsidian Gold besitzen zusätzliche kleine weiße Sternpunkte im Arbeitsbereich. Die Punkte sind statisch, damit sie nicht beim Zeichnen ablenken oder Animationen Rechenleistung beanspruchen.

Plus-Designs werden erst nach Plus-Aktivierung freigeschaltet. Ohne gültige Aktivierung bleibt ein gespeichertes Plus-Design gesperrt; beim Start wird stattdessen Dunkel verwendet. Die Designwahl bleibt gespeichert. Designs verändern ausschließlich die Oberfläche, niemals Bildpixel oder Exporte.

## Neu in 6.2.0: lokale Objektentfernung für Plus

Nach Plus-Aktivierung **KI entfernen (Plus)** in der Werkzeugleiste oder im Menü **Effekte** öffnen. Bearbeitet wird die aktive, sichtbare Ebene.

1. Person oder Objekt vollständig rot übermalen, einschließlich Schatten, falls dieser ebenfalls verschwinden soll. Mit der rechten Maustaste Markierungen entfernen; die Pinselgröße lässt sich einstellen.
2. **Hintergrund ergänzen (lokale KI)** oder **Transparent entfernen** auswählen.
3. **Vorschau berechnen** anklicken. Über **Original zum Vergleichen anzeigen** das Ergebnis prüfen.
4. **Als neue Ebene übernehmen** speichert das Ergebnis auf einer neuen Ebene. Die ursprüngliche Ebene wird ausgeblendet und bleibt inklusive ihrer Fotoeffekte erhalten. **Strg+Z** macht die Änderung rückgängig. Abbrechen verändert das Dokument nicht.

**Hintergrund ergänzen** verwendet das mitgelieferte LaMa-Modell über ONNX Runtime auf der CPU. Modell und Bibliotheken sind im Installer enthalten. Es erfolgen weder Downloads noch Bild-Uploads während der Bearbeitung; ONNX-Telemetrie ist deaktiviert. Der erste Aufruf lädt das Modell und kann mehrere Sekunden dauern. Die Berechnung läuft im Hintergrund und kann über Abbrechen verworfen werden.

Die KI arbeitet mit einem 512 × 512 großen Ausschnitt um die Markierung. Das Gesamtbild behält seine Auflösung; unmarkierte Pixel bleiben unverändert. Große entfernte Bereiche und komplizierte Hintergründe können sichtbare Fehler oder erfundene Details enthalten. Die Auswahl erfolgt mit dem Pinsel, nicht durch automatische Objekterkennung.

**Transparent entfernen** entfernt die Deckkraft innerhalb der Markierung ohne KI-Hintergrundberechnung. Das Schachbrett zeigt transparente Stellen. Auf dem Blatt können darunterliegende sichtbare Ebenen erscheinen. Für einen transparenten Export PNG/WebP/TIFF wählen und unter Datei die Option für transparenten Blatthintergrund aktivieren.

Mindestens eine zusätzliche Ebene muss innerhalb der bestehenden Grenzen frei sein (32 Ebenen, insgesamt 128 Millionen Ebenenpixel). Die KI benötigt zusätzlichen Arbeitsspeicher. Der Installer ist wegen des lokalen Modells größer als bisher.

Modell: [OpenCV LaMa](https://huggingface.co/opencv/inpainting_lama), Apache 2.0; Forschung: Suvorov et al., *Resolution-robust Large Mask Inpainting with Fourier Convolutions*, WACV 2022. Herkunft, Prüfsumme und Lizenz liegen im Ordner `models`. Die mitgelieferten Bibliotheken enthalten ihre Lizenzdateien.

## Neu in 6.1.3: Desktop-Symbol

Nach Plus-Aktivierung wird auch die Desktop-Verknüpfung auf das blaue Plus-Symbol umgestellt. Bereits aktivierte Installationen versuchen dies beim ersten Start nach dem Update automatisch. Das Symbol verweist auf die mitgelieferte ICO-Datei in der Installation; Startziel, Argumente und Arbeitsordner bleiben erhalten. Explorer wird über die Änderung informiert.

Beim öffentlichen Desktop kann Windows Administratorrechte anfordern. Abbrechen ändert die Plus-Aktivierung nicht. Unter **Datei → Desktop-Symbol aktualisieren** lässt sich die Aktualisierung erneut auslösen, auch nach einer Installer-Reparatur. Es werden nur vorhandene Repaintko-/Repainko-Verknüpfungen aktualisiert, die auf genau diese Installation zeigen. Es werden keine zusätzlichen Verknüpfungen angelegt. Ein Symbol auf dem öffentlichen Desktop ist für alle Windows-Benutzer sichtbar.

## Neu in 6.1.2: Repaintko Plus

Das Logo rechts oben ist jetzt 64 statt 32 Pixel groß. Unter **Datei → Repaintko Plus aktivieren** den Access Key eingeben. Nach erfolgreicher Aktivierung erscheint ein blaues Logo mit Pluszeichen, auch als Fenstersymbol. Die Aktivierung bleibt für das aktuelle Windows-Benutzerkonto nach einem Neustart und MSI-Update erhalten. Die Theme-Auswahl bleibt unabhängig davon.

Die Prüfung erfolgt lokal ohne Konto oder Server. Der Schlüssel wird nicht im Klartext gespeichert. Diese Version ergänzt die Aktivierung und das Plus-Logo; bestehende Bearbeitungsfunktionen bleiben verfügbar.

## Neu in 6.1.1: Browser-Bilder und sicheres Platzieren

Bilder direkt aus dem Browser oder Explorer ins Fenster ziehen. Unterstützt werden Bilddaten, HTML-Bildverweise, direkte HTTP-/HTTPS-Bildadressen und eingebettete Data-Bilder. Ein manuelles Herunterladen ist normalerweise nicht nötig. Bei Internetadressen lädt Repaintko das Bild mit einer abbrechbaren Fortschrittsanzeige (maximal 40 MB und 64 Millionen Bildpixel). Wenn eine Webseite den Zugriff nur nach Anmeldung erlaubt oder keine echten Bilddaten übergibt, kann „Bild kopieren“ im Browser und **Strg+V** helfen. Repaintko übernimmt keine Browser-Anmeldedaten.

**Bilder werden jetzt immer auf einer neuen Ebene eingefügt**, auch beim Ziehen ohne Strg. Das gilt ebenfalls für **Datei → Bild einfügen** und **Strg+V**. Vor dem Einfügen öffnet sich die Platzierungsvorschau: das Bild mit der Maus verschieben oder X/Y in Pixeln eingeben, danach **Platzieren**. **Abbrechen / Esc** verändert das Dokument nicht. Die Leinwand wird bei Bedarf nach rechts/unten erweitert, innerhalb der Pixel-Limits. Alte Ebenen, Zeichnungen, Fotos und Effekt-Einstellungen bleiben erhalten. Der neue Bildinhalt kann anschließend mit **Auswahl** weiter verschoben werden. **Strg+Z** macht Einfügen oder Verschieben rückgängig.

**Datei → Öffnen** öffnet ein Bild weiterhin als eigenständiges Dokument. Gezogene PDFs und Projektdateien verwenden weiterhin Öffnen mit Speicherabfrage; PDFs zeigen ihre Seitenauswahl. Quelldateien werden nicht verschoben oder gelöscht. Pro Drag-and-drop wird eine Datei bzw. ein Bild angenommen.

## Neu in 6.0.0

- **Bild → Blattfarbe ändern** oder **Optionen → Blattfarbe ändern**: freie RGB-/HSV-/Hex-Farbauswahl für den Hintergrund. Neue Blätter haben eine transparente Zeichenebene über dieser Farbe. Weiße Stellen in Fotos bleiben echte Bildinhalte.
- **Datei → Mit transparentem Blatthintergrund speichern** aktivieren und PNG, WebP oder TIFF wählen. Ohne Häkchen wird die Blattfarbe mitgespeichert. JPEG unterstützt keine Transparenz. Bereits vorhandene weiße Hintergründe in älteren Bildern/Projekten werden nicht automatisch entfernt.
- Schnelleres Füllen mit exakter Farbübereinstimmung und vierseitiger Verbindung. Große Berechnungen laufen im Hintergrund; Abbrechen verwirft das Ergebnis. Die Anzeige bleibt bedienbar.
- Zensurpinsel kopieren RGB-Quellen nicht mehr unnötig und bearbeiten lange Striche mit weniger überlappenden Teilberechnungen. Die Anzeige wird beim Loslassen nicht nochmals vollständig aufgebaut. Geschwindigkeit hängt weiterhin von Bild, Modus und Hardware ab.
- **↶ Zurück / ↷ Vor**, Logo oben rechts und korrekter Name **Repaintko**.
- Acht Themes unter **Ansicht → Design**: Hell, Dunkel, Ozean, Wald, Abendrot, Lavendel, Bernstein und Graphit.
- Schriftwahl aus den unter Windows installierten Schriftarten, inklusive Vorschau im Auswahlfeld; Schriftgröße und Fettdruck bleiben verfügbar.
- Jeder Zeichenpinsel merkt sich seine eigene Größe. Alle Zensurarten teilen weiterhin die Zensurgröße. Auch die Bleistiftgröße wirkt sich jetzt auf den Strich aus.
- **Datei → Bild einfügen** versucht 4× Gesamtpixel (doppelte Breite und Höhe), danach 2× Gesamtpixel, sonst Originalgröße. Die Leinwand wächst bei Bedarf mit, statt das Bild abzuschneiden. Es gelten 64 Millionen Leinwandpixel und 128 Millionen Ebenenpixel insgesamt. Passt selbst das Original nicht, wird das Einfügen abgelehnt. Öffnen und Einfügen aus der internen Zwischenablage behalten die Originalauflösung. Hochskalierung erzeugt keine zusätzlichen Bilddetails.
- Der Radierer entfernt Deckkraft und erhält Fotoeffekte und ihre Einstellungen. Spätere Effektänderungen machen ausradierte Stellen nicht wieder sichtbar.

## Zeichnen, Ebenen und Effekte

Pinsel, Bleistift, Airbrush, Radierer, Füllen, Pipette, Formen, Text, Auswahl und Zoom. Deckkraft für Zeichenpinsel, RGB-/HSV-/Hex-Farbwähler sowie Vorder- und Hintergrundfarbe für Werkzeuge.

Ebenen können ergänzt, dupliziert, umbenannt, ausgeblendet, umgeordnet und zusammengeführt werden. Jede Ebene hat eine eigene Deckkraft. Maximal 32 Ebenen bei insgesamt 128 Millionen Ebenenpixeln.

**Datei → Projekt mit Ebenen speichern** erzeugt `.repaintko`-Dateien mit Ebenen, Blattfarbe, Transparenz und Effekt-Einstellungen. Ältere `.repainko`-Projekte können weiterhin geöffnet werden. Bildformate exportieren die sichtbare Kombination. Bei mehreren Ebenen ersetzt ein Bildexport nicht das Speichern des Projekts.

Fotoeffekte umfassen Helligkeit, Kontrast, Sättigung, Schärfen, Staub entfernen, Klarheit, Struktur, Looks und Grafikeffekte. Unterschiedliche Effekte lassen sich kombinieren; derselbe Effekt wird aktualisiert, statt sich mehrfach zu stapeln. Die Vorschau ist verkleinert; beim Übernehmen wird die volle Auflösung berechnet.

Zensur wird mit dem Pinsel nur auf die gewünschten Bereiche gemalt. 27 Modi, unter anderem Verpixeln, Mosaik, Spirale, Speed-Streifen, Feine Wischstreifen und Malpinsel-Blur. Größe und Stärke sind einstellbar. Schwarze Zensur ist entfernt.

## Dateien und Bedienung

**Als Kopie speichern** (`Strg+Alt+S`) erstellt eine separate Datei, ohne das Original zu überschreiben oder den aktuellen Dateipfad zu ändern. Rückgängig: `Strg+Z`, Wiederholen: `Strg+Y`.

Bilder werden beim Öffnen in Originalauflösung eingelesen und nur für die Anzeige an das Fenster angepasst. PDF-Dateien lassen sich über Öffnen importieren: Seite und Auflösung wählen; die ausgewählte Seite wird als neues Bild geöffnet. Das PDF bleibt unverändert.

Auf kleinen Bildschirmen werden die Seitenleisten automatisch eingeklappt. Über **Optionen**, **Werkzeuge** und **Ebenen** lassen sie sich wieder einblenden. Die Oberfläche unterstützt Fenster ab 640 × 440 Pixel.

## Prüfung

117 automatisierte Tests einschließlich Ebenen, PDF-Import, Zensurarten, GUI, Export, Pixel-Limits und Radierer/Effekt-Regressionsprüfung. Füllvergleich auf diesem Rechner: 1000 × 1000 Pixel ca. 0,04 s statt 2,3 s; 3840 × 2160 Pixel ca. 0,19 s. Das sind Beispielmessungen, keine garantierten Zeiten.
