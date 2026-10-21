"""Windows native spell checking, isolated on a COM-initialized worker thread."""
import ctypes as c,uuid
from PySide6.QtCore import QThread,Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPushButton,QListWidget,QLineEdit,QMessageBox

def check_spelling(text,language):
    ole=c.OleDLL('ole32');ole.CoInitializeEx.argtypes=[c.c_void_p,c.c_uint];ole.CoInitializeEx.restype=c.c_long
    ole.CoCreateInstance.argtypes=[c.c_void_p,c.c_void_p,c.c_uint,c.c_void_p,c.POINTER(c.c_void_p)];ole.CoCreateInstance.restype=c.c_long
    ole.CoTaskMemFree.argtypes=[c.c_void_p]
    def call(obj,index,types=(),args=()):
        v=c.cast(obj,c.POINTER(c.POINTER(c.c_void_p))).contents
        return c.WINFUNCTYPE(c.c_long,c.c_void_p,*types)(v[index])(obj,*args)
    def release(obj):
        if obj:call(obj,2)
    def ok(hr):
        if hr<0:raise OSError(f'Windows-Rechtschreibung: 0x{hr & 0xffffffff:08X}')
    def guid(value):return c.create_string_buffer(uuid.UUID(value).bytes_le)
    init=ole.CoInitializeEx(None,0);ok(init);factory=c.c_void_p();checker=c.c_void_p();errors=c.c_void_p()
    try:
        ok(ole.CoCreateInstance(guid('7AB36653-1796-484B-BDFA-E74F1DB7C1DC'),None,1,guid('8E018A9D-2415-4677-BF08-794EA61F94BB'),c.byref(factory)))
        supported=c.c_int();ok(call(factory,4,(c.c_wchar_p,c.POINTER(c.c_int)),(language,c.byref(supported))))
        if not supported.value:raise ValueError(f'Das Windows-Wörterbuch für {language} fehlt. Installiere es unter Windows → Einstellungen → Zeit und Sprache → Sprache.')
        ok(call(factory,5,(c.c_wchar_p,c.POINTER(c.c_void_p)),(language,c.byref(checker))))
        ok(call(checker,4,(c.c_wchar_p,c.POINTER(c.c_void_p)),(text,c.byref(errors))))
        output=[];raw=text.encode('utf-16-le')
        while len(output)<500:
            error=c.c_void_p();hr=call(errors,3,(c.POINTER(c.c_void_p),),(c.byref(error),));ok(hr)
            if not error:break
            try:
                start=c.c_uint();length=c.c_uint();action=c.c_int();replacement=c.c_void_p()
                ok(call(error,3,(c.POINTER(c.c_uint),),(c.byref(start),)));ok(call(error,4,(c.POINTER(c.c_uint),),(c.byref(length),)));ok(call(error,5,(c.POINTER(c.c_int),),(c.byref(action),)))
                word=raw[start.value*2:(start.value+length.value)*2].decode('utf-16-le');suggestions=[]
                if action.value==2:
                    ok(call(error,6,(c.POINTER(c.c_void_p),),(c.byref(replacement),)))
                    if replacement:suggestions.append(c.wstring_at(replacement));ole.CoTaskMemFree(replacement)
                elif action.value==3:suggestions.append('')
                else:
                    enum=c.c_void_p();ok(call(checker,5,(c.c_wchar_p,c.POINTER(c.c_void_p)),(word,c.byref(enum))))
                    try:
                        for _ in range(8):
                            value=c.c_void_p();fetched=c.c_uint();hr=call(enum,3,(c.c_uint,c.POINTER(c.c_void_p),c.POINTER(c.c_uint)),(1,c.byref(value),c.byref(fetched)));ok(hr)
                            if not fetched.value:break
                            suggestions.append(c.wstring_at(value));ole.CoTaskMemFree(value)
                    finally:release(enum)
                output.append((start.value,length.value,word,suggestions))
            finally:release(error)
        return output
    finally:release(errors);release(checker);release(factory);ole.CoUninitialize()

class SpellWorker(QThread):
    ready=Signal(object);failed=Signal(str)
    def __init__(self,text,language,parent):super().__init__(parent);self.text=text;self.language=language
    def run(self):
        try:self.ready.emit(check_spelling(self.text,self.language))
        except Exception as exc:self.failed.emit(str(exc))

class SpellDialog(QDialog):
    def __init__(self,editor,parent):
        super().__init__(parent);self.editor=editor;self.worker=None;self.snapshot='';self.items=[];self.setWindowTitle('Rechtschreibung');self.resize(580,420)
        layout=QVBoxLayout(self);self.info=QLabel('Prüft lokal mit dem installierten Windows-Wörterbuch.');self.info.setWordWrap(True);layout.addWidget(self.info);row=QHBoxLayout();self.language=QComboBox();self.language.addItems(['de-DE','de-CH','de-AT','en-US','en-GB','fr-FR','it-IT']);row.addWidget(self.language);self.start=QPushButton('Text prüfen');self.start.clicked.connect(self.check);row.addWidget(self.start);layout.addLayout(row);self.results=QListWidget();layout.addWidget(self.results);self.results.currentRowChanged.connect(self.selected);self.suggestions=QComboBox();self.suggestions.setEditable(True);layout.addWidget(self.suggestions);self.apply=QPushButton('Diese Stelle korrigieren und neu prüfen');self.apply.clicked.connect(self.replace);self.apply.setEnabled(False);layout.addWidget(self.apply)
    def check(self):
        if self.worker and self.worker.isRunning():return
        self.snapshot=self.editor.toPlainText()
        if len(self.snapshot)>200000:self.info.setText('Bitte höchstens 200.000 Zeichen auf einmal prüfen.');return
        self.start.setEnabled(False);self.apply.setEnabled(False);self.info.setText('Prüfe …');self.worker=SpellWorker(self.snapshot,self.language.currentText(),self);self.worker.ready.connect(self.ready);self.worker.failed.connect(self.failed);self.worker.start()
    def failed(self,message):self.start.setEnabled(True);self.info.setText(message)
    def ready(self,items):
        self.start.setEnabled(True);self.items=items;self.results.clear();self.results.addItems([f'{word} · Position {start+1}' for start,length,word,suggestions in items]);self.info.setText(f'{len(items)} auffällige Stellen (maximal 500 pro Prüfung).');self.results.setCurrentRow(0)
    def selected(self,index):
        self.suggestions.clear();self.apply.setEnabled(0<=index<len(self.items))
        if 0<=index<len(self.items):self.suggestions.addItems(self.items[index][3])
    def replace(self):
        i=self.results.currentRow()
        if i<0:return
        if self.editor.toPlainText()!=self.snapshot:self.info.setText('Der Text hat sich geändert. Bitte erneut prüfen.');return
        start,length,_,_=self.items[i];cursor=self.editor.textCursor();cursor.setPosition(start);cursor.setPosition(start+length,QTextCursor.MoveMode.KeepAnchor);cursor.insertText(self.suggestions.currentText());self.editor.setTextCursor(cursor);self.check()
    def reject(self):
        if self.worker and self.worker.isRunning():self.info.setText('Die Prüfung wird gleich beendet. Bitte kurz warten.');return
        super().reject()
