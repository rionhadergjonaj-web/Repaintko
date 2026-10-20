"""ReBrowko: tabs, persistent website sessions, history and explicit password tools."""
import json
from pathlib import Path
from urllib.parse import urlencode
from PySide6.QtCore import Qt,QUrl,Signal,QTimer,QStandardPaths
from PySide6.QtGui import QAction,QKeySequence
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLineEdit,QLabel,QStackedWidget,QTabWidget,QDialog,QListWidget,QDialogButtonBox,QFormLayout,QMessageBox,QInputDialog
from PySide6.QtNetwork import QNetworkAccessManager,QNetworkRequest,QNetworkReply
from browser_store import BrowserStore,origin

def destination(text):
    text=text.strip()
    if not text:return QUrl('https://www.google.com/')
    if text.lower().startswith(('https://','http://')):return QUrl(text)
    if ' ' not in text and '.' in text and ':' not in text:return QUrl('https://'+text)
    return QUrl('https://www.google.com/search?'+urlencode({'q':text}))

# Only a user-clicked action reads/fills the top-level page. No page-to-native bridge.
READ_LOGIN="""(()=>{const visible=e=>e.getClientRects().length&&!e.disabled;
const p=[...document.querySelectorAll('input[type=password]')].find(visible);if(!p)return '';
const fields=[...(p.form||document).querySelectorAll('input')];
const u=fields.find(e=>visible(e)&&e.autocomplete==='username')||fields.find(e=>visible(e)&&['email','text'].includes(e.type));
return JSON.stringify({site:location.origin,user:u?u.value:'',password:p.value});})()"""
def fill_script(site,user,password):
    data=json.dumps(dict(site=site,user=user,password=password),ensure_ascii=True)
    return """(()=>{const d="""+data+""";if(location.origin!==d.site)return false;
const visible=e=>e.getClientRects().length&&!e.disabled&&!e.readOnly;
const p=[...document.querySelectorAll('input[type=password]')].find(visible);
const fields=[...(p&&p.form?p.form:document).querySelectorAll('input')];
const u=fields.find(e=>visible(e)&&e.autocomplete==='username')||fields.find(e=>visible(e)&&['email','text'].includes(e.type));
function set(e,v){const setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;setter.call(e,v);e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));}
if(u)set(u,d.user);if(p)set(p,d.password);return !!(u||p);})()"""

