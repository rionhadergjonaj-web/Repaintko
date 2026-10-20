"""EXE installer for the signed-format Windows Installer payload (not code-signed)."""
import sys,subprocess,hashlib,json,os
from pathlib import Path

def main():
    root=Path(__file__).resolve().parent
    msi=root/'Repaintko-Setup-13.1.0.msi'
    expected=json.loads((root/'setup-payload1310.json').read_text(encoding='utf-8'))
    with msi.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    if digest!=expected['sha256']:raise RuntimeError('Das Installationspaket ist beschädigt. Bitte erneut herunterladen.')
    if '--verify-only' in sys.argv:
        Path(sys.argv[sys.argv.index('--verify-only')+1]).write_text(json.dumps({'ok':True,'sha256':digest,'bytes':msi.stat().st_size}),encoding='utf-8');return 0
    exe=Path(os.environ.get('WINDIR','C:/Windows'))/'System32/msiexec.exe'
    return subprocess.call([str(exe),'/i',str(msi)])
if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None,str(exc),'Repaintko Setup',0x10);sys.exit(1)
