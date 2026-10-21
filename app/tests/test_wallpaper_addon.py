import io,json,hashlib,tempfile,unittest,zipfile
from pathlib import Path
from PIL import Image
from wallpaper_catalog import CATALOG
from wallpaper_addon import WallpaperStore

def pack(path,extra=None,bad=False):
    stream=io.BytesIO();Image.new('RGB',(32,18),'red').save(stream,'WEBP');data=stream.getvalue()
    files={name:hashlib.sha256(data).hexdigest() for name in WallpaperStore.expected_files()}
    if bad:files[next(iter(files))]='0'*64
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('manifest.json',json.dumps(dict(id='wallpaper-plus',version=1,files=files)))
        for name in files:z.writestr(name,data)
        if extra:z.writestr(extra,'no executable addons')

class WallpaperTests(unittest.TestCase):
    def test_catalog_split_and_unique_ids(self):
        self.assertEqual(len({x['id'] for x in CATALOG}),101)
        self.assertEqual([sum(x['category']==c for x in CATALOG) for c in ('color','anime','realistic')],[20,40,41])
        self.assertEqual(sum(x['plus'] for x in CATALOG),81)

    def test_install_license_gate_repair_uninstall(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'pack.zip';pack(p);s=WallpaperStore(root/'addons');self.assertFalse(s.installed());s.install(p);self.assertTrue(s.installed())
            self.assertIsNotNone(s.image('color_mint'));self.assertIsNone(s.image('anime_alpine_dawn'));self.assertIsNotNone(s.image('anime_alpine_dawn',plus=True));self.assertIsNotNone(s.image('anime_alpine_dawn',thumbnail=True))
            self.assertIsNone(s.image('../outside'));s.install(p);self.assertTrue(s.installed());s.uninstall();self.assertFalse(s.installed());self.assertTrue(p.exists())

    def test_bad_package_and_cancel_preserve_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'pack.zip';pack(p);s=WallpaperStore(root/'addons');s.install(p)
            for extra in ('../escape.py','plugin.py'):
                pack(p,extra=extra)
                with self.assertRaises(ValueError):s.install(p)
                self.assertTrue(s.installed());self.assertFalse((root/'escape.py').exists())
            pack(p,bad=True)
            with self.assertRaises(ValueError):s.install(p)
            pack(p)
            with self.assertRaises(InterruptedError):s.install(p,cancel=lambda:True)
            self.assertTrue(s.installed());self.assertEqual([p.name for p in s.root.iterdir()],['wallpaper-plus'])

    def test_opacity_and_paint_cache_do_not_touch_document(self):
        from PySide6.QtWidgets import QApplication
        from designs import DesignScrollArea
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'red.png';Image.new('RGB',(40,20),'red').save(p)
            view=DesignScrollArea();view.resize(200,120);view.set_design('test','#000000');view.show();view.set_wallpaper(p,100);app.processEvents()
            self.assertGreater(view.viewport().grab().toImage().pixelColor(20,20).red(),240)
            cache=view.wallpaper_scaled.cacheKey();view.viewport().update();app.processEvents();self.assertEqual(cache,view.wallpaper_scaled.cacheKey())
            view.set_wallpaper(p,50);app.processEvents();self.assertTrue(120<=view.viewport().grab().toImage().pixelColor(20,20).red()<=135)
            view.set_wallpaper(p,0);app.processEvents();self.assertLess(view.viewport().grab().toImage().pixelColor(20,20).red(),5)
            view.close()

    def test_in_app_install_selection_opacity_and_uninstall(self):
        import os
        from unittest.mock import patch
        from PySide6.QtWidgets import QApplication,QMessageBox
        from PySide6.QtCore import Qt
        from qt_app import Repainko
        from addon_ui import AddonDialog
        from browser_mode import Browser
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bundle=root/'pack.zip';pack(bundle)
            with patch.dict(os.environ,{'REPAINKO_SETTINGS_PATH':str(root/'settings.ini')}),patch.object(Browser,'check'),patch('addon_ui.BUNDLE',bundle):
                window=Repainko();window.wallpapers=WallpaperStore(root/'addons');before=window.doc.image.tobytes();dialog=AddonDialog(window)
                self.assertEqual(dialog.gallery.count(),0);dialog.install();self.assertEqual(dialog.gallery.count(),101)
                dialog.gallery.setCurrentRow(0);dialog.apply();self.assertFalse(window.scroll.wallpaper.isNull())
                dialog.opacity.setValue(26);self.assertEqual(window.preferences.value('wallpaper/opacity',type=int),26);self.assertEqual(window.scroll.wallpaper_opacity,.26)
                dialog.category.setCurrentIndex(1);self.assertEqual(dialog.gallery.count(),20)
                dialog.category.setCurrentIndex(2);dialog.gallery.setCurrentRow(0)
                previous=window.preferences.value('wallpaper/selected')
                with patch.object(QMessageBox,'information') as message:dialog.apply();self.assertTrue(message.called)
                self.assertEqual(window.preferences.value('wallpaper/selected'),previous)
                self.assertEqual(window.doc.image.tobytes(),before)
                dialog.uninstall();self.assertFalse(window.wallpapers.installed());self.assertTrue(window.scroll.wallpaper.isNull())
                window.open_help();self.assertTrue(window.addons_action.isEnabled());self.assertTrue(window.addons_action.isVisible());window.return_from_help();window.close()
