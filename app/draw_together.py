"""DrawTogether embedded workspace: discovery, session controls and shared canvas."""
import getpass,threading,time
from pathlib import Path
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt,Signal,QTimer,QSize
from PySide6.QtGui import QPainter,QColor,QAction,QKeySequence
from PySide6.QtNetwork import QNetworkInterface
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QStackedWidget,QLabel,QLineEdit,QPushButton,QListWidget,QListWidgetItem,QDialog,QFormLayout,QSpinBox,QCheckBox,QDialogButtonBox,QMessageBox,QInputDialog,QColorDialog,QScrollArea,QComboBox,QSplitter,QFileDialog,QApplication)
from document import Document
from draw_network import DrawServer,DrawClient,discover_servers

class DrawTogether(QWidget):
    returnRequested=Signal()
    job=Signal(str,object)
    statusSignal=Signal(str,bool)
    frameSignal=Signal(object,object,int)
    usersSignal=Signal(object)
    errorSignal=Signal(str)
    def __init__(self,parent=None,source=None):
        super().__init__(parent);self.source=source;self.server=None;self.client=None;self.active=None;self.online=False;self.color='#101820';self.meta=[];self.revision=0;self.saved_revision=-1;self.searching=False;self.working=False;self.generation=0
        self.job.connect(self.job_done);self.statusSignal.connect(self.status);self.frameSignal.connect(self.frame);self.usersSignal.connect(self.users);self.errorSignal.connect(self.error)
        layout=QVBoxLayout(self);top=QHBoxLayout();back=QPushButton('← Bild / GIF');back.clicked.connect(self.returnRequested);top.addWidget(back);top.addWidget(QLabel('DrawTogether · gemeinsam zeichnen'));top.addStretch();layout.addLayout(top)
        self.pages=QStackedWidget();layout.addWidget(self.pages,1);lobby=QWidget();self.pages.addWidget(lobby);left=QVBoxLayout(lobby)
        self.username=QLineEdit(getpass.getuser());self.username.setMaxLength(40);form=QFormLayout();form.addRow('Dein Benutzername',self.username);self.network_mode=QComboBox();self.network_mode.addItems(['LAN / WLAN','Online']);form.addRow('Verbindung',self.network_mode);self.network_mode.currentIndexChanged.connect(self.search);left.addLayout(form)
        buttons=QHBoxLayout();self.host_button=QPushButton('Server hosten');self.host_button.clicked.connect(self.host_dialog);self.join_button=QPushButton('Server beitreten');self.join_button.clicked.connect(self.join);self.search_button=QPushButton('Erneut suchen');self.search_button.clicked.connect(self.search)
        for b in (self.host_button,self.join_button,self.search_button):buttons.addWidget(b)
        self.id_button=QPushButton('Über Raum-ID beitreten');self.id_button.clicked.connect(self.join_id);buttons.addWidget(self.id_button);left.addLayout(buttons);self.servers=QListWidget();self.servers.itemDoubleClicked.connect(lambda _:self.join());left.addWidget(self.servers,1)
        self.search_info=QLabel('Server im gleichen LAN/WLAN werden automatisch gesucht.');self.search_info.setWordWrap(True);left.addWidget(self.search_info)
        tip=QLabel('Beide PCs müssen im gleichen Netzwerk sein. Erlaube Repaintko in der Windows-Firewall für private Netzwerke. Gast-WLANs können Verbindungen zwischen Geräten sperren.');tip.setWordWrap(True);left.addWidget(tip)
        session=QWidget();self.pages.addWidget(session);body=QVBoxLayout(session);header=QHBoxLayout();self.status_label=QLabel('Verbinde …');self.status_label.setWordWrap(True);header.addWidget(self.status_label,1);self.save_button=QPushButton('Zeichnung speichern …');self.save_button.clicked.connect(self.save);header.addWidget(self.save_button);self.leave_button=QPushButton('Sitzung verlassen');self.leave_button.clicked.connect(self.leave);header.addWidget(self.leave_button);body.addLayout(header)
        from draw_editor import SharedPaintEditor
        self.editor=SharedPaintEditor(self);body.addWidget(self.editor,1)
        self.editor.setEnabled(False)
        self.user_list=QListWidget();self.user_list.setMaximumHeight(62);body.addWidget(self.user_list)
        management=QHBoxLayout();self.invite_button=QPushButton('Raum-ID kopieren');self.invite_button.clicked.connect(self.copy_invite);management.addWidget(self.invite_button);self.kick_button=QPushButton('Teilnehmer entfernen');self.kick_button.clicked.connect(self.kick);management.addWidget(self.kick_button);management.addStretch();body.addLayout(management)
        self.resync_button=QPushButton('Neu synchronisieren');self.resync_button.clicked.connect(self.editor.shared_bridge.resync);self.resync_button.hide();body.addWidget(self.resync_button)
        self.notice=QLabel('');self.notice.setWordWrap(True);body.addWidget(self.notice);self.search_timer=QTimer(self);self.search_timer.setInterval(4000);self.search_timer.timeout.connect(self.search);self.search_timer.start()
    def showEvent(self,event):super().showEvent(event);QTimer.singleShot(0,self.search)
    def error(self,message):self.editor.shared_bridge.fail(message)
    def search(self):
        if self.searching or self.working or self.pages.currentIndex()!=0 or not self.isVisible():return
        online=self.network_mode.currentIndex()==1;self.searching=True;self.search_info.setText('Suche Online-Räume …' if online else 'Suche Server im LAN …');targets=['255.255.255.255']
        for interface in QNetworkInterface.allInterfaces():
            for entry in interface.addressEntries():
                value=entry.broadcast().toString()
                if value:targets.append(value)
        def work():
            try:
                if online:
                    from draw_online import list_rooms
                    result=list_rooms()
                else:result=discover_servers(targets)
                self.job.emit('servers',result)
            except Exception as exc:self.job.emit('search_error',str(exc))
        threading.Thread(target=work,daemon=True).start()
    def job_done(self,kind,result):
        if kind=='network':
            generation,fn,args=result
            if generation==self.generation:fn(*args)
        elif kind=='servers':
            self.searching=False;selected=self.servers.currentItem();sid=selected.data(Qt.ItemDataRole.UserRole)['id'] if selected else None;self.servers.clear()
            for info in result:
                item=QListWidgetItem(info['name']+(f"  · {info['players']}/{info['maximum']}" if 'players' in info else '')+('  · Passwort' if info['locked'] else '  · Offen'));item.setData(Qt.ItemDataRole.UserRole,info);self.servers.addItem(item)
                if info['id']==sid:self.servers.setCurrentItem(item)
            self.search_info.setText(f'{len(result)} Server gefunden. Suche wird automatisch aktualisiert.')
        elif kind=='search_error':self.searching=False;self.search_info.setText(result)
        elif kind=='hosted':
            self.working=False;self.host_button.setEnabled(True);self.server,password=result;self.connect(dict(self.server.info(),host='127.0.0.1'),password)
        elif kind=='host_error':self.working=False;self.host_button.setEnabled(True);QMessageBox.warning(self,'Server konnte nicht starten',str(result))
        elif kind=='saved':self.working=False;self.save_button.setEnabled(True);self.saved_revision=result;self.notice.setText('Zeichnung gespeichert.')
        elif kind=='save_error':self.working=False;self.save_button.setEnabled(True);self.error(str(result))
    def host_dialog(self):
        if self.working:return
        dialog=QDialog(self);dialog.setWindowTitle('DrawTogether · Server hosten');layout=QFormLayout(dialog);title=QLineEdit('Gemeinsam zeichnen');title.setMaxLength(80);password=QLineEdit();password.setMaxLength(128);password.setEchoMode(QLineEdit.EchoMode.Password);password.setPlaceholderText('Leer lassen = ohne Passwort');use_current=QCheckBox('Kopie des aktuellen Bildes mit Ebenen verwenden');use_current.setChecked(True);w=QSpinBox();w.setRange(64,8192);w.setValue(1920);h=QSpinBox();h.setRange(64,8192);h.setValue(1080)
        maximum=QSpinBox();maximum.setRange(2,32);maximum.setValue(8);layout.addRow('Teilnehmerlimit',maximum);layout.addRow('Servername',title);layout.addRow('Passwort (optional)',password);layout.addRow(use_current);layout.addRow('Breite für neues Blatt',w);layout.addRow('Höhe für neues Blatt',h);buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addRow(buttons)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        if not self.username.text().strip():QMessageBox.information(self,'Benutzername','Gib zuerst deinen Benutzernamen ein.');return
        document=None
        if use_current.isChecked() and self.source:
            from draw_edits import clone
            document=clone(self.source())
        if self.network_mode.currentIndex()==1:
            from draw_state import SharedDrawing
            try:
                state=SharedDrawing(document,(w.value(),h.value())).export()
                self.connect(dict(online=True,create=True,state=state,name=title.text(),maximum=maximum.value()),password.text())
            except Exception as exc:QMessageBox.warning(self,'Online-Raum',str(exc))
            return
        self.working=True;self.host_button.setEnabled(False);self.search_info.setText('Lokaler Server wird gestartet …');server_name=title.text();secret=password.text();size=(w.value(),h.value());participant_limit=maximum.value()
        def work():
            try:self.job.emit('hosted',(DrawServer(server_name,secret,document,size,max_participants=participant_limit),secret))
            except Exception as exc:self.job.emit('host_error',str(exc))
        threading.Thread(target=work,daemon=True).start()
    def join_id(self):
        from draw_online import ENDPOINT
        room,ok=QInputDialog.getText(self,'Online-Raum','Raum-ID:')
        if not ok or not room.strip():return
        password,ok=QInputDialog.getText(self,'Online-Raum','Passwort (leer lassen bei offenem Raum):',QLineEdit.EchoMode.Password)
        if ok:self.connect(dict(id=room.strip(),name=room.strip(),online=True,endpoint=ENDPOINT),password)
    def join(self):
        if self.working:return
        item=self.servers.currentItem()
        if not item:self.search_info.setText('Wähle einen gefundenen Server aus.');return
        if not self.username.text().strip():self.search_info.setText('Gib zuerst deinen Benutzernamen ein.');return
        info=item.data(Qt.ItemDataRole.UserRole);password=''
        if info['locked']:
            password,ok=QInputDialog.getText(self,'Server beitreten',f'Passwort für {info["name"]}:',QLineEdit.EchoMode.Password)
            if not ok:return
        self.connect(info,password)
    def connect(self,info,password):
        if self.client:self.client.stop()
        self.editor.shared_bridge.reset();self.user_list.clear();self.online=False
        self.generation+=1;generation=self.generation;self.pages.setCurrentIndex(1);self.status_label.setText('Verbinde …');self.notice.clear();self.saved_revision=-1;self.meta=[];self.active=None;self.leave_button.setText('Server schließen' if self.server else 'Sitzung verlassen')
        def active(fn):
            def emit(*args):
                if generation==self.generation:self.job.emit('network',(generation,fn,args))
            return emit
        from draw_online import OnlineClient
        client_type=OnlineClient if info.get('online') else DrawClient
        self.online_host=bool(info.get('create'));self.leave_button.setText('Raum schließen' if self.online_host else ('Server schließen' if self.server else 'Sitzung verlassen'))
        self.client=client_type(info,self.username.text(),password,on_status=active(self.statusSignal.emit),on_frame=active(self.frameSignal.emit),on_users=active(self.usersSignal.emit),on_error=active(self.errorSignal.emit),document_frames=True,on_operation=active(self.editor.shared_bridge.preview),on_cursor=active(self.remote_cursor))
    def remote_cursor(self,message):
        import time
        if not hasattr(self.editor.canvas,"remote_cursors"):self.editor.canvas.remote_cursors={}
        self.editor.canvas.remote_cursors[message["identity"]]=(message,time.monotonic())
        self.editor.canvas.update()
    def status(self,message,online):
        self.online=online;self.status_label.setText(message)
        if not online and self.editor.canvas.start is not None:
            self.editor.doc.finish_stroke();self.editor.canvas.start=self.editor.canvas.last=self.editor.canvas.current=None;self.editor.refresh()
        self.editor.setEnabled(online or self.editor.shared_bridge.conflict)
    def frame(self,image,metadata,revision):
        self.revision=revision;self.meta=metadata;self.editor.shared_bridge.frame(image,revision)
    def users(self,users):
        selected=self.user_list.currentItem();selected_id=selected.data(Qt.ItemDataRole.UserRole) if selected else None
        self.user_list.clear()
        for u in users:
            item=QListWidgetItem(u['name']+(' (du)' if self.client and u['id']==self.client.identity else '')+(' · Host' if u.get('host') else ''))
            item.setData(Qt.ItemDataRole.UserRole,u['id']);self.user_list.addItem(item)
            if u['id']==selected_id:self.user_list.setCurrentItem(item)
        self.kick_button.setEnabled(bool(self.server or getattr(self,'online_host',False)))
        self.invite_button.setEnabled(bool(self.client and self.client.server.get('id')))
    def copy_invite(self):
        if self.client and self.client.server.get('id'):
            QApplication.clipboard().setText(self.client.server['id']);self.notice.setText('Raum-ID kopiert. Online: über „Raum-ID beitreten“ eingeben. Im LAN erscheint der Raum automatisch in der Suche.')
    def kick(self):
        item=self.user_list.currentItem()
        if not item or not self.client:return
        identity=item.data(Qt.ItemDataRole.UserRole)
        if identity==self.client.identity:return
        try:
            if self.server:self.server.kick(identity)
            elif getattr(self,'online_host',False):self.client.administer('kick',identity)
        except Exception as exc:self.notice.setText(str(exc))
    def save(self):
        if self.editor.save():self.saved_revision=self.revision
    def confirm_shutdown(self):
        if self.working:QMessageBox.information(self,'DrawTogether','Bitte den laufenden Start- oder Speichervorgang abwarten.');return False
        if not self.client:return True
        message='Den Server für alle Teilnehmer schließen?' if self.server else 'Die gemeinsame Sitzung verlassen?'
        if self.revision!=self.saved_revision:message+='\nDie gemeinsame Zeichnung ist lokal noch nicht gespeichert. Mit Abbrechen kannst du vorher „Zeichnung speichern“ wählen.'
        return QMessageBox.question(self,'DrawTogether',message,QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Cancel)==QMessageBox.StandardButton.Yes
    def shutdown(self):
        self.generation+=1
        if self.server:self.server.stop();self.server=None
        if self.client:
            if getattr(self,'online_host',False) and self.client.connected:
                try:self.client.administer('close')
                except Exception:pass
            self.client.stop();self.client=None
        self.online=False;self.editor.setEnabled(False);self.editor.shared_bridge.reset()
    def leave(self):
        if not self.confirm_shutdown():return
        self.shutdown();self.pages.setCurrentIndex(0);self.user_list.clear();self.search()
