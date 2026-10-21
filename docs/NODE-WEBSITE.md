# Node.js-Webseite: Anmeldung und Vorschläge

## Lokal starten

Node.js 24.15 oder neuer innerhalb der 24er-LTS-Reihe verwenden. Keine npm-Abhängigkeiten erforderlich. `npm start` startet http://127.0.0.1:3000. Die Startseite verwendet weiterhin das bestehende Design; `/community` enthält Registrierung, Anmeldung, eigene Vorschläge und die Admin-Übersicht. `npm test` führt die HTTP-Integrationstests aus.

Konten und Vorschläge bleiben in `data/community.sqlite` (SQLite mit WAL) gespeichert. Das Verzeichnis liegt außerhalb der öffentlichen Dateiliste und wird nicht eingecheckt. Beim Umzug die Datenbank konsistent sichern, etwa bei gestopptem Dienst inklusive WAL-Dateien. Keine flüchtige Hosting-Festplatte verwenden.

## Admin Rezzko

`Rezzko` ist bei öffentlichen Registrierungen reserviert, auch in anderer Großschreibung. Es gibt kein Standardpasswort und keine automatische Admin-Beförderung anhand eines vom Browser gesendeten Namens oder Rollenwerts.

Vor der ersten Nutzung auf dem Server `REZZKO_ADMIN_PASSWORD` über einen geheimen Umgebungswert setzen (12–128 Zeichen) und `npm run admin:setup` ausführen. Danach den Umgebungswert entfernen. Nicht in Chat, Git, Kommandozeilenargumenten oder einer öffentlichen Datei speichern. `DATABASE_PATH` muss dabei auf dieselbe Datenbank wie der Webserver zeigen. Ein bestehendes Konto wird nicht überschrieben. Der Besitzer kann sich anschließend als Rezzko anmelden. Es wurde bewusst noch kein produktives Admin-Passwort festgelegt.

## Verhalten

- Benutzername: 5–24 ASCII-Buchstaben, Zahlen oder Unterstriche. Groß-/Kleinschreibung zählt nicht als Unterschied. Datenbank-UNIQUE-Constraint schützt auch gleichzeitige Registrierungen.
- Passwörter: 12–128 Zeichen, gesalzene scrypt-Hashes; keine Klartextspeicherung.
- Sitzungen: zufällige Tokens, nur Hashes in der Datenbank, sieben Tage Gültigkeit, Logout widerruft die Sitzung. Produktionscookies sind Secure, HttpOnly und SameSite=Strict.
- Nur angemeldete Benutzer können Vorschläge senden und ihre letzten 100 eigenen Vorschläge lesen.
- Nur die serverseitig gespeicherte Admin-Rolle kann alle Vorschläge seitenweise sehen und den Status ändern: Neu / Wird geprüft / Geplant / Umgesetzt.
- Herkunftsprüfung für Schreibaktionen, Größenbegrenzung, parametrisierte SQL-Abfragen, XSS-sichere Textausgabe, Sicherheitsheader und begrenzte Passwortberechnungen.
- Keine E-Mail-Adressen erforderlich; E-Mail-Bestätigung und automatische Passwort-zurücksetzen-Funktion sind nicht implementiert.

## Bereitstellung (noch nicht erfolgt)

GitHub Pages führt kein Node.js aus. Für Konten und Vorschläge muss die komplette Webseite einschließlich `/api`, `/community` und `/version.json` auf einen Node-Host umziehen. Die bestehende Pages-Webseite wird durch diesen lokalen Branch nicht geändert.

Container: `docker build -f site/Dockerfile -t repaintko-web .`

