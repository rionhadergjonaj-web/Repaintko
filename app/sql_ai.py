"""Local Qwen assistant: drafts only, never connects to or executes a database."""
from text_ai import TextAI
from PySide6.QtWidgets import QMessageBox

class SQLAI(TextAI):
    def __init__(self,editor,parent=None,dialect='sqlite',layout=False):
        super().__init__(editor,parent);self.layout_mode=layout;self.dialect=dialect
        self.setWindowTitle('ReDataKo · Lokale SQL-KI' if not layout else 'ReDrawko · Lokale Layout-KI')
        self.mode.clear();self.mode.addItems(['SQL korrigieren','Fremdschlüssel ergänzen','SQL optimieren','SQL entwerfen'] if not layout else ['Tabellen logisch anordnen'])
        self.system_prompt=('Du bist ein SQL-Experte für '+dialect+'. Gib ausschließlich ein vollständiges SQL-Script ohne Markdown aus. Erhalte Spalten, Primärschlüssel und Fremdschlüssel. Erfinde keine vorhandenen Daten. Führe nichts aus. '+
                            'Für SQLite beachte zusammengesetzte Schlüssel und Referenzintegrität.')
        if layout:self.system_prompt='Ordne die gegebenen Tabellen nach fachlichen Gruppen. Gib ausschließlich JSON mit einem Feld order aus, dessen Wert alle gegebenen Tabellennamen genau einmal enthält. Ändere keine Namen.'
        self.info.setText('Lokales Qwen-Modell · keine Cloud, keine Ausführung. SQL und KI-Vorschläge vor dem Übernehmen prüfen. Maximal 6.000 Zeichen pro Auftrag.')
    def checked(self):
        text=self.preview.toPlainText().strip()
        if text.startswith('```'):text='\n'.join(text.splitlines()[1:-1]).strip();self.preview.setPlainText(text)
        try:
            if self.layout_mode:
                import json
                value=json.loads(text)
                if not isinstance(value.get('order'),list):raise ValueError('JSON muss eine Liste order enthalten.')
            else:
                import sqlglot
                if not sqlglot.parse(text,read=self.dialect):raise ValueError('Kein SQL vorhanden.')
            return True
        except Exception as exc:QMessageBox.warning(self,'Vorschlag prüfen','Nicht übernommen: '+str(exc));return False
    def replace(self):
        if self.checked():super().replace()
    def insert(self):
        if self.checked():super().insert()
