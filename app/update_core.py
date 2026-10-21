"""Signed, bounded update metadata and atomic verified downloads. No UI dependencies."""
import base64, hashlib, json, os, re, time, urllib.request
from pathlib import Path
from urllib.parse import urlparse
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

MANIFEST_URL = "https://repaintko.com/version.json"
MAX_INSTALLER = 3 * 1024**3
RELEASE_PREFIX = "/rionhadergjonaj-web/Repaintko/releases/download/"

def version(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,5}\.[0-9]{1,5}\.[0-9]{1,5}", value):
        raise ValueError("Ungültige Versionsnummer")
    return tuple(map(int, value.split(".")))

def canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")

def verify_manifest(raw, public_key, current, now=None):
    if len(raw) > 65536: raise ValueError("Versionsdaten zu groß")
    envelope = json.loads(raw)
    payload = envelope["payload"]
    Ed25519PublicKey.from_public_bytes(public_key).verify(base64.b64decode(envelope["signature"], validate=True), canonical(payload))
    if payload.get("schema") != 1: raise ValueError("Unbekanntes Updateformat")
    now = int(time.time()) if now is None else now
    if type(payload.get("expires")) is not int or payload["expires"] <= now: raise ValueError("Versionsdaten sind abgelaufen")
    if type(payload.get("issued")) is not int or payload["issued"] > now + 300: raise ValueError("Versionsdaten liegen in der Zukunft")
    if payload["expires"] <= payload["issued"]: raise ValueError("Ungültige Gültigkeit")
    available = version(payload["version"])
    url = urlparse(payload["url"])
    if url.scheme != "https" or url.hostname != "github.com" or url.username or url.password or url.port or not url.path.startswith(RELEASE_PREFIX) or not url.path.endswith(".msi") or url.query or url.fragment:
        raise ValueError("Unzulässige Updatequelle")
    if type(payload.get("size")) is not int or not 0 < payload["size"] <= MAX_INSTALLER: raise ValueError("Ungültige Installationsgröße")
    if not re.fullmatch(r"[0-9a-f]{64}", payload.get("sha256", "")): raise ValueError("Ungültige Prüfsumme")
    return payload if available > version(current) else None

class HTTPSOnly(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlparse(newurl).scheme != "https": raise ValueError("Unsichere Weiterleitung")
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def open_https(url):
    if urlparse(url).scheme != "https": raise ValueError("HTTPS erforderlich")
    return urllib.request.build_opener(HTTPSOnly()).open(urllib.request.Request(url, headers={"User-Agent":"Repaintko-Updater/1"}), timeout=20)

def fetch_manifest():
    with open_https(MANIFEST_URL) as response:
        raw = response.read(65537)
    if len(raw) > 65536: raise ValueError("Versionsdaten zu groß")
    return raw

def download(payload, destination, progress=lambda done,total:None, cancelled=lambda:False):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(".part")
    digest = hashlib.sha256(); count = 0
    try:
        with open_https(payload["url"]) as source, partial.open("wb") as target:
            while True:
                if cancelled(): raise InterruptedError("Download abgebrochen")
                block = source.read(256 * 1024)
                if not block: break
                count += len(block)
                if count > payload["size"]: raise ValueError("Update größer als angekündigt")
                digest.update(block); target.write(block); progress(count, payload["size"])
            target.flush(); os.fsync(target.fileno())
        if count != payload["size"] or digest.hexdigest() != payload["sha256"]: raise ValueError("Update-Prüfsumme stimmt nicht")
        os.replace(partial, destination)
        return destination
    finally:
        partial.unlink(missing_ok=True)
