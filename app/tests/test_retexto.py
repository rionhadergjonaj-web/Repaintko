import unittest,tempfile,os
from pathlib import Path
from unittest.mock import patch
from text_files import read_text,write_text
from PySide6.QtWidgets import QApplication,QMessageBox
from PySide6.QtGui import QTextCursor

class TextTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def test_encoding_and_newlines_roundtrip(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'text.txt'
   for enc in ('utf-8','utf-8-sig','utf-16-le','utf-16-be','cp1252'):
    for eol in ('\n','\r\n','\r'):
     stamp=write_text(p,'Grüße\nZeile 2\n',enc,eol);text,actual,ending,fingerprint=read_text(p);self.assertEqual((text,actual,ending,fingerprint),('Grüße\nZeile 2\n',enc,eol,stamp))
 def test_external_changes_are_protected(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'test.txt';stamp=write_text(p,'first','utf-8','\n');p.write_text('external')
   with self.assertRaises(FileExistsError):write_text(p,'lost','utf-8','\n',stamp)
   self.assertEqual(p.read_text(),'external')
 def test_encoding_failure_keeps_original(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'test.txt';stamp=write_text(p,'first','utf-8','\n')
   with self.assertRaises(UnicodeEncodeError):write_text(p,'😀','cp1252','\n',stamp)
   self.assertEqual(p.read_text(),'first')
 def test_binary_rejected(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'data';p.write_bytes(b'abc\0def')
   with self.assertRaises(ValueError):read_text(p)
 def test_tabs_save_cancel_and_markdown(self):
  from retexto import ReTexto
  with tempfile.TemporaryDirectory() as folder:
   w=ReTexto();w.show();tab=w.current();tab.editor.insertPlainText('# Titel\nText');path=Path(folder)/'hello.md'
   with patch('retexto.QFileDialog.getSaveFileName',return_value=(str(path),'')):self.assertTrue(w.save())
   self.assertEqual(read_text(path)[0],'# Titel\nText');tab.editor.insertPlainText('!')
   with patch('retexto.QMessageBox.question',return_value=QMessageBox.StandardButton.Cancel):self.assertFalse(w.confirm_all());w.close_tab();self.assertEqual(w.tabs.count(),1)
   w.new();w.open([path]);self.assertIs(w.current(),tab);w.markdown.setChecked(True);w.toggle_preview();self.assertIn('Titel',tab.preview.toPlainText());w.close()
 def test_search_wrap_and_unicode(self):
  from retexto import ReTexto
  w=ReTexto();w.current().editor.setPlainText('Äpfel 😀 Äpfel');w.search_text='Äpfel';self.assertTrue(w.find_next());self.assertTrue(w.find_next());self.assertTrue(w.find_next());self.assertEqual(w.current().editor.textCursor().selectionStart(),0);w.close()
 def test_ai_result_is_explicit_and_undoable(self):
  from retexto import ReTexto
  from text_ai import TextAI
  w=ReTexto();e=w.current().editor;e.setPlainText('Hallo Welt');c=e.textCursor();c.setPosition(6);c.movePosition(QTextCursor.MoveOperation.End,QTextCursor.MoveMode.KeepAnchor);e.setTextCursor(c);d=TextAI(e,w);d.preview.setPlainText('ReTexto');self.assertEqual(e.toPlainText(),'Hallo Welt');d.replace();self.assertEqual(e.toPlainText(),'Hallo ReTexto');e.undo();self.assertEqual(e.toPlainText(),'Hallo Welt');w.close()
 def test_embedded_mode_switch_retains_text(self):
  from browser_mode import Browser
  from browser_store import BrowserStore
  from qt_app import Repainko
  with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'REPAINKO_SETTINGS_PATH':str(Path(folder)/'prefs.ini')}),patch.object(Browser,'check'),patch('browser_mode.BrowserStore',side_effect=lambda unused:BrowserStore(folder)):
   w=Repainko();w.show();doc=w.doc;w.open_retexto();self.assertTrue(w.retexto_active);self.assertIs(w.retexto.window(),w);w.retexto.current().editor.insertPlainText('Bleibt erhalten');w.open_help();w.return_from_help();self.assertTrue(w.retexto_active);self.assertEqual(w.retexto.current().editor.toPlainText(),'Bleibt erhalten');w.leave_video_editor();self.assertIs(w.doc,doc)
   with patch('retexto.QMessageBox.question',return_value=QMessageBox.StandardButton.Cancel):w.close();self.assertTrue(w.isVisible())
   with patch('retexto.QMessageBox.question',return_value=QMessageBox.StandardButton.Discard):w.close()
