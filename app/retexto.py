"""Embedded plain text editor; each tab owns its file metadata."""
from pathlib import Path
from datetime import datetime
import re
from PySide6.QtCore import Qt,Signal,QTimer
from PySide6.QtGui import QAction,QKeySequence,QTextCursor,QTextDocument,QFont
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QMenuBar,QTabWidget,QPlainTextEdit,QTextBrowser,QSplitter,QLabel,QFileDialog,QMessageBox,QInputDialog,QFontDialog,QDialog,QLineEdit,QPushButton,QCheckBox,QComboBox)
from text_files import read_text,write_text,ENCODINGS

class Preview(QTextBrowser):
    def loadResource(self,kind,url):return None  # Never fetch resources referenced by an untrusted document.

class TextTab(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);self.path=None;self.encoding='utf-8';self.eol='\r\n';self.fingerprint=None
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);split=QSplitter();layout.addWidget(split)
        self.editor=QPlainTextEdit();self.editor.setFont(QFont('Consolas',11));self.preview=Preview();self.preview.setOpenLinks(False);split.addWidget(self.editor);split.addWidget(self.preview);self.preview.hide()
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(250);self.timer.timeout.connect(self.render);self.editor.textChanged.connect(self.timer.start)
    def render(self):
        if self.preview.isVisible():self.preview.setMarkdown(self.editor.toPlainText())