Erforderliche Einstellungen: `NODE_ENV=production`, `PUBLIC_ORIGIN=https://repaintko.com` (ohne abschließenden Slash), `HOST=0.0.0.0`, `PORT=3000`, `DATABASE_PATH=/data/community.sqlite`. Dauerhaftes Volume nach `/data` einhängen. HTTPS am vertrauenswürdigen Reverse-Proxy terminieren. Eine Instanz verwenden. Der Server vertraut absichtlich keinen frei eingesendeten X-Forwarded-For-Headern; hinter einem Proxy teilen sich Nutzer das zusätzliche IP-Limit. Vor größerem Betrieb Proxy-IP-Prüfung und verteiltes Rate-Limiting planen.

Erst nach Hosting-/DNS-Freigabe umziehen. Danach alte Pages-Deployments deaktivieren, damit sie die Domain nicht wieder auf eine statische Kopie zeigen lassen. Die bisherigen Release-Downloads und signierten Update-Metadaten bleiben verfügbar.

## Tatsächlich geprüft

HTTP-Integrationstests: Registrierung/Anmeldung, Mindestlängen, reservierter Adminname, gleiche Namen in anderer Schreibweise und parallele Registrierung, Rollenmanipulation, Fremd-Origin, Zugriff auf fremde Vorschläge, Admin-Statusänderung, übergroße Eingaben, gesperrte private Dateipfade, persistente Daten/Sitzungen nach Neustart, Logout, Admin-Neuanlage-Sperre, Secure-Cookies und Rate-Limit. Keine produktive Veröffentlichung und kein Container-/Hosting-Test erfolgt.

Node-API-Referenz: https://nodejs.org/download/release/latest-v24.x/docs/api/sqlite.html

## Kostenloser Start: Render Free + Turso Free

Vorbereitet am 21.10.2026. Render Free hat kein dauerhaftes lokales Dateisystem; deshalb verwendet der Dienst dort zwingend eine externe Turso-Datenbank. Er startet auf Render ohne TURSO_DATABASE_URL nicht. Die lokale SQLite-Variante bleibt für Entwicklung erhalten.

1. Kostenlose Konten bei https://dashboard.render.com und https://app.turso.tech selbst anlegen/anmelden. Keine Zahlungsdaten oder kostenpflichtigen Pläne auswählen.
2. In Turso eine Datenbank im kostenlosen Tarif erstellen. Die Datenbankadresse und ein ausschließlich für diese Datenbank geltendes Zugriffstoken als Render-Secrets hinterlegen: TURSO_DATABASE_URL und TURSO_AUTH_TOKEN. Token nicht in Chat, Git oder Browsercode schreiben.
3. Render-Web-Service mit diesem Repository/Branch einrichten. Runtime Node, Plan Free, Build `node --check site/server.mjs`, Start `npm start`, Node 24.19.0, HOST=0.0.0.0, NODE_ENV=production. render.yaml enthält die Vorlage; automatische Deployments sind aus.
4. Zunächst die von Render vergebene HTTPS-Adresse nutzen. RENDER_EXTERNAL_URL wird automatisch als erlaubte Herkunft verwendet. Für repaintko.com nach ausdrücklicher DNS-Freigabe PUBLIC_ORIGIN=https://repaintko.com setzen.
5. Ein eigenes starkes Adminpasswort vorübergehend als REZZKO_ADMIN_PASSWORD in Render setzen. Beim Start wird Rezzko nur angelegt, falls er noch nicht existiert; kein vorhandenes Passwort wird überschrieben. Nach erfolgreicher Adminanmeldung den Secret-Umgebungswert entfernen.
6. Registrierung, Adminansicht und erneute Anmeldung nach einem Neustart gegen die echte Cloud-Datenbank testen, bevor die Domain umzieht. Die Cloudverbindung ist bisher nur durch lokale Transporttests geprüft, noch nicht mit einem echten Turso-Konto.

Die Gratisdienste haben Nutzungsgrenzen und können pausieren. Render schläft bei Inaktivität ein; erste Aufrufe können verzögert sein. Keine automatische Tarif-Aufwertung aktivieren. Render-Dokumentation: https://render.com/docs/free ; Turso-Tarife: https://turso.tech/pricing?frequency=monthly .
