"""ReDrawko's native, theme-inheriting desktop diagram editor."""
import base64,copy,json,math
from pathlib import Path
from PySide6.QtCore import Qt,QPointF,QRectF,QSize,QMimeData,Signal,QTimer
from PySide6.QtGui import QAction,QKeySequence,QIcon,QPixmap,QPainter,QColor,QDrag,QFont,QImage,QGuiApplication
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QMenuBar,QToolBar,QSplitter,QListWidget,QListWidgetItem,QLineEdit,QLabel,QPushButton,QComboBox,QDoubleSpinBox,QSpinBox,QCheckBox,QScrollArea,QFormLayout,QDialog,QDialogButtonBox,QPlainTextEdit,QTableWidget,QTableWidgetItem,QHeaderView,QColorDialog,QFileDialog,QMessageBox,QInputDialog,QFontComboBox,QTabWidget)
from redraw_model import DiagramDocument,SHAPES,node,edge,page,layer,uid,validate,template,atomic_write
from redraw_scene import DiagramScene,DiagramView,NodeItem,EdgeItem,outline
from redraw_io import drawio_import,drawio_export,sql_export,sql_import,export_scene
from PySide6.QtWidgets import QApplication

def shape_icon(key):
    pix=QPixmap(72,48);pix.fill(Qt.GlobalColor.transparent);p=QPainter(pix);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.translate(7,6);p.setPen(QColor('#6de0be'));p.setBrush(QColor('#355c67'));p.drawPath(outline(key,58,34));p.end();return QIcon(pix)

class ShapeList(QListWidget):
    def startDrag(self,actions):
        item=self.currentItem()
        if not item:return
        mime=QMimeData();mime.setData('application/x-redrawko-shape',item.data(Qt.ItemDataRole.UserRole).encode());drag=QDrag(self);drag.setMimeData(mime);drag.setPixmap(item.icon().pixmap(72,48));drag.exec(Qt.DropAction.CopyAction)