class ReTexto(QWidget):
    returnRequested=Signal()
    def __init__(self,parent=None):
        super().__init__(parent);self.setAcceptDrops(True);self.search_text='';self.search_flags=QTextDocument.FindFlag(0);self.printer=None;self.ai_dialog=None
        layout=QVBoxLayout(self);layout.setContentsMargins(8,8,8,8)
        heading=QHBoxLayout();back=QPushButton('← Zurück zum Bild');back.clicked.connect(self.returnRequested);heading.addWidget(back);heading.addWidget(QLabel('ReTexto · Texteditor'));heading.addStretch();layout.addLayout(heading)
        self.menus=QMenuBar();layout.addWidget(self.menus)
        file=self.menus.addMenu('Datei');edit=self.menus.addMenu('Bearbeiten');view=self.menus.addMenu('Ansicht');extras=self.menus.addMenu('Extras')
        self.action(file,'Neu',self.new,'Ctrl+N');self.action(file,'Öffnen …',self.open,'Ctrl+O');self.action(file,'Speichern',self.save,'Ctrl+S');self.action(file,'Speichern unter …',lambda:self.save(as_new=True),'Ctrl+Shift+S');self.action(file,'Alle speichern',self.save_all);self.action(file,'Tab schließen',self.close_tab,'Ctrl+W');file.addSeparator();self.action(file,'Seite einrichten …',self.page_setup);self.action(file,'Drucken …',self.print_text,'Ctrl+P')
        for label,method,key in [('Rückgängig','undo','Ctrl+Z'),('Wiederholen','redo','Ctrl+Y'),('Ausschneiden','cut','Ctrl+X'),('Kopieren','copy','Ctrl+C'),('Einfügen','paste','Ctrl+V'),('Alles auswählen','selectAll','Ctrl+A')]:
            self.action(edit,label,lambda m=method:getattr(self.current().editor,m)(),key)
        edit.addSeparator();self.action(edit,'Suchen …',self.find_dialog,'Ctrl+F');self.action(edit,'Ersetzen …',lambda:self.find_dialog(True),'Ctrl+H');self.action(edit,'Weitersuchen',self.find_next,'F3');self.action(edit,'Rückwärts suchen',lambda:self.find_next(True),'Shift+F3');self.action(edit,'Gehe zu Zeile …',self.goto,'Ctrl+G');self.action(edit,'Uhrzeit / Datum',lambda:self.current().editor.insertPlainText(datetime.now().strftime('%H:%M %d.%m.%Y')),'F5')
        self.wrap=self.action(view,'Zeilenumbruch',self.toggle_wrap,check=True);self.wrap.setChecked(True)
        self.markdown=self.action(view,'Markdown-Vorschau',self.toggle_preview,check=True)
        self.action(view,'Schriftart …',self.font);self.action(view,'Vergrößern',lambda:self.current().editor.zoomIn(),'Ctrl++');self.action(view,'Verkleinern',lambda:self.current().editor.zoomOut(),'Ctrl+-');self.action(view,'Standardgröße',lambda:self.current().editor.setFont(QFont('Consolas',11)),'Ctrl+0')
        fmt=self.menus.addMenu('Markdown')
        for label,left,right in [('Fett','**','**'),('Kursiv','*','*'),('Überschrift','# ',''),('Liste','- ',''),('Code','`','`'),('Link','[','](https://)')]:self.action(fmt,label,lambda a=left,b=right:self.insert_markup(a,b))
        self.action(extras,'Rechtschreibung prüfen …',self.spellcheck);self.action(extras,'Lokale KI-Texthilfe …',self.ai)
        self.tabs=QTabWidget();self.tabs.setTabsClosable(True);self.tabs.setMovable(True);self.tabs.tabCloseRequested.connect(self.close_tab);self.tabs.currentChanged.connect(self.changed);layout.addWidget(self.tabs,1)
        bottom=QHBoxLayout();self.status=QLabel();bottom.addWidget(self.status,1);self.encoding=QComboBox();self.encoding.addItems(ENCODINGS);self.encoding.currentTextChanged.connect(self.set_encoding);bottom.addWidget(self.encoding);self.endings=QComboBox();self.endings.addItems(['Windows (CRLF)','Unix (LF)','Mac (CR)']);self.endings.currentIndexChanged.connect(self.set_eol);bottom.addWidget(self.endings);layout.addLayout(bottom);self.new()
    def action(self,menu,label,callback,key=None,check=False):
        a=QAction(label,self);a.setCheckable(check);a.triggered.connect(lambda _=False:callback());menu.addAction(a)
        if key:a.setShortcut(QKeySequence(key));a.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut);self.addAction(a)
        return a
    def current(self):return self.tabs.currentWidget()
    def new(self):
        tab=TextTab();self.tabs.addTab(tab,'Unbenannt');self.tabs.setCurrentWidget(tab);tab.editor.document().modificationChanged.connect(lambda _:self.update_title(tab));tab.editor.cursorPositionChanged.connect(self.update_status);tab.editor.textChanged.connect(self.update_status);self.toggle_wrap();tab.editor.setFocus();return tab
    def update_title(self,tab):
        i=self.tabs.indexOf(tab)
        if i>=0:self.tabs.setTabText(i,('● ' if tab.editor.document().isModified() else '')+(tab.path.name if tab.path else 'Unbenannt'));self.tabs.setTabToolTip(i,str(tab.path or 'Noch nicht gespeichert'))
    def changed(self,*_):
        tab=self.current()
        if not tab:return
        self.encoding.blockSignals(True);self.encoding.setCurrentText(tab.encoding);self.encoding.blockSignals(False);self.endings.blockSignals(True);self.endings.setCurrentIndex(['\r\n','\n','\r'].index(tab.eol));self.endings.blockSignals(False);self.markdown.setChecked(not tab.preview.isHidden());self.wrap.setChecked(tab.editor.lineWrapMode()!=QPlainTextEdit.LineWrapMode.NoWrap);self.update_status()
    def update_status(self):
        tab=self.current()
        if tab:
            c=tab.editor.textCursor();self.status.setText(f'Zeile {c.blockNumber()+1}, Spalte {c.positionInBlock()+1}  ·  {tab.editor.document().characterCount()-1:,} Zeichen')
    def open(self,paths=None):
        if not paths:paths=QFileDialog.getOpenFileNames(self,'Textdateien öffnen','','Textdateien (*.txt *.md *.markdown *.log *.csv *.json *.py);;Alle Dateien (*)')[0]
        for path in paths:
            try:
                path=Path(path).resolve()
                existing=next((self.tabs.widget(i) for i in range(self.tabs.count()) if self.tabs.widget(i).path==path),None)
                if existing:self.tabs.setCurrentWidget(existing);continue
                text,encoding,eol,stamp=read_text(path);tab=self.new();tab.path=path;tab.encoding=encoding;tab.eol=eol;tab.fingerprint=stamp;tab.editor.setPlainText(text);tab.editor.document().setModified(False)
                if text.startswith('.LOG'):
                    tab.editor.moveCursor(QTextCursor.MoveOperation.End);tab.editor.insertPlainText('\n'+datetime.now().strftime('%H:%M %d.%m.%Y')+'\n')
                if path.suffix.lower() in ('.md','.markdown'):tab.preview.show();tab.render()
                self.update_title(tab);self.changed()
            except Exception as exc:QMessageBox.warning(self,'Öffnen fehlgeschlagen',str(exc))
    def save(self,tab=None,as_new=False):
        tab=tab or self.current();path=tab.path;stamp=tab.fingerprint
        if as_new or path is None:
            name=QFileDialog.getSaveFileName(self,'Text speichern',str(path or 'Unbenannt.txt'),'Textdatei (*.txt);;Markdown (*.md);;Alle Dateien (*)')[0]
            if not name:return False
            path=Path(name).resolve();stamp=tab.fingerprint if path==tab.path else None
        try:
            try:stamp=write_text(path,tab.editor.toPlainText(),tab.encoding,tab.eol,stamp)
            except FileExistsError:
                if QMessageBox.question(self,'Datei extern geändert','Die Datei wurde außerhalb von ReTexto geändert. Trotzdem mit deinem Text überschreiben?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return False
                stamp=write_text(path,tab.editor.toPlainText(),tab.encoding,tab.eol)
            tab.path=path;tab.fingerprint=stamp;tab.editor.document().setModified(False);self.update_title(tab);return True
        except Exception as exc:QMessageBox.warning(self,'Speichern fehlgeschlagen',str(exc));return False
    def save_all(self):
        for i in range(self.tabs.count()):
            tab=self.tabs.widget(i)
            if (tab.editor.document().isModified() or tab.path is None) and not self.save(tab):return False
        return True
    def confirm(self,tab):
        if not tab.editor.document().isModified():return True
        self.tabs.setCurrentWidget(tab);answer=QMessageBox.question(self,'Änderungen speichern?',f'{tab.path.name if tab.path else "Unbenannt"}: Änderungen speichern?',QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel)
        return self.save(tab) if answer==QMessageBox.StandardButton.Save else answer==QMessageBox.StandardButton.Discard
    def confirm_all(self):
        if self.ai_dialog is not None and self.ai_dialog.busy:
            QMessageBox.information(self,'Lokale KI','Bitte zuerst die KI-Berechnung abschließen oder abbrechen.');return False
        return all(self.confirm(self.tabs.widget(i)) for i in range(self.tabs.count()))
    def close_tab(self,index=None):
        if index is None:index=self.tabs.currentIndex()
        tab=self.tabs.widget(index)
        if not self.confirm(tab):return
        self.tabs.removeTab(index);tab.deleteLater()
        if not self.tabs.count():self.new()
    def set_encoding(self,value):
        if self.current() and self.current().encoding!=value:self.current().encoding=value;self.current().editor.document().setModified(True)
    def set_eol(self,index):
        if self.current() and self.current().eol!=['\r\n','\n','\r'][index]:self.current().eol=['\r\n','\n','\r'][index];self.current().editor.document().setModified(True)
    def toggle_wrap(self):self.current().editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth if self.wrap.isChecked() else QPlainTextEdit.LineWrapMode.NoWrap)
    def toggle_preview(self):self.current().preview.setVisible(self.markdown.isChecked());self.current().render()
    def font(self):
        font,ok=QFontDialog.getFont(self.current().editor.font(),self)
        if ok:self.current().editor.setFont(font)
    def insert_markup(self,left,right):
        cursor=self.current().editor.textCursor();cursor.insertText(left+cursor.selectedText().replace('\u2029','\n')+right);self.current().editor.setTextCursor(cursor)
    def goto(self):
        number,ok=QInputDialog.getInt(self,'Gehe zu','Zeile:',1,1,self.current().editor.blockCount())
        if ok:self.current().editor.setTextCursor(QTextCursor(self.current().editor.document().findBlockByNumber(number-1)))
    def find_next(self,back=False):
        if not self.search_text:self.find_dialog();return False
        editor=self.current().editor;flags=self.search_flags|(QTextDocument.FindFlag.FindBackward if back else QTextDocument.FindFlag(0))
        if editor.find(self.search_text,flags):return True
        old=editor.textCursor();editor.moveCursor(QTextCursor.MoveOperation.End if back else QTextCursor.MoveOperation.Start)
        if editor.find(self.search_text,flags):return True
        editor.setTextCursor(old);self.status.setText('Keine weiteren Treffer.');return False
    def find_dialog(self,replace=False):
        dialog=QDialog(self);dialog.setWindowTitle('Suchen und Ersetzen' if replace else 'Suchen');layout=QVBoxLayout(dialog);query=QLineEdit(self.search_text);query.setPlaceholderText('Suchen nach …');layout.addWidget(query);replacement=QLineEdit();replacement.setPlaceholderText('Ersetzen durch …')
        if replace:layout.addWidget(replacement)
        case=QCheckBox('Groß-/Kleinschreibung');word=QCheckBox('Nur ganze Wörter');layout.addWidget(case);layout.addWidget(word)
        def options():
            self.search_text=query.text();self.search_flags=QTextDocument.FindFlag(0)
            if case.isChecked():self.search_flags|=QTextDocument.FindFlag.FindCaseSensitively
            if word.isChecked():self.search_flags|=QTextDocument.FindFlag.FindWholeWords
        def find():
            options()
            if self.search_text:self.find_next()
        button=QPushButton('Weitersuchen');button.clicked.connect(find);layout.addWidget(button)
        if replace:
            def one():
                options();cursor=self.current().editor.textCursor();selected=cursor.selectedText();a=selected if case.isChecked() else selected.casefold();b=query.text() if case.isChecked() else query.text().casefold()
                if b and a==b:cursor.insertText(replacement.text())
                if b:self.find_next()
            def all_matches():
                options()
                if not query.text():return
                editor=self.current().editor;cursor=QTextCursor(editor.document());cursor.beginEditBlock();count=0
                while True:
                    found=editor.document().find(query.text(),cursor,self.search_flags)
                    if found.isNull():break
                    found.insertText(replacement.text());cursor.setPosition(found.position());count+=1
                cursor.endEditBlock();self.status.setText(f'{count} Treffer ersetzt.')
            for label,fn in [('Ersetzen',one),('Alle ersetzen',all_matches)]:b=QPushButton(label);b.clicked.connect(fn);layout.addWidget(b)
        dialog.resize(420,200);dialog.exec()
    def get_printer(self):
        if self.printer is None:
            from PySide6.QtPrintSupport import QPrinter
            self.printer=QPrinter(QPrinter.PrinterMode.HighResolution)
        return self.printer
    def page_setup(self):
        from PySide6.QtPrintSupport import QPageSetupDialog
        QPageSetupDialog(self.get_printer(),self).exec()
    def print_text(self):
        from PySide6.QtPrintSupport import QPrintDialog
        if QPrintDialog(self.get_printer(),self).exec()==QDialog.DialogCode.Accepted:self.current().editor.document().print_(self.get_printer())
    def spellcheck(self):
        from text_spell import SpellDialog
        SpellDialog(self.current().editor,self).exec()
    def ai(self):
        from text_ai import TextAI
        self.ai_dialog=TextAI(self.current().editor,self);self.ai_dialog.exec()
    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls() and all(u.isLocalFile() for u in event.mimeData().urls()):event.acceptProposedAction()
    def dropEvent(self,event):self.open([u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]);event.acceptProposedAction()
