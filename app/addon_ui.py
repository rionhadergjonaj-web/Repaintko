"""In-app installer and gallery for the optional Wallpaper+ data pack."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from PySide6.QtCore import Qt,QSize,QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,QLineEdit,QListWidget,QListWidgetItem,QSlider,QCheckBox,QProgressDialog,QMessageBox
from wallpaper_catalog import CATALOG,BY_ID
from wallpaper_addon import BUNDLE
from branding import is_activated

def wallpaper_icon():
    from PySide6.QtGui import QPixmap,QPainter,QColor,QPen,QPolygonF
    from PySide6.QtCore import QPointF,QRectF
    pix=QPixmap(112,112);pix.fill(Qt.GlobalColor.transparent);p=QPainter(pix);p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor('#467fd1'));p.drawRoundedRect(QRectF(5,8,94,84),12,12)
    p.setBrush(QColor('#ffe69a'));p.drawEllipse(QRectF(66,20,17,17));p.setBrush(QColor('#b3d9ef'))
    p.drawPolygon(QPolygonF([QPointF(7,77),QPointF(39,35),QPointF(73,81)]));p.setBrush(QColor('#47776e'))
    p.drawPolygon(QPolygonF([QPointF(8,91),QPointF(58,48),QPointF(98,91)]))
    p.setBrush(QColor('#63e6be'));p.setPen(QPen(QColor('#17252e'),3));p.drawEllipse(QRectF(70,70,38,38))
    p.setPen(QPen(QColor('#17252e'),4,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap));p.drawLine(80,89,98,89);p.drawLine(89,80,89,98);p.end();return pix

class AddonHub(QDialog):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.setWindowTitle('Repaintko · Add-ons');self.resize(720,380)
        root=QVBoxLayout(self);title=QLabel('Add-ons');title.setStyleSheet('font-size:26px;font-weight:bold;');root.addWidget(title)
        intro=QLabel('Mitgelieferte Erweiterungen verwalten – kein Download erforderlich');root.addWidget(intro)
        from PySide6.QtWidgets import QScrollArea,QWidget
        outer=root;area=QScrollArea();area.setWidgetResizable(True);container=QWidget();root=QVBoxLayout(container);area.setWidget(container);outer.addWidget(area,1);self.resize(760,min(650,self.screen().availableGeometry().height()-60))
        from PySide6.QtWidgets import QFrame
        card=QFrame();card.setFrameShape(QFrame.Shape.StyledPanel);row=QHBoxLayout(card);root.addWidget(card)
        logo=QLabel();logo.setPixmap(wallpaper_icon());row.addWidget(logo)
        details=QVBoxLayout();row.addLayout(details,1);name=QLabel('Wallpaper+');name.setStyleSheet('font-size:20px;font-weight:bold;');details.addWidget(name)
        description=QLabel('101 Hintergründe · 20 Farben für alle · 81 Plus-Motive\nAnime, Landschaften und der Oeschinensee');description.setWordWrap(True);details.addWidget(description)
        self.status=QLabel();details.addWidget(self.status);buttons=QHBoxLayout();details.addLayout(buttons)
        self.install_button=QPushButton();self.install_button.clicked.connect(self.toggle_install);buttons.addWidget(self.install_button)
        self.settings_button=QPushButton('Einstellungen');self.settings_button.clicked.connect(self.settings);buttons.addWidget(self.settings_button)
        diagram_card=QFrame();diagram_card.setFrameShape(QFrame.Shape.StyledPanel);diagram_row=QHBoxLayout(diagram_card);root.addWidget(diagram_card)
        from redraw_ui import shape_icon
        icon=QLabel();icon.setPixmap(shape_icon('entity').pixmap(112,90));diagram_row.addWidget(icon)
        diagram_details=QVBoxLayout();diagram_row.addLayout(diagram_details,1)
        label=QLabel('ReDrawko');label.setStyleSheet('font-size:20px;font-weight:bold;');diagram_details.addWidget(label)
        label=QLabel('Native Diagramme und ERM · Formen, Verbindungen, Ebenen und Seiten\nOffline im Repaintko-Design · für alle verfügbar');label.setWordWrap(True);diagram_details.addWidget(label)
        self.redraw_status=QLabel();diagram_details.addWidget(self.redraw_status)
        controls=QHBoxLayout();diagram_details.addLayout(controls)
        self.redraw_install=QPushButton();self.redraw_install.clicked.connect(self.toggle_redraw);controls.addWidget(self.redraw_install)
        self.redraw_settings=QPushButton('Einstellungen');self.redraw_settings.clicked.connect(self.diagram_settings);controls.addWidget(self.redraw_settings)
        self.redraw_open=QPushButton('Öffnen');self.redraw_open.clicked.connect(self.launch_redraw);controls.addWidget(self.redraw_open)
        data_card=QFrame();data_card.setFrameShape(QFrame.Shape.StyledPanel);data_row=QHBoxLayout(data_card);root.addWidget(data_card)
        logo=QLabel();logo.setPixmap(shape_icon('database').pixmap(112,90));data_row.addWidget(logo);details=QVBoxLayout();data_row.addLayout(details,1)
        title=QLabel('ReDataKo');title.setStyleSheet('font-size:20px;font-weight:bold;');details.addWidget(title)
        info=QLabel('Datenbank-Plugin · SQLite, MySQL, Access\nSQL-Editor, Daten, ERD, lokale KI, Import und Export');info.setWordWrap(True);details.addWidget(info)
        self.data_status=QLabel();details.addWidget(self.data_status);controls=QHBoxLayout();details.addLayout(controls)
        self.data_install=QPushButton();self.data_install.clicked.connect(self.toggle_data);controls.addWidget(self.data_install)
        self.data_open=QPushButton('Öffnen');self.data_open.clicked.connect(self.launch_data);controls.addWidget(self.data_open)
        self.data_settings=QPushButton('Einstellungen');self.data_settings.clicked.connect(self.data_options);controls.addWidget(self.data_settings)
        root.addStretch();close=QPushButton('Schließen');close.clicked.connect(self.accept);outer.addWidget(close,alignment=Qt.AlignmentFlag.AlignRight);self.refresh()
    def refresh(self):
        installed=self.window.wallpapers.installed();self.status.setText('Installiert' if installed else 'Nicht installiert')
        self.install_button.setText('Deinstallieren' if installed else 'Installieren');self.settings_button.setEnabled(installed)
        installed=self.window.redraw_store.installed();self.redraw_status.setText('Installiert' if installed else 'Nicht installiert')
        self.redraw_install.setText('Deinstallieren' if installed else 'Installieren');self.redraw_settings.setEnabled(installed);self.redraw_open.setEnabled(installed)
        self.window.redraw_action.setVisible(installed)
        installed=self.window.redata_store.installed();self.data_status.setText('Aktiviert · lokal enthalten' if installed else 'Bereits enthalten · noch nicht aktiviert');self.data_install.setText('Deaktivieren' if installed else 'Aktivieren');self.data_open.setEnabled(installed);self.data_settings.setEnabled(installed);self.window.redata_action.setVisible(installed)
    def toggle_data(self):
        try:
            if self.window.redata_store.installed():
                editor=self.window.redatako
                if editor is not None:
                    if not editor.confirm():return
                    if self.window.redata_active:self.window.leave_video_editor()
                    editor.shutdown();self.window.workspace.removeWidget(editor);editor.deleteLater();self.window.redatako=None
                self.window.redata_store.uninstall()
            else:self.window.redata_store.install()
        except Exception as exc:QMessageBox.warning(self,'ReDataKo',str(exc))
        self.refresh()
    def launch_data(self):self.accept();self.window.open_redatako()
    def data_options(self):
        QMessageBox.information(self,'ReDataKo · Einstellungen','Verbindungen werden direkt unter Verbinden eingerichtet. Standardmäßig ist der Schreibschutz aktiv, für MySQL zusätzlich TLS. Zugangsdaten werden nicht gespeichert. Datenbanken und SQL-Dateien bleiben bei Deinstallation erhalten. Den Hintergrund stellst du bei Wallpaper+ ein.')
    def toggle_redraw(self):
        try:
            if self.window.redraw_store.installed():
                editor=self.window.redrawko
                if editor is not None:
                    if not editor.confirm():return
                    if self.window.redraw_active:self.window.leave_video_editor()
                    editor.shutdown();self.window.workspace.removeWidget(editor);editor.deleteLater();self.window.redrawko=None
                self.window.redraw_store.uninstall()
            else:self.window.redraw_store.install()
        except Exception as exc:QMessageBox.warning(self,'ReDrawko',str(exc))
        self.refresh()
    def launch_redraw(self):
        self.accept();self.window.open_redrawko()
    def diagram_settings(self):
        dialog=QDialog(self);dialog.setWindowTitle('ReDrawko · Einstellungen');layout=QVBoxLayout(dialog)
        label=QLabel('Raster, Seitengröße, Farben und Verbindungen stellst du direkt im Diagramm ein.\nDen Hintergrund des Modus wählst du unter Wallpaper+ → Einstellungen.');label.setWordWrap(True);layout.addWidget(label)
        grid=QCheckBox('Raster bei neuen Diagrammen anzeigen');grid.setChecked(self.window.preferences.value('redrawko/grid',True,type=bool));layout.addWidget(grid)
        snap=QCheckBox('Neue Diagramme am Raster einrasten');snap.setChecked(self.window.preferences.value('redrawko/snap',True,type=bool));layout.addWidget(snap)
        save=QPushButton('Speichern');layout.addWidget(save)
        def apply():
            self.window.preferences.setValue('redrawko/grid',grid.isChecked());self.window.preferences.setValue('redrawko/snap',snap.isChecked());dialog.accept()
        save.clicked.connect(apply);dialog.exec()
    def toggle_install(self):
        dialog=AddonDialog(self.window)
        try:
            if self.window.wallpapers.installed():dialog.uninstall()
            else:dialog.install()
        finally:dialog.deleteLater();self.refresh()
    def settings(self):
        AddonDialog(self.window).exec();self.refresh()

class AddonDialog(QDialog):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.store=window.wallpapers;self.settings=window.preferences;self.busy=False
        self.setWindowTitle('Repaintko · Add-ons · Wallpaper+')
        available=window.screen().availableGeometry();self.resize(min(980,available.width()-40),min(740,available.height()-60))
        root=QVBoxLayout(self)
        title=QLabel('Wallpaper+');title.setStyleSheet('font-size:24px;font-weight:bold;');root.addWidget(title)
        intro=QLabel('101 Hintergründe: 20 Farben für alle · 40 Anime/Cartoon + 41 realistische Landschaften für Plus, inklusive Oeschinensee.\nDas Paket wird offline für dein Windows-Benutzerkonto installiert. Deine Zeichnungen bleiben unverändert.');intro.setWordWrap(True);root.addWidget(intro)
        row=QHBoxLayout();root.addLayout(row);self.status=QLabel();row.addWidget(self.status,1)
        self.install_button=QPushButton('Installieren');self.install_button.clicked.connect(self.install);row.addWidget(self.install_button)
        self.remove_button=QPushButton('Deinstallieren');self.remove_button.clicked.connect(self.uninstall);row.addWidget(self.remove_button)
        self.enabled=QCheckBox('Wallpaper+ aktiv');self.enabled.setChecked(self.settings.value('wallpaper/enabled',False,type=bool));self.enabled.toggled.connect(self.enable_changed);root.addWidget(self.enabled)
        from wallpaper_modes import MODES, selected_modes
        from PySide6.QtWidgets import QGroupBox, QGridLayout
        modes_box=QGroupBox('Wallpaper anzeigen in');modes_layout=QGridLayout(modes_box);root.addWidget(modes_box)
        selected=selected_modes(self.settings);self.mode_checks={}
        for index,(key,label) in enumerate(MODES):
            check=QCheckBox(label);check.setChecked(key in selected);self.mode_checks[key]=check
            modes_layout.addWidget(check,index//3,index%3);check.toggled.connect(self.modes_changed)
        modes_box.setToolTip('Gilt für den Hintergrund der Oberfläche. Dokumente, Videobilder und Webseiten bleiben unverändert. ReDrawko gilt, sobald der Modus verfügbar ist.')
        filters=QHBoxLayout();root.addLayout(filters)
        self.category=QComboBox()
        for text,value in [('Alle (101)','all'),('Farben (20)','color'),('Anime / Cartoon · Plus (40)','anime'),('Realistisch · Plus (41)','realistic')]:self.category.addItem(text,value)
        self.category.currentIndexChanged.connect(self.refresh_gallery);filters.addWidget(self.category)
        self.search=QLineEdit();self.search.setPlaceholderText('Wallpaper suchen …');self.search.textChanged.connect(self.refresh_gallery);filters.addWidget(self.search,1)
        self.gallery=QListWidget();self.gallery.setViewMode(QListWidget.ViewMode.IconMode);self.gallery.setResizeMode(QListWidget.ResizeMode.Adjust);self.gallery.setMovement(QListWidget.Movement.Static);self.gallery.setIconSize(QSize(176,99));self.gallery.setGridSize(QSize(208,140));self.gallery.setWordWrap(True);self.gallery.itemDoubleClicked.connect(lambda _:self.apply());root.addWidget(self.gallery,1)
        self.credit=QLabel();self.credit.setWordWrap(True);self.credit.setOpenExternalLinks(True);root.addWidget(self.credit);self.gallery.currentItemChanged.connect(self.show_credit)
        opacity_row=QHBoxLayout();root.addLayout(opacity_row);opacity_row.addWidget(QLabel('Hintergrund-Deckkraft'))
        self.opacity=QSlider(Qt.Orientation.Horizontal);self.opacity.setRange(0,100);self.opacity.setValue(self.settings.value('wallpaper/opacity',100,type=int));opacity_row.addWidget(self.opacity,1)
        self.opacity_label=QLabel(f'{self.opacity.value()} %');self.opacity_label.setMinimumWidth(45);opacity_row.addWidget(self.opacity_label);self.opacity.valueChanged.connect(self.opacity_changed)
        footer=QHBoxLayout();root.addLayout(footer)
        note=QLabel('Doppelklick zum Anwenden. Plus-Motive sind für alle als Vorschau sichtbar.');note.setWordWrap(True);footer.addWidget(note,1)
        self.apply_button=QPushButton('Wallpaper anwenden');self.apply_button.clicked.connect(self.apply);footer.addWidget(self.apply_button)
        close=QPushButton('Schließen');close.clicked.connect(self.accept);footer.addWidget(close)
        self.refresh()

    def show_credit(self,entry,*args):
        from html import escape
        item=BY_ID.get(entry.data(Qt.ItemDataRole.UserRole),{}) if entry else {}
        if item.get('author'):
            self.credit.setText('Foto: '+escape(item['author'])+' · <a href="'+escape(item['source_url'],quote=True)+'">Original auf Wikimedia Commons</a> · <a href="'+item['license_url']+'">'+item['license']+'</a> · '+escape(item['changes']))
        else:self.credit.setText('KI-generierte Landschaft' if item.get('plus') else '')

    def refresh(self):
        installed=self.store.installed();self.status.setText('Installiert · Version 1' if installed else 'Noch nicht installiert')
        self.install_button.setText('Erneut installieren' if installed else 'Installieren');self.install_button.setEnabled(BUNDLE.is_file())
        if not BUNDLE.is_file():self.status.setText('Wallpaper-Paket fehlt – vollständiges Repaintko-Setup verwenden.')
        for control in (self.enabled,self.remove_button,self.gallery,self.opacity,self.apply_button):control.setEnabled(installed)
        self.refresh_gallery()

    def refresh_gallery(self,*args):
        self.gallery.clear()
        if not self.store.installed():return
        category=self.category.currentData();query=self.search.text().casefold();plus=is_activated(self.settings)
        selected=str(self.settings.value('wallpaper/selected','color_mint'))
        for item in CATALOG:
            if category not in ('all',item['category']) or query not in item['title'].casefold():continue
            path=self.store.image(item['id'],thumbnail=True)
            entry=QListWidgetItem(QIcon(str(path)) if path else QIcon(),item['title']+(' · Plus' if item['plus'] else ''))
            entry.setData(Qt.ItemDataRole.UserRole,item['id']);entry.setToolTip(item['title']+(' – Repaintko Plus erforderlich' if item['plus'] and not plus else ' – Doppelklick zum Anwenden'));self.gallery.addItem(entry)
            if item['id']==selected:self.gallery.setCurrentItem(entry)

    def enable_changed(self,value):
        self.settings.setValue('wallpaper/enabled',value);self.window.refresh_wallpaper()

    def modes_changed(self,*args):
        self.settings.setValue('wallpaper/modes',[key for key,check in self.mode_checks.items() if check.isChecked()]);self.window.refresh_wallpaper()

    def opacity_changed(self,value):
        self.opacity_label.setText(f'{value} %');self.settings.setValue('wallpaper/opacity',value);self.window.refresh_wallpaper()

    def apply(self):
        entry=self.gallery.currentItem()
        if not entry:return
        key=entry.data(Qt.ItemDataRole.UserRole)
        if BY_ID[key]['plus'] and not is_activated(self.settings):
            QMessageBox.information(self,'Repaintko Plus','Dieses Wallpaper benötigt Repaintko Plus. Aktivierung unter Datei → Repaintko Plus aktivieren. Die 20 Farb-Wallpaper kannst du ohne Plus verwenden.');return
        self.settings.setValue('wallpaper/selected',key);self.settings.setValue('wallpaper/enabled',True);self.enabled.setChecked(True);self.window.refresh_wallpaper();self.status.setText('Aktiv: '+BY_ID[key]['title'])

    def install(self):
        if self.busy:return
        self.busy=True;cancel=Event();progress=[0]
        dialog=QProgressDialog('Wallpaper+ wird installiert …','Abbrechen',0,100,self);dialog.setWindowModality(Qt.WindowModality.WindowModal);dialog.setAutoClose(False);dialog.setAutoReset(False);dialog.canceled.connect(cancel.set);dialog.setMinimumDuration(0)
        executor=ThreadPoolExecutor(max_workers=1);future=executor.submit(self.store.install,BUNDLE,lambda n:progress.__setitem__(0,n),cancel.is_set)
        timer=QTimer(dialog)
        def update():
            dialog.setValue(progress[0])
            if future.done():dialog.done(0)
        timer.timeout.connect(update);timer.start(40);dialog.exec()
        # Closing/cancelling never destroys a running extraction worker.
        if not future.done():
            cancel.set()
            from PySide6.QtCore import QEventLoop
            loop=QEventLoop();timer.timeout.disconnect();timer.timeout.connect(lambda:loop.quit() if future.done() else None);loop.exec()
        timer.stop();executor.shutdown(wait=True);self.busy=False
        try:
            future.result();self.settings.setValue('wallpaper/enabled',True)
            if not self.settings.value('wallpaper/selected',''):self.settings.setValue('wallpaper/selected','color_mint')
            self.enabled.setChecked(True)
        except InterruptedError:pass
        except Exception as exc:QMessageBox.warning(self,'Wallpaper+ konnte nicht installiert werden',str(exc))
        self.window.refresh_wallpaper();self.refresh()

    def uninstall(self):
        if self.busy:return
        # This removes only reinstallable pack data, never user drawings.
        self.settings.setValue('wallpaper/enabled',False);self.enabled.setChecked(False);self.window.refresh_wallpaper()
        try:self.store.uninstall()
        except Exception as exc:QMessageBox.warning(self,'Deinstallation fehlgeschlagen',str(exc))
        self.refresh()

    def reject(self):
        if not self.busy:super().reject()