class Browser(QWidget):
    returnRequested=Signal()
    onlineChanged=Signal(bool)
    def __init__(self,parent=None,storage=None):
        super().__init__(parent);self.online=False;self.reply=None;self.profile=None;self.stopping=False
        self.store=BrowserStore(storage or Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))/'ReBrowko')
        root=QVBoxLayout(self);bar=QHBoxLayout();root.addLayout(bar)
        self.button(bar,'← Bild / GIF',self.returnRequested.emit)
        self.back=self.button(bar,'←',lambda:self.view.back() if self.view else None);self.back.setToolTip('Zurück')
        self.forward=self.button(bar,'→',lambda:self.view.forward() if self.view else None);self.forward.setToolTip('Vor')
        self.button(bar,'Neu laden',self.reload);self.button(bar,'Google',lambda:self.navigate(''))
        self.address=QLineEdit();self.address.setEnabled(False);self.address.setPlaceholderText('Mit Google suchen oder Webadresse eingeben');self.address.returnPressed.connect(lambda:self.navigate(self.address.text()));bar.addWidget(self.address,1)
        row=QHBoxLayout();root.addLayout(row)
        self.button(row,'+ Tab',self.new_tab);self.button(row,'Verlauf',self.show_history);self.button(row,'Login speichern',self.capture_login);self.button(row,'Login ausfüllen',self.fill_login);self.button(row,'Passwörter',self.password_manager);self.button(row,'Cookies löschen',self.clear_cookies);row.addStretch()
        migration=QHBoxLayout();root.addLayout(migration);self.button(migration,'Lesezeichen',self.show_bookmarks);self.button(migration,'Chrome / Edge importieren',self.import_browser);self.button(migration,'Als Standardbrowser einstellen',self.default_browser);migration.addStretch();self.pending_url=None
        self.status=QLabel('ReBrowko · Internetverbindung wird geprüft …');self.status.setWordWrap(True);root.addWidget(self.status)
        self.stack=QStackedWidget();root.addWidget(self.stack,1)
        self.notice=QLabel('ReBrowko benötigt Internet.\nMit „Neu laden“ erneut prüfen.');self.notice.setAlignment(Qt.AlignmentFlag.AlignCenter);self.stack.addWidget(self.notice)
        self.tabs=QTabWidget();self.tabs.setTabsClosable(True);self.tabs.setMovable(True);self.tabs.tabCloseRequested.connect(self.close_tab);self.tabs.currentChanged.connect(self.current_changed);self.stack.addWidget(self.tabs)
        self.network=QNetworkAccessManager(self);self.timer=QTimer(self);self.timer.setInterval(30000);self.timer.timeout.connect(self.check);self.timer.start();QTimer.singleShot(0,self.check)
        for shortcut,callback in [('Ctrl+T',self.new_tab),('Ctrl+W',lambda:self.close_tab(self.tabs.currentIndex())),('Ctrl+L',self.focus_address),('Ctrl+H',self.show_history),('Ctrl+Tab',lambda:self.cycle(1)),('Ctrl+Shift+Tab',lambda:self.cycle(-1))]:
            action=QAction(self);action.setShortcut(QKeySequence(shortcut));action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut);action.triggered.connect(lambda checked=False,fn=callback:fn());self.addAction(action)
    @property
    def view(self):return self.tabs.currentWidget()
    def import_browser(self):
        from browser_import_ui import ImportBrowser
        ImportBrowser(self).exec()
    def default_browser(self):
        try:
            from browser_default import register
            register();self.status.setText('In Windows unter Standard-Apps Repaintko auswählen und als Standard festlegen.')
        except Exception as exc:QMessageBox.warning(self,'Standardbrowser',str(exc))
    def show_bookmarks(self):
        path=self.store.root/'bookmarks.json';rows=json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
        dialog=QDialog(self);dialog.setWindowTitle('Lesezeichen');dialog.resize(650,450);layout=QVBoxLayout(dialog);items=QListWidget();layout.addWidget(items)
        for row in rows:items.addItem((row.get('folder','')+' / '+row.get('title',row['url'])).strip(' /'))
        def open_item():
            if items.currentRow()>=0:self.open_external(rows[items.currentRow()]['url']);dialog.accept()
        button=QPushButton('Öffnen');button.clicked.connect(open_item);layout.addWidget(button);items.itemDoubleClicked.connect(lambda _:open_item());dialog.exec()
    def open_external(self,url):
        from urllib.parse import urlsplit
        parsed=urlsplit(url)
        if parsed.scheme not in ('http','https') or not parsed.hostname:return
        self.pending_url=url
        if self.online:self.activate_online()
        else:self.check()
    def button(self,bar,label,fn):
        b=QPushButton(label);b.clicked.connect(lambda:fn());bar.addWidget(b);return b
    def focus_address(self):self.address.setFocus();self.address.selectAll()
    def cycle(self,step):
        if self.tabs.count():self.tabs.setCurrentIndex((self.tabs.currentIndex()+step)%self.tabs.count())
    def showEvent(self,event):
        super().showEvent(event);self.check()
        if self.online:self.activate_online()
    def reload(self):
        if self.online and self.view:self.view.reload()
        self.check()
    def check(self):
        if self.stopping or self.reply is not None:return
        request=QNetworkRequest(QUrl('https://www.google.com/generate_204'));request.setTransferTimeout(7000)
        self.reply=self.network.get(request);self.reply.finished.connect(self.checked)
    def checked(self):
        reply=self.reply
        if reply is None:return
        self.reply=None
        ok=reply.error()==QNetworkReply.NetworkError.NoError and reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute) in (200,204)
        reply.deleteLater()
        if not self.stopping:self.set_online(ok)
    def set_online(self,online):
        changed=online!=self.online;self.online=online;self.address.setEnabled(online)
        if changed:self.onlineChanged.emit(online)
        if not online:
            for i in range(self.tabs.count()):self.tabs.widget(i).stop()
            self.stack.setCurrentWidget(self.notice);self.status.setText('Kein Internet oder Google nicht erreichbar. Mit „Neu laden“ erneut versuchen.');return
        self.status.setText('ReBrowko · Online · Anmeldesitzungen werden gespeichert.')
        if self.isVisible():self.activate_online()
    def activate_online(self):
        try:
            if self.pending_url:
                url,self.pending_url=self.pending_url,None;self.new_tab(url)
            elif not self.tabs.count():self.new_tab()
            if self.tabs.count():self.stack.setCurrentWidget(self.tabs)
        except Exception as exc:self.stack.setCurrentWidget(self.notice);self.status.setText('Browser konnte nicht gestartet werden: '+str(exc))
    def ensure_profile(self):
        if self.profile:return
        from PySide6.QtWebEngineCore import QWebEngineProfile
        self.profile=QWebEngineProfile('ReBrowko',self)
        self.profile.setPersistentStoragePath(str(self.store.root/'profile'));self.profile.setCachePath(str(self.store.root/'cache'))
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        self.profile.downloadRequested.connect(lambda d:(d.cancel(),self.status.setText('Downloads bitte im normalen Browser öffnen.')))
    def new_tab(self,url=None):
        if not self.online:self.check();return
        if self.tabs.count()>=30:self.status.setText('Maximal 30 Tabs. Bitte zuerst einen Tab schließen.');return
        from PySide6.QtWebEngineWidgets import QWebEngineView
        from PySide6.QtWebEngineCore import QWebEnginePage
        self.ensure_profile()
        class Page(QWebEnginePage):
            def acceptNavigationRequest(page,url,kind,main):return url.scheme() in ('http','https','about')
        view=QWebEngineView(self.tabs);page=Page(self.profile,view);view.setPage(page)
        page.newWindowRequested.connect(lambda request:self.new_tab(request.requestedUrl()))
        view.urlChanged.connect(lambda _:self.current_changed());view.titleChanged.connect(lambda title:self.tab_title(view,title));view.loadFinished.connect(lambda ok:self.loaded(view,ok));view.loadProgress.connect(lambda n:self.status.setText(f'ReBrowko · Laden {n} %') if view is self.view else None)
        index=self.tabs.addTab(view,'Neuer Tab');self.tabs.setCurrentIndex(index);self.stack.setCurrentWidget(self.tabs)
        view.setUrl(url if isinstance(url,QUrl) else destination(url or ''))
    def close_tab(self,index):
        if index<0:return
        view=self.tabs.widget(index);self.tabs.removeTab(index);view.stop();view.deleteLater()
        if not self.tabs.count():
            self.stack.setCurrentWidget(self.notice);self.notice.setText('Kein Tab geöffnet. Mit + Tab eine neue Seite öffnen.')
    def tab_title(self,view,title):
        index=self.tabs.indexOf(view)
        if index>=0:self.tabs.setTabText(index,title[:32] or 'ReBrowko');self.tabs.setTabToolTip(index,title)
    def current_changed(self,*args):
        if self.view:
            self.address.setText(self.view.url().toString());self.back.setEnabled(self.view.history().canGoBack());self.forward.setEnabled(self.view.history().canGoForward())
    def loaded(self,view,ok):
        if ok:
            try:self.store.visit(view.url().toString(),view.title())
            except Exception:self.status.setText('Verlauf konnte nicht gespeichert werden.')
        if view is self.view:
            self.current_changed()
            if not ok:self.status.setText('Seite konnte nicht geladen werden. Adresse oder Verbindung prüfen.')
            else:self.status.setText('ReBrowko · Online')
    def navigate(self,text):
        if not self.online:self.check();return
        if not self.view:self.new_tab(destination(text))
        else:self.view.setUrl(destination(text))
    def show_history(self):
        dialog=QDialog(self);dialog.setWindowTitle('Such- und Seitenverlauf');dialog.resize(700,480);layout=QVBoxLayout(dialog);search=QLineEdit();search.setPlaceholderText('Verlauf durchsuchen …');layout.addWidget(search);items=QListWidget();layout.addWidget(items)
        layout.addWidget(QLabel('Bis zu 1.000 Treffer angezeigt. Suche durchsucht den gesamten Verlauf.'))
        try:rows=self.store.history()
        except Exception as exc:QMessageBox.warning(self,'Verlauf',str(exc));return
        def refresh():
            items.clear()
            for row in rows:
                if search.text().casefold() in (row['title']+' '+row['url']).casefold():
                    from PySide6.QtWidgets import QListWidgetItem
                    item=QListWidgetItem(row['time']+' · '+row['title']+'\n'+row['url']);item.setData(Qt.ItemDataRole.UserRole,row['url']);items.addItem(item)
                    if items.count()>=1000:break
        def open_item(item):self.new_tab(QUrl(item.data(Qt.ItemDataRole.UserRole)));dialog.accept()
        items.itemDoubleClicked.connect(open_item);search.textChanged.connect(refresh);refresh();row=QHBoxLayout();layout.addLayout(row)
        self.button(row,'Öffnen',lambda:open_item(items.currentItem()) if items.currentItem() else None)
        def clear():
            if QMessageBox.question(dialog,'Verlauf löschen','Den gesamten Such- und Seitenverlauf löschen?')==QMessageBox.StandardButton.Yes:
                try:self.store.clear_history();rows.clear();refresh()
                except Exception as exc:QMessageBox.warning(dialog,'Verlauf',str(exc))
        self.button(row,'Verlauf löschen',clear);self.button(row,'Schließen',dialog.accept);dialog.exec()
    def site(self):
        if not self.view:raise ValueError('Zuerst eine HTTPS-Webseite öffnen.')
        return origin(self.view.url().toString())
    def capture_login(self):
        try:site=self.site()
        except Exception as exc:QMessageBox.information(self,'Login speichern',str(exc));return
        view=self.view;page=view.page()
        def captured(raw):
            if self.view is not view or origin_or_empty(view.url().toString())!=site:return
            data={}
            try:data=json.loads(raw) if raw else {}
            except (ValueError,TypeError):pass
            if data.get('site')!=site:data={}
            self.edit_login(site,data.get('user',''),data.get('password',''))
        page.runJavaScript(READ_LOGIN,1,captured)
    def edit_login(self,site,user='',password=''):
        dialog=QDialog(self);dialog.setWindowTitle('Login speichern');form=QFormLayout(dialog);label=QLabel(site);label.setTextFormat(Qt.TextFormat.PlainText);form.addRow('Webseite',label)
        username=QLineEdit(user);secret=QLineEdit(password);secret.setEchoMode(QLineEdit.EchoMode.Password);form.addRow('Benutzername / E-Mail',username);form.addRow('Passwort',secret);note=QLabel('Verschlüsselt für dein Windows-Benutzerkonto speichern.\nZum Ausfüllen später „Login ausfüllen“ anklicken.');form.addRow(note)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);form.addRow(buttons)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            try:self.store.save(site,username.text(),secret.text());self.status.setText('Login verschlüsselt gespeichert.')
            except Exception as exc:QMessageBox.warning(self,'Passwortspeicher',str(exc))
        secret.clear()
    def fill_login(self):
        try:
            site=self.site();rows=[r for r in self.store.credentials() if r['site']==site]
            if not rows:QMessageBox.information(self,'Login ausfüllen','Für diese Webseite ist kein Login gespeichert.');return
            chosen,ok=QInputDialog.getItem(self,'Login ausfüllen',site,[r['user'] or '(ohne Benutzername)' for r in rows],0,False)
            if not ok:return
            record=rows[[r['user'] or '(ohne Benutzername)' for r in rows].index(chosen)];view=self.view
            if self.site()!=site:return
            view.page().runJavaScript(fill_script(site,record['user'],record['password']),1,lambda ok:self.status.setText('Login ausgefüllt. Anmeldung selbst bestätigen.' if ok else 'Kein passendes Eingabefeld gefunden.'))
        except Exception as exc:QMessageBox.warning(self,'Login ausfüllen',str(exc))
    def password_manager(self):
        try:rows=self.store.credentials()
        except Exception as exc:QMessageBox.warning(self,'Passwortspeicher',str(exc));return
        dialog=QDialog(self);dialog.setWindowTitle('Gespeicherte Passwörter');dialog.resize(620,400);layout=QVBoxLayout(dialog);layout.addWidget(QLabel('Passwörter sind verschlüsselt. Ausfüllen nur auf derselben HTTPS-Webseite.'));items=QListWidget();layout.addWidget(items)
        def refresh():items.clear();items.addItems([r['site']+' · '+(r['user'] or '(ohne Benutzername)') for r in rows])
        def delete():
            index=items.currentRow()
            if index<0:return
            if QMessageBox.question(dialog,'Login löschen','Diesen gespeicherten Login löschen?')!=QMessageBox.StandardButton.Yes:return
            try:r=rows[index];self.store.delete(r['site'],r['user']);rows.pop(index);refresh()
            except Exception as exc:QMessageBox.warning(dialog,'Passwortspeicher',str(exc))
        refresh();row=QHBoxLayout();layout.addLayout(row);self.button(row,'Löschen',delete);self.button(row,'Schließen',dialog.accept);dialog.exec()
    def clear_cookies(self):
        if not self.profile:return
        if QMessageBox.question(self,'Cookies löschen','Alle Cookies löschen? Du wirst auf vielen Webseiten abgemeldet. Gespeicherte Passwörter und Verlauf bleiben erhalten.')==QMessageBox.StandardButton.Yes:self.profile.cookieStore().deleteAllCookies();self.status.setText('Cookies werden gelöscht.')
    def shutdown(self):
        self.stopping=True;self.timer.stop()
        if self.reply:self.reply.abort()
        for i in range(self.tabs.count()):self.tabs.widget(i).stop()

def origin_or_empty(url):
    try:return origin(url)
    except ValueError:return ''
