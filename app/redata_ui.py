"""ReDataKo database workbench: all database work runs in one background worker."""
import csv,json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from PySide6.QtCore import Qt,QTimer,Signal
from PySide6.QtGui import QAction,QKeySequence
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QSplitter,QPushButton,QLabel,QListWidget,QTabWidget,QPlainTextEdit,QTableWidget,QTableWidgetItem,QFileDialog,QMessageBox,QDialog,QFormLayout,QLineEdit,QComboBox,QCheckBox,QSpinBox,QDialogButtonBox,QInputDialog)
from redata_engine import Database
from redraw_ui import ReDrawko

class ReDataKo(QWidget):
    returnRequested=Signal()
    def __init__(self,parent=None,settings=None):
        super().__init__(parent);self.settings=settings;self.db=Database();self.pool=ThreadPoolExecutor(max_workers=1);self.future=None;self.callback=None;self.table_data=None;self.dirty=False;self.script_path=None
        root=QVBoxLayout(self);top=QHBoxLayout();root.addLayout(top)
        for title,fn in [('← Bild / GIF',self.returnRequested.emit),('Verbinden',self.connect_dialog),('Neue SQLite-DB',self.new_database),('Tabelle erstellen',self.create_table),('Schema / ERD',self.load_erd),('Backup',self.backup)]:self.button(top,title,fn)
        self.status=QLabel('ReDataKo · SQLite, MySQL und Microsoft Access');self.status.setWordWrap(True);root.addWidget(self.status)
        extra=QHBoxLayout();root.addLayout(extra)
        self.button(extra,'Neue Access-DB',self.new_access);self.button(extra,'Neue MySQL-DB',self.new_mysql);self.button(extra,'Schema als SQL speichern',self.export_schema)
        split=QSplitter();root.addWidget(split,1);side=QWidget();left=QVBoxLayout(side);left.addWidget(QLabel('Tabellen / Ansichten'));self.tables=QListWidget();self.tables.itemDoubleClicked.connect(lambda i:self.browse(i.text()));left.addWidget(self.tables);self.button(left,'Aktualisieren',self.refresh_tables);split.addWidget(side)
        self.tabs=QTabWidget();split.addWidget(self.tabs);split.setSizes([220,1000]);query=QWidget();layout=QVBoxLayout(query);bar=QHBoxLayout();layout.addLayout(bar)
        for title,fn in [('SQL öffnen',self.open_script),('SQL speichern',self.save_script),('Ausführen (F5)',self.run_sql),('Abbrechen',self.cancel),('Commit',lambda:self.transact(True)),('Rollback',lambda:self.transact(False)),('Lokale KI',self.ai)]:self.button(bar,title,fn)
        self.sql=QPlainTextEdit();self.sql.setPlaceholderText('SELECT * FROM "meine_tabelle";\n\nSQL wird erst durch Ausführen gestartet. Änderungen anschließend mit Commit bestätigen oder mit Rollback verwerfen.');layout.addWidget(self.sql,1);self.sql.textChanged.connect(lambda:setattr(self,'dirty',True))
        self.results=QTabWidget();layout.addWidget(self.results,1);self.tabs.addTab(query,'SQL & Ergebnisse')
        data=QWidget();body=QVBoxLayout(data);row=QHBoxLayout();body.addLayout(row)
        for title,fn in [('← 500',lambda:self.page(-500)),('500 →',lambda:self.page(500)),('Zeile hinzufügen',lambda:self.edit_row(True)),('Zeile bearbeiten',self.edit_row),('Zeile löschen',self.delete_row),('CSV exportieren',self.csv_export),('CSV importieren',self.csv_import)]:self.button(row,title,fn)
        self.grid=QTableWidget();self.grid.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);self.grid.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows);body.addWidget(self.grid);self.tabs.addTab(data,'Tabellendaten')
        self.erd=ReDrawko(self,settings);self.erd.returnRequested.connect(lambda:self.tabs.setCurrentIndex(0));self.tabs.addTab(self.erd,'ERD');self.erd.autosave.stop()
        self.timer=QTimer(self);self.timer.setInterval(60);self.timer.timeout.connect(self.poll)
        action=QAction(self);action.setShortcut(QKeySequence('F5'));action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut);action.triggered.connect(self.run_sql);self.addAction(action)
    def button(self,row,title,fn):
        button=QPushButton(title);button.clicked.connect(lambda:fn());row.addWidget(button);return button
    def submit(self,fn,callback=None):
        if self.future:self.status.setText('Eine Aufgabe läuft bereits. Bitte warten oder abbrechen.');return
        self.db.cancelled.clear()
        self.status.setText('ReDataKo arbeitet …');self.callback=callback;self.future=self.pool.submit(fn);self.timer.start()
    def poll(self):
        if not self.future or not self.future.done():return
        future,self.future=self.future,None;callback,self.callback=self.callback,None;self.timer.stop()
        try:
            result=future.result();self.status.setText(self.db.label+(' · Schreibgeschützt' if self.db.readonly else ' · Änderungen benötigen Commit'))
            if callback:callback(result)
            elif isinstance(result,str):self.status.setText(result)
        except Exception as exc:QMessageBox.warning(self,'ReDataKo',str(exc));self.status.setText('Aufgabe fehlgeschlagen. '+str(exc)[:300])
    def new_database(self):
        if not self.confirm_connection():return
        path=QFileDialog.getSaveFileName(self,'Neue SQLite-Datenbank','','SQLite (*.sqlite *.db)')[0]
        if path:self.submit(lambda:self.db.connect('sqlite',path=path,create=True,readonly=False),self.show_tables)
    def connect_dialog(self):
        if self.future:return
        if not self.confirm_connection():return
        dialog=QDialog(self);dialog.setWindowTitle('Datenbank verbinden');form=QFormLayout(dialog);kind=QComboBox();kind.addItems(['SQLite','MySQL','Access']);form.addRow('System',kind)
        fields={}
        for name,title,default in [('path','Datei (.sqlite / .accdb / .mdb)',''),('host','MySQL-Host','localhost'),('port','Port','3306'),('database','Datenbank',''),('user','Benutzer',''),('password','Passwort','')]:
            field=QLineEdit(default);fields[name]=field;form.addRow(title,field)
            if name=='password':field.setEchoMode(QLineEdit.EchoMode.Password)
        pick=QPushButton('Datei auswählen');pick.clicked.connect(lambda:fields['path'].setText(QFileDialog.getOpenFileName(dialog,'Datenbank','','Datenbanken (*.sqlite *.db *.sqlite3 *.accdb *.mdb)')[0]));form.addRow(pick)
        readonly=QCheckBox('Schreibgeschützt verbinden');readonly.setChecked(True);form.addRow(readonly);tls=QCheckBox('MySQL: TLS mit Zertifikatsprüfung');tls.setChecked(True);form.addRow(tls)
        note=QLabel('MySQL benötigt einen erreichbaren Server. Access benötigt den installierten Microsoft-ODBC-Treiber (64 Bit). Passwörter werden nicht gespeichert.');note.setWordWrap(True);form.addRow(note)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);form.addRow(buttons)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        options={k:v.text() for k,v in fields.items()};options.update(readonly=readonly.isChecked(),tls=tls.isChecked());selected=kind.currentText().lower();self.submit(lambda:self.db.connect(selected,**options),self.show_tables)
    def show_tables(self,tables):self.tables.clear();self.tables.addItems(tables)
    def confirm_connection(self):
        if self.future:return False
        if self.db.connection and not self.db.readonly:return QMessageBox.question(self,'Verbindung wechseln','Nicht bestätigte Änderungen werden beim Wechsel zurückgerollt. Vorher bei Bedarf Commit wählen. Jetzt wechseln?')==QMessageBox.StandardButton.Yes
        return True
    def new_access(self):
        if not self.confirm_connection():return
        path=QFileDialog.getSaveFileName(self,'Neue Access-Datenbank','','Access (*.accdb)')[0]
        if path:
            from redata_engine import create_access
            self.submit(lambda:(create_access(path),self.db.connect('access',path=path,readonly=False))[1],self.show_tables)
    def new_mysql(self):
        if self.db.kind!='mysql' or not self.db.connection:QMessageBox.information(self,'MySQL','Zuerst zum MySQL-Server verbinden. Das Datenbankfeld kann leer bleiben.');return
        name,ok=QInputDialog.getText(self,'Neue MySQL-Datenbank','Name:')
        if ok and name.strip():self.sql.setPlainText('CREATE DATABASE '+self.db.quote(name.strip())+' CHARACTER SET utf8mb4;');self.tabs.setCurrentIndex(0);self.status.setText('DDL vorbereitet. Nach Ausführen zur neuen Datenbank verbinden.')
    def export_schema(self):
        path=QFileDialog.getSaveFileName(self,'Schema exportieren','Schema.sql','SQL (*.sql)')[0]
        if path:
            from redraw_model import atomic_write
            self.submit(self.db.schema_sql,lambda text:atomic_write(path,text.encode('utf-8')))
    def refresh_tables(self):self.submit(self.db.tables,self.show_tables)
    def run_sql(self):
        source=self.sql.textCursor().selectedText().replace('\u2029','\n') or self.sql.toPlainText()
        if not source.strip():return
        self.submit(lambda:self.db.execute(source),self.show_results)
    def show_results(self,results):
        self.results.clear()
        for i,result in enumerate(results):
            table=QTableWidget();self.fill_grid(table,result);table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);self.results.addTab(table,f'Ergebnis {i+1}'+(' · erste 1000 Zeilen' if result['truncated'] else ''))
        self.tabs.setCurrentIndex(0)
        if self.db.kind=='mysql':self.status.setText('MySQL: DDL wie CREATE/ALTER kann serverseitig automatisch committen. DML mit Commit bestätigen.')
    def fill_grid(self,grid,data):
        grid.clear();grid.setRowCount(len(data['rows']));grid.setColumnCount(len(data['columns']));grid.setHorizontalHeaderLabels(data['columns'])
        for r,row in enumerate(data['rows']):
            for c,value in enumerate(row):grid.setItem(r,c,QTableWidgetItem('NULL' if value is None else '<BLOB '+str(len(value))+' Bytes>' if isinstance(value,bytes) else str(value)))
        grid.resizeColumnsToContents()
    def transact(self,commit):self.submit(lambda:self.db.transaction(commit))
    def cancel(self):self.db.cancel();self.status.setText('Abbruch angefordert. Die Reaktionszeit hängt vom Datenbanktreiber ab.')
    def browse(self,table,offset=0):
        self.submit(lambda:self.db.browse(table,offset),self.show_data)
    def show_data(self,data):self.table_data=data;self.fill_grid(self.grid,data);self.tabs.setCurrentIndex(1);self.status.setText(f"{data['table']} · ab Zeile {data['offset']+1} · {len(data['rows'])} Zeilen geladen")
    def page(self,delta):
        if self.table_data:self.browse(self.table_data['table'],max(0,self.table_data['offset']+delta))
    def row_values(self):
        if not self.table_data or self.grid.currentRow()<0:raise ValueError('Zuerst eine Tabellenzeile auswählen.')
        return dict(zip(self.table_data['columns'],self.table_data['rows'][self.grid.currentRow()]))
    def edit_row(self,new=False):
        if not self.table_data:return
        if self.db.readonly:QMessageBox.information(self,'Schreibschutz','Bitte ohne Schreibschutz neu verbinden.');return
        try:original=None if new else self.row_values()
        except ValueError as exc:QMessageBox.information(self,'Zeile',str(exc));return
        from PySide6.QtWidgets import QScrollArea
        dialog=QDialog(self);dialog.setWindowTitle('Neue Zeile' if new else 'Zeile bearbeiten');layout=QVBoxLayout(dialog);info=QLabel('NULL bedeutet ohne Wert. Standard verwendet den Datenbank-Standardwert, z. B. eine automatisch erzeugte ID.');info.setWordWrap(True);layout.addWidget(info)
        area=QScrollArea();area.setWidgetResizable(True);container=QWidget();form=QFormLayout(container);area.setWidget(container);layout.addWidget(area);fields={}
        for name in self.table_data['columns']:
            value=original.get(name) if original else None;line=QLineEdit('' if value is None else str(value));null=QCheckBox('NULL');null.setChecked(value is None);default=QCheckBox('Standard');default.setChecked(new);default.setVisible(new);row=QHBoxLayout();row.addWidget(line,1);row.addWidget(null);row.addWidget(default);form.addRow(name,row);fields[name]=(line,null,default)
            line.textEdited.connect(lambda _,n=null,d=default:(n.setChecked(False),d.setChecked(False)))
            null.clicked.connect(lambda _,d=default:d.setChecked(False))
            if isinstance(value,bytes):line.setText('Binärdaten – unverändert');line.setEnabled(False);null.setEnabled(False)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons);dialog.resize(650,500)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        try:
            values={}
            for name,(line,null,default) in fields.items():
                if (new and default.isChecked()) or not line.isEnabled():continue
                value=None if null.isChecked() else line.text()
                if value is not None and original and isinstance(original.get(name),(int,float)):value=type(original[name])(value)
                values[name]=value
            table=self.table_data['table'];self.submit(lambda:self.db.change_row(table,values,original),lambda _:self.browse(table))
        except Exception as exc:QMessageBox.warning(self,'Zeile',str(exc))
    def delete_row(self):
        try:original=self.row_values()
        except ValueError:return
        if QMessageBox.question(self,'Zeile löschen','Ausgewählte Zeile löschen? Anschließend Commit oder Rollback wählen.')!=QMessageBox.StandardButton.Yes:return
        table=self.table_data['table'];self.submit(lambda:self.db.change_row(table,{},original,True),lambda _:self.browse(table))
    def create_table(self):
        dialog=QDialog(self);dialog.setWindowTitle('Tabelle erstellen');layout=QVBoxLayout(dialog);name=QLineEdit();name.setPlaceholderText('Tabellenname');layout.addWidget(name);grid=QTableWidget(3,4);grid.setHorizontalHeaderLabels(['Spalte','Datentyp','PK (ja/nein)','NULL (ja/nein)']);layout.addWidget(grid)
        for c,value in enumerate(['id','INTEGER','ja','nein']):grid.setItem(0,c,QTableWidgetItem(value))
        self.button(layout,'Weitere Spalte',lambda:grid.insertRow(grid.rowCount()));buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons);dialog.resize(680,450)
        if dialog.exec()!=QDialog.DialogCode.Accepted or not name.text().strip():return
        lines=[];pk=[]
        for r in range(grid.rowCount()):
            values=[grid.item(r,c).text().strip() if grid.item(r,c) else '' for c in range(4)]
            if not values[0]:continue
            lines.append(self.db.quote(values[0])+' '+(values[1] or 'TEXT')+(' NOT NULL' if values[3].casefold() not in ('ja','yes','1') else ''))
            if values[2].casefold() in ('ja','yes','1'):pk.append(self.db.quote(values[0]))
        if pk:lines.append('PRIMARY KEY ('+', '.join(pk)+')')
        self.sql.setPlainText('CREATE TABLE '+self.db.quote(name.text().strip())+' (\n  '+',\n  '.join(lines)+'\n);');self.tabs.setCurrentIndex(0);self.status.setText('SQL vorbereitet. Prüfen und mit F5 ausführen.')
    def load_erd(self):
        if self.erd.doc.dirty and not self.erd.confirm():return
        def show(source):
            from sql_schema import parse_schema
            from redraw_model import DiagramDocument
            p=parse_schema(source,'mysql' if self.db.kind=='mysql' else 'sqlite');self.erd.doc=DiagramDocument();self.erd.doc.data.update(pages=[p],active_page=p['id']);self.erd.scene.doc=self.erd.doc;self.erd.refresh();self.erd.fit();self.tabs.setCurrentIndex(2)
        self.submit(self.db.schema_sql,show)
    def open_script(self):
        if not self.confirm_script():return
        path=QFileDialog.getOpenFileName(self,'SQL-Script öffnen','','SQL (*.sql);;Text (*.txt)')[0]
        if path:
            try:self.sql.setPlainText(Path(path).read_text(encoding='utf-8-sig'));self.script_path=path;self.dirty=False
            except Exception as exc:QMessageBox.warning(self,'Öffnen',str(exc))
    def save_script(self):
        path=QFileDialog.getSaveFileName(self,'SQL speichern',self.script_path or 'Abfrage.sql','SQL (*.sql)')[0]
        if not path:return False
        try:
            from redraw_model import atomic_write
            atomic_write(path,self.sql.toPlainText().encode('utf-8'));self.script_path=path;self.dirty=False;return True
        except Exception as exc:QMessageBox.warning(self,'Speichern',str(exc));return False
    def csv_export(self):
        if not self.table_data:return
        path=QFileDialog.getSaveFileName(self,'Geladene 500 Zeilen exportieren','Daten.csv','CSV (*.csv)')[0]
        if path:
            try:
                with open(path,'w',encoding='utf-8-sig',newline='') as f:writer=csv.writer(f);writer.writerow(self.table_data['columns']);writer.writerows(self.table_data['rows'])
            except Exception as exc:QMessageBox.warning(self,'CSV',str(exc))
    def csv_import(self):
        if not self.table_data:return
        path=QFileDialog.getOpenFileName(self,'CSV in aktuelle Tabelle importieren','','CSV (*.csv)')[0]
        if not path:return
        table=self.table_data['table'];columns=set(self.table_data['columns'])
        def load():
            count=0
            try:
                with open(path,encoding='utf-8-sig',newline='') as f:
                    reader=csv.DictReader(f)
                    if not reader.fieldnames or not set(reader.fieldnames)<=columns:raise ValueError('CSV-Kopf enthält unbekannte Spalten.')
                    for row in reader:
                        if count>=100000:raise ValueError('Maximal 100.000 Zeilen pro Import.')
                        self.db.change_row(table,row);count+=1
                return f'{count} Zeilen eingefügt. Commit oder Rollback wählen.'
            except Exception:self.db.connection.rollback();raise
        self.submit(load)
    def backup(self):
        path=QFileDialog.getSaveFileName(self,'SQLite-Backup in neue Datei','','SQLite (*.sqlite)')[0]
        if path:self.submit(lambda:self.db.backup(path))
    def ai(self):
        from sql_ai import SQLAI
        SQLAI(self.sql,self,'mysql' if self.db.kind=='mysql' else 'tsql' if self.db.kind=='access' else 'sqlite').exec()
    def confirm_script(self):
        if not self.dirty:return True
        answer=QMessageBox.question(self,'SQL-Script speichern?','Ungespeichertes Script speichern?',QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel)
        return self.save_script() if answer==QMessageBox.StandardButton.Save else answer==QMessageBox.StandardButton.Discard
    def confirm(self):
        if self.future:QMessageBox.information(self,'ReDataKo','Zuerst die laufende Aufgabe beenden oder abbrechen.');return False
        if not self.confirm_script() or not self.erd.confirm():return False
        if self.db.connection and not self.db.readonly:
            if QMessageBox.question(self,'Verbindung schließen','Beim Schließen werden nicht bestätigte Änderungen verworfen. Vorher bei Bedarf Commit wählen. Jetzt schließen?')!=QMessageBox.StandardButton.Yes:return False
        return True
    def shutdown(self):self.timer.stop();self.erd.shutdown();self.pool.submit(self.db.close);self.pool.shutdown(wait=False)
