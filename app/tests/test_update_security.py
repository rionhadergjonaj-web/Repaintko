import base64, hashlib, json, unittest
import io, tempfile
from pathlib import Path
from unittest.mock import patch
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from update_core import canonical, verify_manifest, version

class Updates(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        self.public = self.key.public_key().public_bytes_raw()
        self.payload = dict(schema=1,version="13.1.0",issued=100,expires=200,url="https://github.com/rionhadergjonaj-web/Repaintko/releases/download/v13.1.0/Repaintko-Setup-13.1.0.msi",size=123,sha256="a"*64)
    def envelope(self):
        return json.dumps(dict(payload=self.payload,signature=base64.b64encode(self.key.sign(canonical(self.payload))).decode())).encode()
    def test_upgrade(self): self.assertEqual(verify_manifest(self.envelope(),self.public,"13.0.1",150)["version"],"13.1.0")
    def test_no_downgrade(self): self.assertIsNone(verify_manifest(self.envelope(),self.public,"14.0.0",150))
    def test_tampering(self):
        raw=self.envelope().replace(b"13.1.0",b"99.1.0")
        with self.assertRaises(Exception): verify_manifest(raw,self.public,"13.0.1",150)
    def test_expired(self):
        with self.assertRaises(ValueError): verify_manifest(self.envelope(),self.public,"13.0.1",201)
    def test_wrong_key(self):
        with self.assertRaises(Exception): verify_manifest(self.envelope(),Ed25519PrivateKey.generate().public_key().public_bytes_raw(),"13.0.1",150)
    def test_untrusted_host(self):
        self.payload["url"]="https://attacker.invalid/setup.msi"
        with self.assertRaises(ValueError): verify_manifest(self.envelope(),self.public,"13.0.1",150)
    def test_numeric_version(self): self.assertGreater(version("13.10.0"),version("13.9.9"))
    def test_download_checks_before_replacing_existing_file(self):
        from update_core import download
        data=b'verified installer fixture'
        payload=dict(url='https://example.invalid/setup.msi',size=len(data),sha256=hashlib.sha256(data).hexdigest())
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'setup.msi';target.write_bytes(b'old valid installer')
            with patch('update_core.open_https',return_value=io.BytesIO(b'corrupt')):
                with self.assertRaises(ValueError):download(payload,target)
            self.assertEqual(target.read_bytes(),b'old valid installer')
            self.assertFalse(target.with_suffix('.part').exists())
            with patch('update_core.open_https',return_value=io.BytesIO(data)):
                download(payload,target)
            self.assertEqual(target.read_bytes(),data)
    def test_cancel_never_leaves_installable_partial(self):
        from update_core import download
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'setup.msi'
            with patch('update_core.open_https',return_value=io.BytesIO(b'fixture')):
                with self.assertRaises(InterruptedError):
                    download(dict(url='https://example.invalid/setup.msi',size=7,sha256='a'*64),target,cancelled=lambda:True)
            self.assertFalse(target.exists());self.assertFalse(target.with_suffix('.part').exists())
if __name__ == "__main__": unittest.main()
