import unittest,tempfile,os
from pathlib import Path
from unittest.mock import patch
from notebook_store import NoteStore
class NoteTests(unittest.TestCase):
 def test_limit_persistence_search_and_delete(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'notes.db';s=NoteStore(path);first=s.create();s.save(first['id'],'Einkauf','Äpfel\nMilch',0)
   for i in range(99):s.create()
   with self.assertRaises(ValueError):s.create()
   self.assertEqual(s.count(),100);s.close();s=NoteStore(path);self.assertEqual(s.list('äPFEL')[0]['title'],'Einkauf');n=s.get(first['id']);s.delete(n['id'],n['revision']);self.assertEqual(s.count(),99);s.create();self.assertEqual(s.count(),100);s.close()
 def test_concurrent_updates_do_not_overwrite(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'notes.db';a=NoteStore(path);b=NoteStore(path);n=a.create();a.save(n['id'],'A','new',0)
   with self.assertRaises(ValueError):b.save(n['id'],'B','lost',0)
   self.assertEqual(a.get(n['id'])['body'],'new');a.close();b.close()
 def test_edit_save_switch_and_failure(self):
  from PySide6.QtWidgets import QApplication
  from notebook import Notebook
  app=QApplication.instance() or QApplication([])
  with tempfile.TemporaryDirectory() as folder:
   w=Notebook(path=Path(folder)/'n.db');w.new_note();key=w.current['id'];w.title.setText('Test');w.editor.setPlainText('Mehrzeilig\nText');self.assertTrue(w.dirty);self.assertTrue(w.flush());w.new_note();self.assertEqual(w.store.get(key)['body'],'Mehrzeilig\nText');w.editor.setPlainText('Nicht verlieren')
   with patch.object(w.store,'save',side_effect=OSError('voll')):self.assertFalse(w.flush());self.assertTrue(w.dirty);self.assertEqual(w.editor.toPlainText(),'Nicht verlieren')
   self.assertTrue(w.flush());w.timer.stop();w.store.close();w.close()
 def test_embedded_return_and_failed_close(self):
  from PySide6.QtWidgets import QApplication
  from notebook import Notebook
  from browser_mode import Browser
  from browser_store import BrowserStore
  from qt_app import Repainko
  app=QApplication.instance() or QApplication([])
  with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'REPAINKO_SETTINGS_PATH':str(Path(folder)/'prefs.ini')}),patch.object(Browser,'check'),patch('browser_mode.BrowserStore',side_effect=lambda unused:BrowserStore(folder)),patch('notebook.NoteStore',side_effect=lambda unused:NoteStore(Path(folder)/'n.db')):
   w=Repainko();w.show();doc=w.doc;w.open_notebook();n=w.notebook;n.new_note();n.editor.setPlainText('bleibt');w.open_help();self.assertTrue(w.help_active);w.return_from_help();self.assertTrue(w.notebook_active);self.assertEqual(n.editor.toPlainText(),'bleibt');self.assertIs(n.window(),w)
   n.editor.setPlainText('weiter')
   with patch.object(n.store,'save',side_effect=OSError('test')):
    w.open_browser();self.assertTrue(w.notebook_active);self.assertFalse(w.close())
   self.assertTrue(n.flush());w.leave_video_editor();self.assertIs(w.doc,doc);w.close();n.store.close()
