from concurrent.futures import ThreadPoolExecutor
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QCheckBox,QPushButton,QFileDialog,QMessageBox
from browser_import import profiles,read_profile,merge_profile,password_csv,bookmarks_html

class ImportBrowser(QDialog):
    def __init__(self,browser):
        super().__init__(browser);self.browser=browser;self.pool=ThreadPoolExecutor(max_workers=1);self.future=None
        self.setWindowTitle('Chrome / Edge übernehmen');self.resize(640,440);layout=QVBoxLayout(self)
        note=QLabel('Lesezeichen und Verlauf aus einem lokalen Profil übernehmen. Für Passwörter im alten Browser den Passwortmanager öffnen, Passwörter als CSV exportieren und hier auswählen. Cookies, bestehende Anmeldesitzungen, Erweiterungen und Passkeys sind nicht übertragbar.');note.setWordWrap(True);layout.addWidget(note)
        self.profile=QComboBox()
        for title,path in profiles():self.profile.addItem(title,str(path))
        layout.addWidget(self.profile);self.bookmarks=QCheckBox('Lesezeichen');self.bookmarks.setChecked(True);layout.addWidget(self.bookmarks);self.history=QCheckBox('Verlauf (bis zu 100.000 Einträge)');self.history.setChecked(True);layout.addWidget(self.history)
        row=QHBoxLayout();layout.addLayout(row);self.profile_button=QPushButton('Profil importieren');self.profile_button.clicked.connect(self.profile_import);row.addWidget(self.profile_button)
        self.html_button=QPushButton('Lesezeichen-HTML');self.html_button.clicked.connect(self.html_import);row.addWidget(self.html_button);self.password_button=QPushButton('Passwort-CSV');self.password_button.clicked.connect(self.password_import);row.addWidget(self.password_button)
        self.status=QLabel('Vorhandene Passwörter werden nicht überschrieben. Importierte Passwörter werden für dein Windows-Konto verschlüsselt gespeichert.');self.status.setWordWrap(True);layout.addWidget(self.status)
        note=QLabel('Die exportierte Passwort-CSV enthält Klartext. Nach dem Import kannst du sie im Explorer entfernen. Bei gesperrtem Verlauf Chrome/Edge schließen und erneut versuchen.');note.setWordWrap(True);layout.addWidget(note)
        close=QPushButton('Schließen');close.clicked.connect(self.reject);layout.addWidget(close);self.timer=QTimer(self);self.timer.setInterval(80);self.timer.timeout.connect(self.poll)
    def start(self,fn):
        if self.future:return
        self.future=self.pool.submit(fn);self.status.setText('Import läuft …');self.timer.start()
        for b in (self.profile_button,self.html_button,self.password_button):b.setEnabled(False)
    def poll(self):
        if not self.future.done():return
        future,self.future=self.future,None;self.timer.stop()
        for b in (self.profile_button,self.html_button,self.password_button):b.setEnabled(True)
        try:self.status.setText(future.result())
        except Exception as exc:self.status.setText('Import fehlgeschlagen: '+str(exc))
    def profile_import(self):
        path=self.profile.currentData();bookmarks=self.bookmarks.isChecked();history=self.history.isChecked()
        if not path:return
        def run():
            data=read_profile(path,bookmarks,history);a,b=merge_profile(self.browser.store,data);return f'{a} Lesezeichen und {b} Verlaufseinträge verarbeitet.'+(' Weitere alte Einträge wurden wegen des Limits ausgelassen.' if data['truncated'] else '')
        self.start(run)
    def html_import(self):
        path=QFileDialog.getOpenFileName(self,'Lesezeichen importieren','','HTML (*.html *.htm)')[0]
        if path:self.start(lambda:str(bookmarks_html(self.browser.store,path))+' Lesezeichen verarbeitet.')
    def password_import(self):
        path=QFileDialog.getOpenFileName(self,'Passwort-CSV importieren','','CSV (*.csv)')[0]
        if path:
            def run():
                added,skipped=password_csv(self.browser.store,path);return f'{added} Passwörter importiert; {skipped} doppelte, leere oder nicht unterstützte Einträge übersprungen (nur HTTPS).'
            self.start(run)
    def reject(self):
        if self.future:self.status.setText('Bitte den laufenden Import abwarten.');return
        self.pool.shutdown(wait=False);super().reject()
