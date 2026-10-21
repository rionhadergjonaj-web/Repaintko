"""Embedded, offline notebook. Notes never require export or a file dialog."""
from pathlib import Path
from PySide6.QtCore import Qt,QTimer,Signal,QStandardPaths
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QSplitter,QPushButton,QLabel,QLineEdit,QPlainTextEdit,QListWidget,QListWidgetItem,QMessageBox
from notebook_store import NoteStore
class Notebook(QWidget):
    returnRequested=Signal()
    def __init__(self,parent=None,path=None):
        super().__init__(parent);self.store=NoteStore(path or Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))/'Notizbuch'/'notizen.sqlite3');self.current=None;self.dirty=False;self.loading=False
        root=QVBoxLayout(self);row=QHBoxLayout();root.addLayout(row)
        self.button(row,'← Bild / GIF',self.returnRequested.emit);self.new_button=self.button(row,'+ Neue Notiz',self.new_note);self.delete_button=self.button(row,'Löschen',self.delete_note);self.button(row,'Speichern',self.flush);self.button(row,'Neu laden',self.reload);row.addStretch();self.counter=QLabel();row.addWidget(self.counter)
        split=QSplitter();root.addWidget(split,1);sidebar=QWidget();side=QVBoxLayout(sidebar);side.setContentsMargins(0,0,0,0);self.search=QLineEdit();self.search.setPlaceholderText('Notizen durchsuchen …');self.search.setClearButtonEnabled(True);side.addWidget(self.search);self.notes=QListWidget();side.addWidget(self.notes);split.addWidget(sidebar)
        paper=QWidget();body=QVBoxLayout(paper);body.setContentsMargins(8,0,0,0);self.title=QLineEdit();self.title.setMaxLength(200);self.title.setPlaceholderText('Titel der Notiz');body.addWidget(self.title);self.editor=QPlainTextEdit();self.editor.setPlaceholderText('Schreibe hier deine Notiz …\nÄnderungen werden automatisch gespeichert.');body.addWidget(self.editor);split.addWidget(paper);split.setSizes([260,740]);self.status=QLabel('Deine Notizen bleiben lokal in Repaintko. Kein Export nötig.');self.status.setWordWrap(True);root.addWidget(self.status)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(700);self.timer.timeout.connect(self.flush)
        self.title.textEdited.connect(self.edited);self.editor.textChanged.connect(self.edited);self.search.textChanged.connect(self.refresh);self.notes.currentItemChanged.connect(self.select)
        self.refresh();self.enable_editor(False)
        if self.notes.count():self.notes.setCurrentRow(0)
    def button(self,row,label,fn):
        button=QPushButton(label);button.clicked.connect(lambda:fn());row.addWidget(button);return button
    def enable_editor(self,on):self.title.setEnabled(on);self.editor.setEnabled(on);self.delete_button.setEnabled(on)
    def refresh(self,*args):
        key=self.current['id'] if self.current else None
        self.notes.blockSignals(True);self.notes.clear()
        for note in self.store.list(self.search.text()):
            item=QListWidgetItem(note['title']);item.setData(Qt.ItemDataRole.UserRole,note['id']);item.setToolTip(note['body'][:160]);self.notes.addItem(item)
            if note['id']==key:self.notes.setCurrentItem(item)
        self.notes.blockSignals(False);count=self.store.count();self.counter.setText(f'{count} / 100 Notizen');self.new_button.setEnabled(count<100)
    def edited(self,*args):
        if self.loading or self.current is None:return
        self.dirty=True;self.status.setText('Ungespeicherte Änderungen …');self.timer.start()
    def flush(self):
        self.timer.stop()
        if not self.dirty or self.current is None:return True
        try:
            self.current=self.store.save(self.current['id'],self.title.text(),self.editor.toPlainText(),self.current['revision']);self.dirty=False;self.refresh();self.status.setText('Automatisch gespeichert · lokal in Repaintko');return True
        except Exception as exc:self.status.setText('Nicht gespeichert: '+str(exc)+'  · „Speichern“ versucht es erneut.');return False
    def load(self,note):
        self.loading=True;self.current=note;self.title.setText(note['title'] if note else '');self.editor.setPlainText(note['body'] if note else '');self.dirty=False;self.loading=False;self.enable_editor(note is not None);self.status.setText('Lokal gespeichert · Änderungen werden automatisch übernommen.');self.refresh()
    def select(self,item,previous):
        if item is None:return
        key=item.data(Qt.ItemDataRole.UserRole)
        if self.current and key==self.current['id']:return
        if not self.flush():self.refresh();return
        try:self.load(self.store.get(key))
        except Exception as exc:self.status.setText(str(exc));self.refresh()
    def new_note(self):
        if not self.flush():return
        try:
            note=self.store.create();self.search.clear();self.load(note);self.title.setFocus();self.title.selectAll()
        except Exception as exc:QMessageBox.warning(self,'Notizbuch',str(exc));self.refresh()
    def delete_note(self):
        if self.current is None or not self.flush():return
        if QMessageBox.question(self,'Notiz löschen','Diese Notiz dauerhaft löschen?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        try:self.store.delete(self.current['id'],self.current['revision']);self.load(None)
        except Exception as exc:self.status.setText(str(exc));return
        if self.notes.count():self.notes.setCurrentRow(0)
    def reload(self):
        if self.dirty and QMessageBox.question(self,'Neu laden','Ungespeicherte Änderungen verwerfen und die gespeicherte Notiz laden?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        self.timer.stop()
        try:self.load(self.store.get(self.current['id']) if self.current else None)
        except ValueError:self.load(None)
        except Exception as exc:self.status.setText(str(exc))
    def showEvent(self,event):
        super().showEvent(event)
        if not self.dirty:self.refresh()
