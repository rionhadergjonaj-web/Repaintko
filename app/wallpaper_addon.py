"""Install a data-only bundled wallpaper pack into the current user's app folder."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile
from wallpaper_catalog import CATALOG, BY_ID

BUNDLE = Path(__file__).resolve().parent/'addons'/'wallpaper-plus.rpkaddon'
MAX_PACK = 350*1024*1024

class WallpaperStore:
    def __init__(self,root):
        self.root=Path(root).resolve();self.path=self.root/'wallpaper-plus'

    def installed(self):
        try:
            if self.path.is_symlink():return False
            manifest=json.loads((self.path/'manifest.json').read_text(encoding='utf-8'))
            return manifest.get('id')=='wallpaper-plus' and manifest.get('version')==1 and set(manifest.get('files',{}))==self.expected_files() and all((self.path/name).is_file() for name in self.expected_files())
        except (OSError,ValueError):return False

    @staticmethod
    def expected_files():
        return {f'{folder}/{item["id"]}.webp' for item in CATALOG for folder in ('images','thumbs')}

    def _owned(self,path):
        path=Path(path)
        if path.is_symlink() or path.is_junction() or path.resolve().parent!=self.root:raise ValueError('Unsicherer Add-on-Pfad.')
        return path

    def install(self,bundle=BUNDLE,progress=lambda n:None,cancel=lambda:False):
        self.root.mkdir(parents=True,exist_ok=True)
        self._owned(self.path)
        stage=Path(tempfile.mkdtemp(prefix='wallpaper-install-',dir=self.root));backup=None
        try:
            with zipfile.ZipFile(bundle) as archive:
                entries=archive.infolist();names=[x.filename for x in entries]
                expected=self.expected_files()
                if len(names)!=len(set(names)) or set(names)!=expected|{'manifest.json'}:raise ValueError('Das Wallpaper-Paket ist unvollständig oder enthält fremde Dateien.')
                if sum(x.file_size for x in entries)>MAX_PACK or any(x.file_size>12*1024*1024 for x in entries):raise ValueError('Wallpaper-Paket ist zu groß.')
                raw=archive.read('manifest.json');manifest=json.loads(raw)
                if manifest.get('id')!='wallpaper-plus' or manifest.get('version')!=1 or set(manifest.get('files',{}))!=expected:raise ValueError('Wallpaper-Paket wird nicht unterstützt.')
                from PIL import Image
                import io
                for index,name in enumerate(sorted(expected)):
                    if cancel():raise InterruptedError('Installation abgebrochen.')
                    data=archive.read(name)
                    if hashlib.sha256(data).hexdigest()!=manifest['files'][name]:raise ValueError('Wallpaper-Paket ist beschädigt.')
                    with Image.open(io.BytesIO(data)) as im:
                        if im.format!='WEBP' or im.width*im.height>16_000_000 or min(im.size)<1:raise ValueError('Ungültiges Wallpaper-Bild.')
                        im.verify()
                    target=stage/name;target.parent.mkdir(exist_ok=True);target.write_bytes(data)
                    progress(round((index+1)*100/len(expected)))
                (stage/'manifest.json').write_bytes(raw)
            if cancel():raise InterruptedError('Installation abgebrochen.')
            if self.path.exists():
                backup=Path(tempfile.mkdtemp(prefix='wallpaper-backup-',dir=self.root));backup.rmdir();os.replace(self.path,backup)
            try:os.replace(stage,self.path)
            except Exception:
                if backup:os.replace(backup,self.path);backup=None
                raise
            if backup:shutil.rmtree(self._owned(backup));backup=None
        finally:
            if stage.exists():shutil.rmtree(self._owned(stage))

    def uninstall(self):
        if self.path.exists():shutil.rmtree(self._owned(self.path))

    def image(self,key,plus=False,thumbnail=False):
        item=BY_ID.get(key)
        if not item or (item['plus'] and not plus and not thumbnail):return None
        path=self.path/('thumbs' if thumbnail else 'images')/(key+'.webp')
        if self.path.is_symlink() or self.path.is_junction() or path.is_symlink() or not path.is_file() or path.resolve().parent!=(self.path/('thumbs' if thumbnail else 'images')).absolute():return None
        return path
