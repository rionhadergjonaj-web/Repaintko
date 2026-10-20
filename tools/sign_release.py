"""Create signed version.json locally. Never uploads files or prints the private key."""
import argparse
import base64
import hashlib
import json
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from browser_store import crypt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from update_core import canonical, version, verify_manifest
from update_trust import PUBLIC_KEY

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('installer', type=Path)
    parser.add_argument('version')
    parser.add_argument('--output', type=Path, default=ROOT/'version.json')
    args = parser.parse_args()
    version(args.version)
    expected = f'Repaintko-Setup-{args.version}.msi'
    if args.installer.name != expected:
        raise ValueError('MSI-Dateiname muss zur Version passen.')
    digest = hashlib.sha256()
    with args.installer.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    now = int(time.time())
    payload = dict(schema=1, version=args.version, issued=now, expires=now+90*86400,
                   url=f'https://github.com/rionhadergjonaj-web/Repaintko/releases/download/v{args.version}/{expected}',
                   size=args.installer.stat().st_size, sha256=digest.hexdigest())
    key = Ed25519PrivateKey.from_private_bytes(crypt((ROOT/'.secrets/update-signing.dpapi').read_bytes(), decrypt=True))
    if key.public_key().public_bytes_raw().hex() != PUBLIC_KEY:
        raise ValueError('Signaturschlüssel passt nicht zum Vertrauensschlüssel der App.')
    raw = json.dumps(dict(payload=payload, signature=base64.b64encode(key.sign(canonical(payload))).decode()), indent=2).encode()
    verify_manifest(raw, bytes.fromhex(PUBLIC_KEY), '0.0.0')
    args.output.write_bytes(raw)
    print('Signierte Versionsdaten geschrieben. Noch nicht veröffentlicht.')

if __name__ == '__main__':
    main()
