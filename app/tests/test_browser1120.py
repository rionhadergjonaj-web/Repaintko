import unittest,tempfile,json,os
from pathlib import Path
from unittest.mock import patch
from browser_store import BrowserStore,origin,crypt
from browser_mode import Browser,destination,fill_script
class StorageTests(unittest.TestCase):
 def test_dpapi_roundtrip_and_deletion(self):
  with tempfile.TemporaryDirectory() as folder:
   s=BrowserStore(folder);s.save('https://example.com/login','demo','test-password-only');data=(Path(folder)/'passwords.dpapi').read_bytes();self.assertNotIn(b'test-password-only',data);self.assertNotIn(b'demo',data)
   s2=BrowserStore(folder);self.assertEqual(s2.credentials()[0]['password'],'test-password-only');s2.save('https://example.com:443','demo','replacement');self.assertEqual(len(s2.credentials()),1);s2.delete('https://example.com','demo');self.assertEqual(s2.credentials(),[])
 def test_failed_encryption_never_writes_plaintext(self):
  with tempfile.TemporaryDirectory() as folder:
   s=BrowserStore(folder)
   with patch('browser_store.crypt',side_effect=OSError('test')):
    with self.assertRaises(OSError):s.save('https://example.com','a','secret')
   self.assertFalse((Path(folder)/'passwords.dpapi').exists())
 def test_origin_is_exact(self):
  self.assertEqual(origin('https://EXAMPLE.com:443/path'),'https://example.com');self.assertNotEqual(origin('https://example.com:444'),origin('https://example.com'))
  for url in ['http://example.com','file:///x','https://user:pass@example.com']:
   with self.assertRaises(ValueError):origin(url)
 def test_history_reload_search_url_and_clear(self):
  with tempfile.TemporaryDirectory() as folder:
   s=BrowserStore(folder);s.visit(destination('Katze & Hund').toString(),'Suche');s.visit('https://u:p@example.com/path#secret','Titel');rows=BrowserStore(folder).history();self.assertEqual(rows[0]['url'],'https://example.com/path');self.assertIn('q=Katze',rows[1]['url']);s.clear_history();self.assertEqual(s.history(),[])
 def test_script_checks_origin_and_escapes(self):
  script=fill_script('https://example.com','x','";alert(1)//');self.assertIn('location.origin!==d.site',script);self.assertIn('\\";alert(1)//',script);self.assertNotIn('.submit(',script)
class BrowserUITests(unittest.TestCase):
 def test_startup_check_hidden_without_webengine_and_help_return(self):
  from PySide6.QtWidgets import QApplication
  from qt_app import Repainko
  app=QApplication.instance() or QApplication([])
  with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'REPAINKO_SETTINGS_PATH':str(Path(folder)/'settings.ini')}),patch.object(Browser,'check') as check,patch('browser_mode.BrowserStore',side_effect=lambda unused:BrowserStore(folder)):
   w=Repainko();app.processEvents();self.assertIsNotNone(w.browser);self.assertTrue(check.called);self.assertTrue(w.browser.timer.isActive());self.assertIsNone(w.browser.profile);w.browser.set_online(True);self.assertIsNone(w.browser.profile)
   w.browser.set_online(False);w.show();w.open_browser();app.processEvents();self.assertTrue(w.browser_active);w.open_help();w.return_from_help();self.assertTrue(w.browser_active);w.close();self.assertFalse(w.browser.timer.isActive())
class TabTests(unittest.TestCase):
 def test_tab_navigation_and_profile_configuration(self):
  import sys,types
  from PySide6.QtWidgets import QApplication,QWidget
  from PySide6.QtCore import QObject,Signal,QUrl
  class Profile(QObject):
   downloadRequested=Signal(object)
   class PersistentCookiesPolicy:ForcePersistentCookies=2
   def __init__(self,name,parent):super().__init__(parent);self.name=name
   def setPersistentStoragePath(self,v):self.storage=v
   def setCachePath(self,v):self.cache=v
   def setPersistentCookiesPolicy(self,v):self.cookies=v
  class Page(QObject):
   newWindowRequested=Signal(object)
   def __init__(self,profile,parent):super().__init__(parent)
  class View(QWidget):
   urlChanged=Signal(object);titleChanged=Signal(str);loadFinished=Signal(bool);loadProgress=Signal(int)
   def setPage(self,p):self.p=p
   def setUrl(self,u):self.u=u;self.urlChanged.emit(u)
   def url(self):return getattr(self,'u',QUrl())
   def stop(self):pass
   def history(self):return self
   def canGoBack(self):return False
   def canGoForward(self):return False
  app=QApplication.instance() or QApplication([])
  with tempfile.TemporaryDirectory() as folder,patch.dict(sys.modules,{'PySide6.QtWebEngineWidgets':types.SimpleNamespace(QWebEngineView=View),'PySide6.QtWebEngineCore':types.SimpleNamespace(QWebEnginePage=Page,QWebEngineProfile=Profile)}),patch.object(Browser,'check'):
   b=Browser(storage=folder);b.online=True;b.new_tab('https://example.com');b.new_tab('https://example.org');self.assertEqual(b.tabs.count(),2);self.assertEqual(b.view.url().host(),'example.org');b.cycle(-1);self.assertEqual(b.view.url().host(),'example.com');self.assertEqual(b.profile.cookies,2);self.assertEqual(b.profile.name,'ReBrowko');self.assertTrue(b.profile.storage.endswith('profile'));self.assertFalse(b.view.p.acceptNavigationRequest(QUrl('file:///secret'),None,True));b.close_tab(0);self.assertEqual(b.tabs.count(),1);b.close_tab(0);self.assertIsNone(b.view);b.shutdown()
