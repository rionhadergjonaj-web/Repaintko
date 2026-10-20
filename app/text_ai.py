"""Optional user-triggered local text generation. No network service or uploads."""
from pathlib import Path
import os,tempfile
from PySide6.QtCore import QProcess,Qt
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QComboBox,QPlainTextEdit,QPushButton,QLabel,QMessageBox

class TextAI(QDialog):
    def __init__(self,editor,parent=None):
        super().__init__(parent);self.editor=editor;self.cursor=editor.textCursor();self.snapshot=editor.toPlainText();self.source=self.cursor.selectedText().replace('\u2029','\n') if self.cursor.hasSelection() else self.snapshot;self.busy=False;self.prompt_path=None;self.output=b'';self.errors=b'';self.cancelled=False
        self.setWindowTitle('ReTexto · Lokale KI');self.resize(720,580);layout=QVBoxLayout(self)
        self.info=QLabel('Qwen 2.5 · läuft auf deinem PC. Vorschläge bitte vor dem Übernehmen prüfen.\nVerwendet die Auswahl oder den gesamten Text, maximal 6.000 Zeichen.');self.info.setWordWrap(True);layout.addWidget(self.info)
        self.mode=QComboBox();self.mode.addItems(['Umschreiben','Zusammenfassen','Rechtschreibung und Grammatik verbessern','Text verfassen']);layout.addWidget(self.mode)
        self.instructions=QPlainTextEdit();self.instructions.setPlaceholderText('Optional: Wünsche, Ton oder Auftrag für einen neuen Text …');self.instructions.setMaximumHeight(100);layout.addWidget(self.instructions)
        row=QHBoxLayout();self.start=QPushButton('Vorschlag erstellen');self.start.clicked.connect(self.generate);row.addWidget(self.start);self.cancel=QPushButton('Berechnung abbrechen');self.cancel.clicked.connect(self.stop);self.cancel.setEnabled(False);row.addWidget(self.cancel);layout.addLayout(row)
        self.preview=QPlainTextEdit();self.preview.setPlaceholderText('Hier erscheint der Vorschlag. Du kannst ihn vor dem Einfügen bearbeiten.');layout.addWidget(self.preview,1)
        row=QHBoxLayout();self.replace_button=QPushButton('Auswahl / Text ersetzen');self.replace_button.clicked.connect(self.replace);self.insert_button=QPushButton('An Cursor einfügen');self.insert_button.clicked.connect(self.insert);row.addWidget(self.replace_button);row.addWidget(self.insert_button);layout.addLayout(row);self.enable_result(False)
        self.process=QProcess(self);self.process.readyReadStandardOutput.connect(self.read_output);self.process.readyReadStandardError.connect(self.read_error);self.process.finished.connect(self.process_done);self.process.errorOccurred.connect(self.error)
        if os.name=='nt':self.process.setCreateProcessArgumentsModifier(lambda args:setattr(args,'flags',args.flags|0x08000000)) if hasattr(self.process,'setCreateProcessArgumentsModifier') else None
    def enable_result(self,value):self.replace_button.setEnabled(value);self.insert_button.setEnabled(value)
    def generate(self):
        runtime=Path(__file__).resolve().parent/'text_ai_runtime';exe=runtime/'llama-completion.exe';model=runtime/'model.gguf'
        if not exe.exists() or not model.exists():self.info.setText('Die lokale KI fehlt. Bitte die Repaintko-Installation reparieren.');return
        source='' if self.mode.currentIndex()==3 else self.source
        if len(source)>6000 or len(self.instructions.toPlainText())>2000:self.info.setText('Bitte maximal 6.000 Zeichen auswählen und den Auftrag auf 2.000 Zeichen kürzen.');return
        if not source.strip() and not self.instructions.toPlainText().strip():self.info.setText('Bitte Text oder einen Auftrag eingeben.');return
        role=getattr(self,'system_prompt','Du bist ein hilfreicher deutscher Schreibassistent. Antworte auf Deutsch und gib nur den angeforderten Text aus, ohne Einleitung.')
        prompt='<|im_start|>system\n'+role+'<|im_end|>\n<|im_start|>user\nAufgabe: '+self.mode.currentText()+'\nWünsche: '+self.instructions.toPlainText()+'\nText:\n'+source+'<|im_end|>\n<|im_start|>assistant\n'
        fd,name=tempfile.mkstemp(suffix='.txt',prefix='retexto-');self.prompt_path=Path(name)
        with os.fdopen(fd,'w',encoding='utf-8') as f:f.write(prompt)
        self.output=b'';self.errors=b'';self.preview.clear();self.busy=True;self.cancelled=False;self.start.setEnabled(False);self.cancel.setEnabled(True);self.enable_result(False);self.info.setText('Die lokale KI rechnet … Beim ersten Start kann es etwas dauern.');self.process.setWorkingDirectory(str(runtime))
        self.process.start(str(exe),['-m',str(model),'-f',str(self.prompt_path),'--no-conversation','--no-display-prompt','--color','off','-c','4096','-n','640','-t',str(max(1,min(8,(os.cpu_count() or 4)//2))),'--temp','0.5'])
    def read_output(self):self.output+=bytes(self.process.readAllStandardOutput())
    def read_error(self):self.errors=(self.errors+bytes(self.process.readAllStandardError()))[-4000:]
    def cleanup(self):
        if self.prompt_path:self.prompt_path.unlink(missing_ok=True);self.prompt_path=None
        self.busy=False;self.start.setEnabled(True);self.cancel.setEnabled(False)
    def error(self,error):
        if error==QProcess.ProcessError.FailedToStart:self.cleanup();self.info.setText('Die lokale KI konnte nicht gestartet werden: '+self.process.errorString())
    def process_done(self,code,status):
        self.read_output();self.read_error();self.cleanup()
        if self.cancelled:self.info.setText('Berechnung abgebrochen. Dein Text bleibt erhalten.');return
        if code!=0:self.info.setText('KI-Berechnung fehlgeschlagen. '+self.errors.decode('utf-8',errors='replace')[-600:]);return
        text=self.output.decode('utf-8',errors='replace').replace('<|im_end|>','').replace('<|endoftext|>','').strip().removesuffix('[end of text]').rstrip();self.preview.setPlainText(text);self.enable_result(bool(text));self.info.setText('Vorschlag bereit. Prüfe Inhalt und Vollständigkeit vor dem Übernehmen (maximal 640 Ausgabe-Tokens).')
    def stop(self):
        if self.busy:self.cancelled=True;self.process.kill()
    def valid(self):
        if self.editor.toPlainText()!=self.snapshot:QMessageBox.warning(self,'Text geändert','Der Ausgangstext hat sich geändert. Öffne die KI-Texthilfe erneut.');return False
        return True
    def replace(self):
        if not self.valid():return
        if not self.cursor.hasSelection():self.cursor.select(self.cursor.SelectionType.Document)
        self.cursor.insertText(self.preview.toPlainText());self.accept()
    def insert(self):
        if not self.valid():return
        self.cursor.clearSelection();self.cursor.insertText(self.preview.toPlainText());self.accept()
    def reject(self):
        if self.busy:self.stop();return
        super().reject()