class ReDrawko(QWidget):
    returnRequested=Signal()
    def __init__(self,parent=None,settings=None,store=None,recovery=None):
        super().__init__(parent);self.preferences=settings;self.store=store;self.doc=DiagramDocument();self.recovery=Path(recovery) if recovery else None;self.updating=False;self.clipboard=None
        self.new_defaults()
        root=QVBoxLayout(self);root.setContentsMargins(5,5,5,5);header=QHBoxLayout();back=QPushButton('← Bild / GIF');back.clicked.connect(self.returnRequested);header.addWidget(back);title=QLabel('ReDrawko');title.setStyleSheet('font-size:22px;font-weight:bold;');header.addWidget(title);self.filename=QLabel('Neues Diagramm');header.addWidget(self.filename,1);root.addLayout(header)
        menus=QMenuBar();root.addWidget(menus);self.file_menu=menus.addMenu('Datei');edit=menus.addMenu('Bearbeiten');arrange=menus.addMenu('Anordnen');view=menus.addMenu('Ansicht');page_menu=menus.addMenu('Seite');help_menu=menus.addMenu('Hilfe')
        self.actions={}
        for label,fn,key in [('Neu',self.new,'Ctrl+N'),('Öffnen …',self.open,'Ctrl+O'),('Speichern',self.save,'Ctrl+S'),('Speichern unter …',lambda:self.save(True),'Ctrl+Shift+S'),('Bild einfügen …',self.image_import,None),('draw.io importieren …',self.import_drawio,None),('draw.io exportieren …',self.export_drawio,None),('SQL importieren …',self.import_sql,None),('SQL exportieren …',self.export_sql,None),('PNG exportieren …',lambda:self.export('png'),None),('SVG exportieren …',lambda:self.export('svg'),None),('PDF exportieren …',lambda:self.export('pdf'),None)]:self.action(self.file_menu,label,fn,key)
        for label,fn,key in [('Rückgängig',lambda:self.history(False),'Ctrl+Z'),('Wiederholen',lambda:self.history(True),'Ctrl+Y'),('Kopieren',self.copy,'Ctrl+C'),('Ausschneiden',self.cut,'Ctrl+X'),('Einfügen',self.paste,'Ctrl+V'),('Duplizieren',self.duplicate,'Ctrl+D'),('Löschen',self.delete,'Delete'),('Alles auswählen',self.select_all,'Ctrl+A'),('Beschriftung bearbeiten',self.edit_selected,'F2'),('Suchen / Ersetzen …',self.search_replace,'Ctrl+F'),('Objektdaten / Link …',self.object_data,None)]:self.action(edit,label,fn,key)
        for label,fn,key in [('Gruppieren',lambda:self.group(True),'Ctrl+G'),('Gruppierung aufheben',lambda:self.group(False),'Ctrl+Shift+G'),('Nach vorne',lambda:self.zorder(1),None),('Nach hinten',lambda:self.zorder(-1),None),('Sperren / Entsperren',self.lock,None),('Links ausrichten',lambda:self.align('left'),None),('Horizontal zentrieren',lambda:self.align('center'),None),('Rechts ausrichten',lambda:self.align('right'),None),('Oben ausrichten',lambda:self.align('top'),None),('Vertikal zentrieren',lambda:self.align('middle'),None),('Unten ausrichten',lambda:self.align('bottom'),None),('Horizontal verteilen',lambda:self.distribute('x'),None),('Vertikal verteilen',lambda:self.distribute('y'),None),('Automatisch: Raster',lambda:self.layout_nodes('grid'),None),('Automatisch: Hierarchie',lambda:self.layout_nodes('tree'),None),('Automatisch: Kreis',lambda:self.layout_nodes('circle'),None)]:self.action(arrange,label,fn,key)
        self.action(view,'Einpassen',self.fit,'Ctrl+0');self.action(view,'100 %',lambda:self.canvas.zoom(100),'Ctrl+1');self.action(view,'Vollbild-Zeichenfläche',self.toggle_panels,'Tab');self.action(view,'Raster anzeigen',self.toggle_grid);self.action(view,'Am Raster einrasten',self.toggle_snap)
        self.action(page_menu,'Seite hinzufügen',self.add_page);self.action(page_menu,'Seite duplizieren',self.duplicate_page);self.action(page_menu,'Seite umbenennen',self.rename_page);self.action(page_menu,'Seite löschen',self.delete_page);self.action(page_menu,'Seitengröße / Hintergrund …',self.page_settings)
        self.action(help_menu,'Bedienung',self.help)
        toolbar=QToolBar();toolbar.setIconSize(QSize(22,22));root.addWidget(toolbar)
        for label in ('Neu','Öffnen …','Speichern','Rückgängig','Wiederholen'):toolbar.addAction(self.actions[label])
        toolbar.addSeparator();self.connect_button=QPushButton('Verbindung');self.connect_button.setCheckable(True);self.connect_button.toggled.connect(self.connect_mode);toolbar.addWidget(self.connect_button)
        self.route=QComboBox();self.route.addItem('Rechtwinklig','orthogonal');self.route.addItem('Gerade','straight');self.route.addItem('Kurve','curved');toolbar.addWidget(self.route)
        templates=QPushButton('Vorlage …');templates.clicked.connect(self.choose_template);toolbar.addWidget(templates)
        ai=QPushButton('Lokale SQL-KI');ai.clicked.connect(self.sql_assistant);toolbar.addWidget(ai)
        self.action(arrange,'Beziehungen automatisch platzieren',self.schema_layout)
        self.action(arrange,'Lokale KI: Anordnung vorschlagen',self.ai_layout)
        self.split=QSplitter();root.addWidget(self.split,1)
        self.library=QWidget();left=QVBoxLayout(self.library);left.setContentsMargins(0,0,4,0);search=QLineEdit();search.setPlaceholderText('Form suchen …');search.textChanged.connect(self.filter_shapes);left.addWidget(search)
        self.category=QComboBox();self.category.addItems(['Alle']+sorted({s[1] for s in SHAPES.values()}));self.category.currentTextChanged.connect(lambda _:self.filter_shapes(search.text()));left.addWidget(self.category)
        self.shapes=ShapeList();self.shapes.setIconSize(QSize(72,48));self.shapes.setDragEnabled(True);self.shapes.itemDoubleClicked.connect(lambda i:self.add_shape(i.data(Qt.ItemDataRole.UserRole)));left.addWidget(self.shapes,1)
        hint=QLabel('Formen ziehen oder doppelklicken.\nVerbinden: zwei Formen anklicken.\nAlt: ohne Einrasten bewegen.');hint.setWordWrap(True);left.addWidget(hint);self.library.setMinimumWidth(160);self.split.addWidget(self.library)
        self.scene=DiagramScene(self.doc);self.canvas=DiagramView(self.scene);self.canvas.add_requested.connect(self.add_shape);self.canvas.connect_requested.connect(self.connect_nodes);self.scene.edit_requested.connect(self.edit_object);self.scene.changed.connect(self.changed);self.scene.selectionChanged.connect(self.selection_changed);self.split.addWidget(self.canvas)
        self.canvas.ports_connected.connect(self.connect_nodes)
        self.right=QTabWidget();self.right.setMinimumWidth(230);self.split.addWidget(self.right);self.split.setSizes([200,850,270])
        self.build_properties();self.build_layers()
        footer=QHBoxLayout();self.pages=QComboBox();self.pages.currentIndexChanged.connect(self.switch_page);footer.addWidget(self.pages);add=QPushButton('+ Seite');add.clicked.connect(self.add_page);footer.addWidget(add);self.status=QLabel('Bereit');footer.addWidget(self.status,1);self.zoom=QSpinBox();self.zoom.setRange(5,800);self.zoom.setSuffix(' %');self.zoom.setValue(100);self.zoom.valueChanged.connect(self.canvas.zoom);self.canvas.zoom_changed.connect(self.zoom.setValue);footer.addWidget(self.zoom);fit=QPushButton('Einpassen');fit.clicked.connect(self.fit);footer.addWidget(fit);root.addLayout(footer)
        self.filter_shapes('');self.refresh();self.initial_fit=QTimer(self);self.initial_fit.setSingleShot(True);self.initial_fit.timeout.connect(self.fit);self.initial_fit.start(0)
        self.autosave=QTimer(self);self.autosave.setInterval(30000);self.autosave.timeout.connect(self.save_recovery);self.autosave.start()
        if self.recovery and self.recovery.exists():QTimer.singleShot(0,self.offer_recovery)
    def action(self,menu,label,fn,key=None):
        a=QAction(label,self);a.triggered.connect(lambda checked=False:fn());menu.addAction(a);self.actions[label]=a
        if key:a.setShortcut(QKeySequence(key));a.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut);self.addAction(a)
        return a
    def filter_shapes(self,query):
        self.shapes.clear();cat=self.category.currentText()
        for key,(title,group) in SHAPES.items():
            if query.casefold() not in title.casefold() or cat not in ('Alle',group) or key=='image':continue
            item=QListWidgetItem(shape_icon(key),title);item.setData(Qt.ItemDataRole.UserRole,key);self.shapes.addItem(item)
    def build_properties(self):
        container=QWidget();form=QFormLayout(container);self.prop={}
        for label,key,lo,hi in [('X','x',-100000,100000),('Y','y',-100000,100000),('Breite','w',20,50000),('Höhe','h',20,50000),('Drehung','rotation',-360,360),('Linienstärke','line_width',.1,30),('Schriftgröße','font_size',5,300),('Deckkraft %','opacity',0,100),('Label X','label_x',-10000,10000),('Label Y','label_y',-10000,10000)]:
            control=QDoubleSpinBox();control.setRange(lo,hi);control.setDecimals(1);control.editingFinished.connect(lambda key=key,c=control:self.set_property(key,c.value()));form.addRow(label,control);self.prop[key]=control
        for label,key in [('Füllfarbe','fill'),('Linienfarbe','stroke'),('Textfarbe','text_color')]:
            b=QPushButton('Wählen …');b.clicked.connect(lambda checked=False,key=key:self.color(key));form.addRow(label,b)
        transparent=QPushButton('Füllung transparent');transparent.clicked.connect(lambda:self.set_property('fill','none'));form.addRow(transparent)
        self.font=QFontComboBox();self.font.currentFontChanged.connect(lambda f:self.set_property('font',f.family()));form.addRow('Schrift',self.font)
        for label,key in [('Fett','bold'),('Kursiv','italic'),('Gestrichelt','dashed')]:
            c=QCheckBox(label);c.toggled.connect(lambda v,key=key:self.set_property(key,v));self.prop[key]=c;form.addRow(c)
        for label,key,choices in [('Textausrichtung','align',[('Links','left'),('Mitte','center'),('Rechts','right')]),('Linienart','route',[('Gerade','straight'),('Rechtwinklig','orthogonal'),('Kurve','curved')]),('Anfang','start',[('Keine','none'),('Pfeil','arrow'),('Offener Pfeil','open'),('Raute','diamond'),('Kreis','circle'),('Genau eins','one'),('Viele','many'),('Null oder eins','zero_one'),('Null oder viele','zero_many')]),('Ende','end',[('Keine','none'),('Pfeil','arrow'),('Offener Pfeil','open'),('Raute','diamond'),('Kreis','circle'),('Genau eins','one'),('Viele','many'),('Null oder eins','zero_one'),('Null oder viele','zero_many')]),('Quellanschluss','source_port',[('Automatisch','auto'),('Links','left'),('Rechts','right'),('Oben','top'),('Unten','bottom')]),('Zielanschluss','target_port',[('Automatisch','auto'),('Links','left'),('Rechts','right'),('Oben','top'),('Unten','bottom')])]:
            box=QComboBox()
            for title,value in choices:box.addItem(title,value)
            box.currentIndexChanged.connect(lambda _,key=key,b=box:self.set_property(key,b.currentData()));form.addRow(label,box);self.prop[key]=box
        reset=QPushButton('Wegpunkte zurücksetzen');reset.clicked.connect(lambda:self.set_property('points',[]));form.addRow(reset)
        edit=QPushButton('Text / Tabellenfelder …');edit.clicked.connect(self.edit_selected);form.addRow(edit)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(container);self.right.addTab(scroll,'Format')
    def build_layers(self):
        panel=QWidget();layout=QVBoxLayout(panel);self.layers=QListWidget();self.layers.currentRowChanged.connect(self.select_layer);self.layers.itemChanged.connect(self.layer_visible);layout.addWidget(self.layers)
        for text,fn in [('+ Ebene',self.add_layer),('Umbenennen',self.rename_layer),('Ebene löschen',self.delete_layer),('Ebene sperren / entsperren',self.lock_layer),('Ebene nach oben',lambda:self.move_layer(1)),('Ebene nach unten',lambda:self.move_layer(-1)),('Auswahl auf diese Ebene',self.move_selection_layer)]:
            b=QPushButton(text);b.clicked.connect(fn);layout.addWidget(b)
        layout.addStretch();self.right.addTab(panel,'Ebenen')
    def records(self):
        keys=set(self.scene.selected_ids());return [i for i in self.doc.page['nodes']+self.doc.page['edges'] if i['id'] in keys]
    def mutate(self,fn,select=None):
        keys=self.scene.selected_ids() if select is None else select
        try:self.doc.change(fn);self.refresh(keys)
        except Exception as exc:QMessageBox.warning(self,'ReDrawko',str(exc));self.refresh()
    def changed(self):self.filename.setText(('* ' if self.doc.dirty else '')+(Path(self.doc.path).name if self.doc.path else 'Neues Diagramm'));self.actions['Rückgängig'].setEnabled(bool(self.doc.undo));self.actions['Wiederholen'].setEnabled(bool(self.doc.redo));self.selection_changed()
    def refresh(self,selection=()):
        self.updating=True;self.scene.reload(selection);self.pages.blockSignals(True);self.pages.clear()
        for p in self.doc.data['pages']:self.pages.addItem(p['name'],p['id'])
        self.pages.setCurrentIndex(self.pages.findData(self.doc.data['active_page']));self.pages.blockSignals(False);self.layers.blockSignals(True);self.layers.clear()
        for l in reversed(self.doc.page['layers']):
            item=QListWidgetItem(('🔒 ' if l['locked'] else '')+l['name']);item.setData(Qt.ItemDataRole.UserRole,l['id']);item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable);item.setCheckState(Qt.CheckState.Checked if l['visible'] else Qt.CheckState.Unchecked);self.layers.addItem(item)
            if l['id']==self.doc.page['active_layer']:self.layers.setCurrentItem(item)
        self.layers.blockSignals(False);self.updating=False;self.changed()
    def selection_changed(self):
        if self.updating or not hasattr(self,'prop'):return
        records=self.records();self.updating=True
        try:
            item=records[0] if records else {}
            for key,control in self.prop.items():
                control.setEnabled(key in item)
                if key not in item:continue
                if isinstance(control,QDoubleSpinBox):control.setValue(item[key])
                elif isinstance(control,QCheckBox):control.setChecked(item[key])
                else:control.setCurrentIndex(control.findData(item[key]))
            if 'font' in item:self.font.setCurrentFont(QFont(item['font']))
            if hasattr(self,'status'):self.status.setText(f"{len(records)} ausgewählt · {len(self.doc.page['nodes'])} Formen · {len(self.doc.page['edges'])} Verbindungen")
        finally:self.updating=False
    def set_property(self,key,value):
        if self.updating:return
        records=self.records()
        if not records:return
        self.mutate(lambda:[r.update({key:copy.deepcopy(value)}) for r in records if key in r])
    def color(self,key):
        records=self.records()
        if not records:return
        c=QColorDialog.getColor(QColor(records[0].get(key,'#ffffff')),self,'Farbe')
        if c.isValid():self.set_property(key,c.name())
    def add_shape(self,shape,point=None):
        if shape not in SHAPES:return
        l=next(l for l in self.doc.page['layers'] if l['id']==self.doc.page['active_layer'])
        if l['locked'] or not l['visible']:self.status.setText('Aktive Ebene zuerst entsperren und einblenden.');return
        point=point or self.canvas.mapToScene(self.canvas.viewport().rect().center());n=node(shape,point.x()-80,point.y()-45,l['id']);self.mutate(lambda:self.doc.page['nodes'].append(n),[n['id']])
    def connect_mode(self,enabled):
        self.canvas.connecting=enabled;self.canvas.source=None;self.status.setText('Quellform und anschließend Zielform anklicken.' if enabled else 'Auswählen und verschieben.')
    def connect_nodes(self,a,b,source_port='auto',target_port='auto'):
        e=edge(a,b,self.doc.page['active_layer']);e['route']=self.route.currentData()
        e.update(source_port=source_port,target_port=target_port)
        lookup={n['id']:n for n in self.doc.page['nodes']}
        if lookup[a]['shape']=='entity' and lookup[b]['shape']=='entity':e['start']='one';e['end']='many'
        self.mutate(lambda:self.doc.page['edges'].append(e),[e['id']])
    def schema_layout(self):
        from sql_schema import layout
        self.mutate(lambda:layout(self.doc.page));self.fit()
    def ai_layout(self):
        from sql_ai import SQLAI
        from sql_schema import layout
        editor=QPlainTextEdit();names=[n['text'] for n in self.doc.page['nodes']];editor.setPlainText(json.dumps({'order':names},ensure_ascii=False))
        dialog=SQLAI(editor,self,layout=True)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            try:
                order=json.loads(editor.toPlainText())['order']
                if len(order)!=len(names) or sorted(order)!=sorted(names):raise ValueError('Der Vorschlag muss alle Tabellennamen unverändert enthalten.')
                self.mutate(lambda:layout(self.doc.page,order));self.fit()
            except Exception as exc:QMessageBox.warning(self,'KI-Anordnung',str(exc))
    def sql_assistant(self):
        from sql_ai import SQLAI
        try:script=sql_export(self.doc.page)
        except Exception as exc:QMessageBox.warning(self,'SQL',str(exc));return
        editor=QPlainTextEdit();editor.setPlainText(script);dialog=SQLAI(editor,self,self.doc.page.get('sql_dialect','sqlite'))
        if dialog.exec()==QDialog.DialogCode.Accepted:
            try:
                from sql_schema import parse_schema
                p=parse_schema(editor.toPlainText(),self.doc.page.get('sql_dialect','sqlite'))
                self.mutate(lambda:(self.doc.data['pages'].append(p),self.doc.data.update(active_page=p['id'])));self.fit()
            except Exception as exc:QMessageBox.warning(self,'SQL-Vorschlag',str(exc))
    def edit_selected(self):
        items=self.records()
        if items:self.edit_object(items[0]['id'])
    def edit_object(self,key):
        item=next((r for r in self.doc.page['nodes']+self.doc.page['edges'] if r['id']==key),None)
        if not item:return
        dialog=QDialog(self);dialog.setWindowTitle('Beschriftung und Attribute');dialog.resize(620,500);layout=QVBoxLayout(dialog)
        if item.get('shape')=='entity':
            title=QLineEdit(item['text']);layout.addWidget(QLabel('Tabellenname'));layout.addWidget(title);table=QTableWidget(len(item['rows']),4);table.setHorizontalHeaderLabels(['Attribut','Datentyp','Schlüssel (PK / FK / UQ)','NULL erlaubt']);table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);layout.addWidget(table,1)
            for row,field in enumerate(item['rows']):
                for col,value in enumerate([field['name'],field.get('type',''),field.get('key',''),'Ja' if field.get('nullable') else 'Nein']):table.setItem(row,col,QTableWidgetItem(value))
                table.item(row,0).setData(Qt.ItemDataRole.UserRole,copy.deepcopy(field))
            actions=QHBoxLayout();layout.addLayout(actions)
            for label,fn in [('+ Attribut',lambda:table.insertRow(table.rowCount())),('− Attribut',lambda:table.removeRow(table.currentRow())),('↑',lambda:self.move_row(table,-1)),('↓',lambda:self.move_row(table,1))]:b=QPushButton(label);b.clicked.connect(fn);actions.addWidget(b)
        else:
            text=QPlainTextEdit(item.get('text',''));layout.addWidget(text,1)
            if 'source' in item:
                source=QLineEdit(item.get('source_label',''));target=QLineEdit(item.get('target_label',''));form=QFormLayout();form.addRow('Quellbeschriftung',source);form.addRow('Zielbeschriftung',target);layout.addLayout(form)
                fk=item.get('sql_fk',{});fk_source=QLineEdit(', '.join(fk.get('columns',[])));fk_target=QLineEdit(', '.join(fk.get('target_columns',[])));form.addRow('FK-Quellspalten (Komma)',fk_source);form.addRow('Referenzierte Zielspalten',fk_target)
                form.addRow(QLabel('Beide Felder leer: nur grafische Verbindung. SQL: Quelle referenziert Ziel.'))
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        def apply():
            if item.get('shape')=='entity':
                def cell(r,c):return table.item(r,c).text().strip() if table.item(r,c) else ''
                item['text']=title.text();rows=[];renames={}
                for r in range(table.rowCount()):
                    if not cell(r,0):continue
                    original=table.item(r,0).data(Qt.ItemDataRole.UserRole) or {};row=dict(original)
                    if original.get('name'):renames[original['name']]=cell(r,0)
                    row.update(name=cell(r,0),type=cell(r,1),key=cell(r,2).upper(),nullable=cell(r,3).casefold() in ('ja','yes','1','true'));rows.append(row)
                item['rows']=rows;item['h']=max(item['h'],42+26*len(rows))
                for link in self.doc.page['edges']:
                    if not link.get('sql_fk'):continue
                    for endpoint,column in [('source','columns'),('target','target_columns')]:
                        if link[endpoint]==item['id']:link['sql_fk'][column]=[renames.get(k,k) for k in link['sql_fk'][column]]
            else:
                item['text']=text.toPlainText()
                if 'source' in item:
                    item['source_label']=source.text();item['target_label']=target.text();a=[v.strip() for v in fk_source.text().split(',') if v.strip()];b=[v.strip() for v in fk_target.text().split(',') if v.strip()]
                    lookup={n['id']:n for n in self.doc.page['nodes']}
                    if a or b:
                        if len(a)!=len(b) or not set(a)<={r['name'] for r in lookup[item['source']].get('rows',[])} or not set(b)<={r['name'] for r in lookup[item['target']].get('rows',[])}:raise ValueError('Die FK-Spalten müssen in Quelle und Ziel existieren und gleich viele sein.')
                        item['sql_fk']=dict(item.get('sql_fk',{}),columns=a,target_columns=b,name=item.get('sql_fk',{}).get('name',''),options=item.get('sql_fk',{}).get('options',[]));item.update(start='many',end='one')
                    else:item.pop('sql_fk',None)
        self.mutate(apply,[key])
    def move_row(self,table,offset):
        row=table.currentRow();target=row+offset
        if row<0 or not 0<=target<table.rowCount():return
        for c in range(table.columnCount()):a=table.takeItem(row,c);b=table.takeItem(target,c);table.setItem(row,c,b or QTableWidgetItem(''));table.setItem(target,c,a or QTableWidgetItem(''))
        table.setCurrentCell(target,0)
    def delete(self):self.mutate(lambda:self.doc.delete(set(self.scene.selected_ids())))
    def duplicate(self):
        keys=self.scene.selected_ids();selection=[];self.mutate(lambda:selection.extend(self.doc.duplicate(keys)),selection)
    def select_all(self):
        for item in list(self.scene.nodes.values())+list(self.scene.edges.values()):item.setSelected(True)
    def copy(self):
        keys=set(self.scene.selected_ids());nodes=[copy.deepcopy(n) for n in self.doc.page['nodes'] if n['id'] in keys];ids={n['id'] for n in nodes};edges=[copy.deepcopy(e) for e in self.doc.page['edges'] if e['source'] in ids and e['target'] in ids]
        if not nodes:return
        mime=QMimeData();mime.setData('application/x-redrawko',json.dumps(dict(nodes=nodes,edges=edges)).encode());QApplication.clipboard().setMimeData(mime)
    def cut(self):self.copy();self.delete()
    def paste(self):
        mime=QApplication.clipboard().mimeData()
        if not mime.hasFormat('application/x-redrawko'):return
        try:
            raw=bytes(mime.data('application/x-redrawko'))
            if len(raw)>50_000_000:raise ValueError('Zwischenablage zu groß.')
            content=json.loads(raw);mapping={n['id']:uid() for n in content['nodes']};selected=[];groups={n.get('group'):uid() for n in content['nodes'] if n.get('group')}
            def apply():
                for n in content['nodes']:n['id']=mapping[n['id']];n['x']+=30;n['y']+=30;n['layer']=self.doc.page['active_layer'];n['group']=groups.get(n.get('group'),'');self.doc.page['nodes'].append(n);selected.append(n['id'])
                for e in content['edges']:e['id']=uid();e['source']=mapping[e['source']];e['target']=mapping[e['target']];e['layer']=self.doc.page['active_layer'];e['points']=[[x+30,y+30] for x,y in e['points']];self.doc.page['edges'].append(e)
            self.mutate(apply,selected)
        except Exception as exc:QMessageBox.warning(self,'Einfügen',str(exc))
    def history(self,redo):self.doc.history(redo);self.refresh()
    def group(self,on):
        group=uid() if on else '';records=self.records();self.mutate(lambda:[r.update(group=group) for r in records if 'shape' in r])
    def zorder(self,offset):
        records=self.records();self.mutate(lambda:[r.update(z=r.get('z',0)+offset) for r in records])
    def lock(self):
        records=[r for r in self.records() if 'shape' in r];value=not all(r.get('locked') for r in records);self.mutate(lambda:[r.update(locked=value) for r in records])
    def align(self,kind):
        nodes=[r for r in self.records() if 'shape' in r]
        if len(nodes)<2:return
        left=min(n['x'] for n in nodes);right=max(n['x']+n['w'] for n in nodes);top=min(n['y'] for n in nodes);bottom=max(n['y']+n['h'] for n in nodes)
        def apply():
            for n in nodes:
                if kind in ('left','center','right'):n['x']={'left':left,'center':(left+right-n['w'])/2,'right':right-n['w']}[kind]
                else:n['y']={'top':top,'middle':(top+bottom-n['h'])/2,'bottom':bottom-n['h']}[kind]
        self.mutate(apply)
    def distribute(self,axis):
        nodes=sorted([r for r in self.records() if 'shape' in r],key=lambda r:r[axis])
        if len(nodes)<3:return
        start,end=nodes[0][axis],nodes[-1][axis];self.mutate(lambda:[n.update({axis:start+i*(end-start)/(len(nodes)-1)}) for i,n in enumerate(nodes)])
    def layout_nodes(self,kind):
        nodes=[r for r in self.records() if 'shape' in r] or self.doc.page['nodes']
        if not nodes:return
        def apply():
            levels={};incoming={n['id']:[] for n in nodes}
            for e in self.doc.page['edges']:
                if e['source'] in incoming and e['target'] in incoming:incoming[e['target']].append(e['source'])
            for _ in nodes:
                for n in nodes:
                    if n['id'] not in levels and all(s in levels for s in incoming[n['id']]):levels[n['id']]=max([levels[s]+1 for s in incoming[n['id']]] or [0])
            rows={}
            for i,n in enumerate(nodes):
                if kind=='circle':a=2*math.pi*i/len(nodes);n['x']=700+500*math.cos(a)-n['w']/2;n['y']=450+330*math.sin(a)-n['h']/2
                elif kind=='tree':depth=levels.get(n['id'],0);row=rows.get(depth,0);rows[depth]=row+1;n['x']=100+row*320;n['y']=100+depth*230
                else:n['x']=100+(i%4)*320;n['y']=100+(i//4)*230
        self.mutate(apply);self.fit()
    def current_layer(self):return next(l for l in self.doc.page['layers'] if l['id']==self.doc.page['active_layer'])
    def select_layer(self,row):
        if self.updating or row<0:return
        self.doc.page['active_layer']=self.layers.item(row).data(Qt.ItemDataRole.UserRole)
    def layer_visible(self,item):
        if self.updating:return
        key=item.data(Qt.ItemDataRole.UserRole);self.mutate(lambda:next(l for l in self.doc.page['layers'] if l['id']==key).update(visible=item.checkState()==Qt.CheckState.Checked))
    def add_layer(self):
        l=layer('Ebene '+str(len(self.doc.page['layers'])+1));self.mutate(lambda:(self.doc.page['layers'].append(l),self.doc.page.update(active_layer=l['id'])))
    def rename_layer(self):
        l=self.current_layer();text,ok=QInputDialog.getText(self,'Ebene','Name:',text=l['name'])
        if ok:self.mutate(lambda:l.update(name=text or 'Ebene'))
    def delete_layer(self):
        p=self.doc.page;l=self.current_layer()
        if len(p['layers'])==1:return
        if QMessageBox.question(self,'Ebene löschen','Ebene und ihre Diagrammobjekte löschen?')!=QMessageBox.StandardButton.Yes:return
        def apply():
            self.doc.delete({r['id'] for r in p['nodes']+p['edges'] if r['layer']==l['id']});p['layers'].remove(l);p['active_layer']=p['layers'][0]['id']
        self.mutate(apply)
    def lock_layer(self):l=self.current_layer();self.mutate(lambda:l.update(locked=not l['locked']))
    def move_layer(self,offset):
        p=self.doc.page;l=self.current_layer();i=p['layers'].index(l);j=max(0,min(len(p['layers'])-1,i+offset))
        def apply():p['layers'].insert(j,p['layers'].pop(i))
        self.mutate(apply)
    def move_selection_layer(self):self.set_property('layer',self.doc.page['active_layer'])
    def add_page(self):
        p=page('Seite '+str(len(self.doc.data['pages'])+1));self.mutate(lambda:(self.doc.data['pages'].append(p),self.doc.data.update(active_page=p['id'])));self.fit()
    def duplicate_page(self):
        p=copy.deepcopy(self.doc.page);mapping={key:uid() for key in [p['id']]+[l['id'] for l in p['layers']]+[n['id'] for n in p['nodes']]+[e['id'] for e in p['edges']]}
        p['id']=mapping[p['id']];p['name']+=' – Kopie';p['active_layer']=mapping[p['active_layer']]
        for obj in p['layers']+p['nodes']+p['edges']:
            for k in ('id','layer','source','target'):
                if k in obj:obj[k]=mapping[obj[k]]
        self.mutate(lambda:(self.doc.data['pages'].append(p),self.doc.data.update(active_page=p['id'])))
    def rename_page(self):
        p=self.doc.page;text,ok=QInputDialog.getText(self,'Seite','Name:',text=p['name'])
        if ok:self.mutate(lambda:p.update(name=text or 'Seite'))
    def delete_page(self):
        if len(self.doc.data['pages'])==1:return
        if QMessageBox.question(self,'Seite löschen','Aktuelle Seite einschließlich aller Objekte löschen?')!=QMessageBox.StandardButton.Yes:return
        p=self.doc.page;self.mutate(lambda:(self.doc.data['pages'].remove(p),self.doc.data.update(active_page=self.doc.data['pages'][0]['id'])))
    def switch_page(self,index):
        if self.updating or index<0:return
        self.doc.data['active_page']=self.pages.itemData(index);self.refresh();self.fit()
    def page_settings(self):
        dialog=QDialog(self);dialog.setWindowTitle('Seiteneinstellungen');form=QFormLayout(dialog);p=self.doc.page;w=QSpinBox();w.setRange(100,50000);w.setValue(round(p['width']));h=QSpinBox();h.setRange(100,50000);h.setValue(round(p['height']));grid=QSpinBox();grid.setRange(5,200);grid.setValue(p['grid_size']);color=QLineEdit(p['background']);form.addRow('Breite (px)',w);form.addRow('Höhe (px)',h);form.addRow('Rasterabstand',grid);form.addRow('Hintergrundfarbe',color);buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);form.addRow(buttons)
        if dialog.exec()==QDialog.DialogCode.Accepted and QColor(color.text()).isValid():self.mutate(lambda:p.update(width=w.value(),height=h.value(),grid_size=grid.value(),background=color.text()));self.fit()
    def toggle_grid(self):self.mutate(lambda:self.doc.page.update(grid=not self.doc.page['grid']))
    def toggle_snap(self):self.mutate(lambda:self.doc.page.update(snap=not self.doc.page['snap']))
    def toggle_panels(self):show=self.library.isHidden();self.library.setVisible(show);self.right.setVisible(show)
    def fit(self):self.canvas.fitInView(QRectF(0,0,self.doc.page['width'],self.doc.page['height']),Qt.AspectRatioMode.KeepAspectRatio);self.zoom.blockSignals(True);self.zoom.setValue(round(self.canvas.transform().m11()*100));self.zoom.blockSignals(False)
    def search_replace(self):
        query,ok=QInputDialog.getText(self,'Suchen','Text auf der aktuellen Seite suchen:')
        if not ok or not query:return
        matches=[r for r in self.doc.page['nodes']+self.doc.page['edges'] if query.casefold() in r.get('text','').casefold()];self.scene.clearSelection()
        for r in matches:
            item=self.scene.nodes.get(r['id']) or self.scene.edges.get(r['id'])
            if item:item.setSelected(True)
        replacement,ok=QInputDialog.getText(self,'Ersetzen',f'{len(matches)} Treffer. Ersetzen durch (Abbrechen = nur markieren):')
        if ok:self.mutate(lambda:[r.update(text=__import__('re').sub(__import__('re').escape(query),lambda _:replacement,r['text'],flags=__import__('re').I)) for r in matches])
    def object_data(self):
        items=self.records()
        if not items or 'shape' not in items[0]:return
        item=items[0];dialog=QDialog(self);form=QFormLayout(dialog);link=QLineEdit(item.get('link',''));data=QPlainTextEdit(json.dumps(item.get('data',{}),ensure_ascii=False,indent=2));form.addRow('Link (wird nur gespeichert)',link);form.addRow('Eigenschaften als JSON',data);buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);form.addRow(buttons)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            try:
                value=json.loads(data.toPlainText())
                if not isinstance(value,dict):raise ValueError('Eigenschaften müssen ein JSON-Objekt sein.')
                self.mutate(lambda:item.update(link=link.text(),data=value))
            except ValueError as exc:QMessageBox.warning(self,'Objektdaten',str(exc))
    def confirm(self):
        if not self.doc.dirty:return True
        result=QMessageBox.question(self,'Diagramm speichern?','Ungespeicherte Änderungen in ReDrawko speichern?',QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel)
        if result==QMessageBox.StandardButton.Save:return self.save()
        if result==QMessageBox.StandardButton.Discard:self.clear_recovery();return True
        return False
    def new(self):
        if not self.confirm():return
        self.doc=DiagramDocument();self.new_defaults();self.scene.doc=self.doc;self.refresh();self.fit()
    def new_defaults(self):
        if self.preferences is not None:
            for name in ('grid','snap'):self.doc.page[name]=self.preferences.value('redrawko/'+name,True,type=bool)
        self.doc.saved=self.doc.serial()
    def set_wallpaper(self,path,opacity):
        value=str(path) if path else None
        if getattr(self.scene,'wallpaper_path',None)!=value:
            self.scene.wallpaper_path=value;self.scene.wallpaper=QPixmap(value) if value else QPixmap()
        self.scene.wallpaper_opacity=opacity/100;self.scene.update()
    def open(self):
        if not self.confirm():return
        path=QFileDialog.getOpenFileName(self,'Diagramm öffnen','','ReDrawko (*.redrawko);;draw.io (*.drawio *.xml)')[0]
        if not path:return
        self.load_path(path)
    def load_path(self,path):
        try:
            doc=DiagramDocument()
            if Path(path).suffix.lower() in ('.drawio','.xml'):doc.data,warnings=drawio_import(path);doc.saved='';self.report_import(warnings)
            else:doc.load(path)
            self.doc=doc;self.scene.doc=doc;self.refresh();self.fit()
        except Exception as exc:QMessageBox.warning(self,'Öffnen fehlgeschlagen',str(exc))
    def save(self,as_new=False):
        path=None if as_new else self.doc.path
        if not path:path=QFileDialog.getSaveFileName(self,'Diagramm speichern','Diagramm.redrawko','ReDrawko (*.redrawko)')[0]
        if not path:return False
        if not Path(path).suffix:path+='.redrawko'
        try:self.doc.save(path);self.clear_recovery();self.changed();return True
        except Exception as exc:QMessageBox.warning(self,'Speichern fehlgeschlagen',str(exc));return False
    def choose_template(self):
        names={'Leer':'empty','ERM · Bestellsystem':'erm','Flussdiagramm':'flow','UML · Klassen':'uml','Netzwerk':'network','Mindmap':'mindmap'};name,ok=QInputDialog.getItem(self,'Vorlage','Neue Zeichnung aus Vorlage:',list(names),0,False)
        if not ok or not self.confirm():return
        self.doc=DiagramDocument();self.doc.data=self.store.templates().get(names[name],template(names[name])) if self.store else template(names[name]);self.scene.doc=self.doc;self.refresh();self.fit()
    def image_import(self):
        path=QFileDialog.getOpenFileName(self,'Bild einfügen','','Bilder (*.png *.jpg *.jpeg *.bmp *.webp)')[0]
        if not path:return
        from PIL import Image,ImageOps
        import io
        try:
            with Image.open(path) as source:
                if source.width*source.height>32_000_000:raise ValueError('Bild maximal 32 Millionen Pixel.')
                im=ImageOps.exif_transpose(source).convert('RGBA');stream=io.BytesIO();im.save(stream,'PNG');n=node('image',100,100,self.doc.page['active_layer']);n['image']=base64.b64encode(stream.getvalue()).decode();n['w']=min(600,im.width);n['h']=max(20,n['w']*im.height/im.width)
            self.mutate(lambda:self.doc.page['nodes'].append(n),[n['id']])
        except Exception as exc:QMessageBox.warning(self,'Bild einfügen',str(exc))
    def report_import(self,warnings):
        if warnings:QMessageBox.information(self,'Importhinweise','\n'.join(warnings[:15]))
    def import_drawio(self):
        if not self.confirm():return
        path=QFileDialog.getOpenFileName(self,'draw.io-Datei importieren','','draw.io (*.drawio *.xml)')[0]
        if path:self.load_path(path)
    def export_drawio(self):
        path=QFileDialog.getSaveFileName(self,'draw.io exportieren','Diagramm.drawio','draw.io (*.drawio)')[0]
        if path:self.io_action(lambda:drawio_export(self.doc.data,path))
    def import_sql(self):
        dialog=QDialog(self);dialog.setWindowTitle('SQL-Schema importieren');dialog.resize(700,450);layout=QVBoxLayout(dialog);text=QPlainTextEdit();text.setPlaceholderText('CREATE TABLE Kunde (id INTEGER PRIMARY KEY, name VARCHAR(100));');layout.addWidget(text);buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
        dialect=QComboBox();dialect.addItem('SQLite','sqlite');dialect.addItem('MySQL','mysql');dialect.addItem('SQL Server / Access-nahe DDL','tsql');layout.insertWidget(0,dialect)
        load=QPushButton('SQL-Datei laden');layout.insertWidget(1,load)
        def load_sql():
            path=QFileDialog.getOpenFileName(dialog,'SQL öffnen','','SQL (*.sql);;Text (*.txt)')[0]
            if path:
                try:text.setPlainText(Path(path).read_text(encoding='utf-8-sig'))
                except Exception as exc:QMessageBox.warning(dialog,'SQL',str(exc))
        load.clicked.connect(load_sql)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        try:
            from sql_schema import parse_schema
            p=parse_schema(text.toPlainText(),dialect.currentData());self.mutate(lambda:(self.doc.data['pages'].append(p),self.doc.data.update(active_page=p['id'])));self.fit();self.report_import(p.get('sql_warnings',[]))
        except Exception as exc:QMessageBox.warning(self,'SQL-Import',str(exc))
    def export_sql(self):
        path=QFileDialog.getSaveFileName(self,'SQL-Grundschema speichern','Schema.sql','SQL (*.sql)')[0]
        if path:self.io_action(lambda:atomic_write(path,sql_export(self.doc.page).encode('utf-8')))
    def export(self,kind):
        path=QFileDialog.getSaveFileName(self,'Aktuelle Seite exportieren','Diagramm.'+kind,kind.upper()+' (*.'+kind+')')[0]
        if not path:return
        scale=2
        if kind=='png':
            scale,ok=QInputDialog.getInt(self,'PNG-Export','Skalierung (1 = 100 %):',2,1,8)
            if not ok:return
        self.io_action(lambda:export_scene(self.scene,path,scale))
    def io_action(self,fn):
        try:fn();self.status.setText('Datei gespeichert.')
        except Exception as exc:QMessageBox.warning(self,'Dateiaktion fehlgeschlagen',str(exc))
    def save_recovery(self):
        if not self.recovery or not self.doc.dirty:return
        try:self.recovery.parent.mkdir(parents=True,exist_ok=True);atomic_write(self.recovery,self.doc.serial().encode('utf-8'))
        except OSError:self.status.setText('Wiederherstellungskopie konnte nicht geschrieben werden. Bitte manuell speichern.')
    def clear_recovery(self):
        if self.recovery and self.recovery.exists():self.recovery.unlink()
    def offer_recovery(self):
        if QMessageBox.question(self,'Diagramm wiederherstellen?','Eine ungespeicherte ReDrawko-Zeichnung wurde gefunden. Wiederherstellen?')==QMessageBox.StandardButton.Yes:
            try:self.doc.load(self.recovery);self.doc.path=None;self.doc.saved='';self.refresh();self.fit()
            except Exception as exc:QMessageBox.warning(self,'Wiederherstellung',str(exc))
    def shutdown(self):self.autosave.stop()
    def help(self):
        QMessageBox.information(self,'ReDrawko · Bedienung','Formen aus der Bibliothek ziehen oder doppelklicken. Ausgewählte Formen verschieben; am blauen Griff skalieren.\n\nVerbindung aktivieren und zwei Formen anklicken. Linien folgen den Formen. Doppelklick bearbeitet Beschriftungen oder ERM-Attribute. Strg+Doppelklick auf eine Linie fügt einen Wegpunkt hinzu; orange Griffe verschieben ihn. Im Formatbereich stehen Linienarten, Anschlüsse, Kardinalitäten und Beschriftungspositionen.\n\nStrg+Mausrad zoomt, mittlere Maustaste verschiebt die Ansicht. Alt bewegt ohne Raster. Bearbeiten enthält Kopieren, Gruppieren und Rückgängig. Anordnen richtet Objekte aus. Seiten und Ebenen trennen große Modelle.\n\n.redrawko speichert alle ReDrawko-Eigenschaften. PNG, SVG und PDF exportieren die aktuelle Seite. draw.io-Austausch unterstützt Grundformen, Texte und Verbindungen; Spezialformen werden mit Hinweis vereinfacht. SQL ist ein Grundschema und wird niemals ausgeführt.')
