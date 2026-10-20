"""Opt-in account page and compact departure widget. Reads only official DOM."""
import json
from datetime import datetime
from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QDialog,QComboBox,QFormLayout,QLineEdit
from timesheet_data import URL, READ_TIMESHEET, is_record_url, calculate

class TimesheetWidget(QWidget):
    def __init__(self, preferences, browser, parent=None):
        super().__init__(parent)
        self.preferences=preferences;self.browser=browser;self.dialog=None;self.web=None
        self.data=None;self.fetched=None;self.loaded_at=None;self.generation=0;self.loading=False;self.enabled=False
        self.mode=str(preferences.value('timesheet/display','both'))
        self.basis=str(preferences.value('timesheet/basis','unknown'))
        self.source=str(preferences.value('timesheet/source','Gleitzeit Saldo'))
        if not preferences.value('timesheet/badge_basis_migrated',False,type=bool):
            if self.source=='Gleitzeit Saldo':self.basis='badge';preferences.setValue('timesheet/basis',self.basis)
            preferences.setValue('timesheet/badge_basis_migrated',True)
        self.manual='' # personal balances remain in memory, not in settings/logs
        self.problem='Bbc anmelden'
        layout=QHBoxLayout(self);layout.setContentsMargins(8,0,8,0)
        self.label=QLabel('Bbc · anmelden');self.label.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(self.label)
        self.open_button=QPushButton('◷');self.open_button.setToolTip('Bbc anmelden / Saldo-Einstellungen');self.open_button.setAccessibleName('Bbc-Zeiterfassung und Saldo-Einstellungen');self.open_button.clicked.connect(lambda:self.open_account());layout.addWidget(self.open_button)
        self.timer=QTimer(self);self.timer.setInterval(5000);self.timer.timeout.connect(self.tick)

    def set_enabled(self,enabled):
        self.enabled=enabled;self.preferences.setValue('timesheet/enabled',enabled)
        if enabled:self.timer.start();self.render()
        else:
            self.timer.stop();self.generation+=1;self.data=None;self.fetched=None
            if self.web:self.web.stop()
            if self.dialog:self.dialog.hide()

    def open_account(self,show=True):
        if self.dialog:
            if show:self.dialog.show();self.dialog.raise_()
            if self.web and not self.data:self.web.reload()
            return
        self.dialog=QDialog(self.window());self.dialog.setWindowTitle('Bbc · Zeiterfassung & Saldo')
        self.dialog.resize(1000,720);root=QVBoxLayout(self.dialog)
        notice=QLabel('Melde dich direkt beim Bbc-Extranet an und öffne den heutigen Tag. Repaintko liest nur die Zeiten; es bucht nichts ein oder aus.');notice.setWordWrap(True);root.addWidget(notice)
        form=QFormLayout();root.addLayout(form)
        self.display_box=QComboBox()
        for title,key in [('Beide Ziele','both'),('8:12 Stunden erreichen','daily'),('Gleitzeit-Saldo auf 0','zero')]:self.display_box.addItem(title,key)
        self.display_box.setCurrentIndex(max(0,self.display_box.findData(self.mode)));form.addRow('Anzeige',self.display_box)
        self.source_box=QComboBox();self.source_box.addItems(['Gleitzeit Saldo','Gleitzeit aktuell','Eigener Übertrag vor heute'])
        self.source_box.setCurrentText(self.source);form.addRow('Wert für Saldo 0',self.source_box)
        self.basis_box=QComboBox()
        for title,key in [('Saldo seit letztem Ausbadgen (Bbc Gleitzeit Saldo)','badge'),('Bitte Bedeutung des Wertes wählen','unknown'),('Saldo vor dem heutigen Arbeitstag','prior'),('Saldo enthält die Arbeitszeit bis zum Laden der Seite','live')]:self.basis_box.addItem(title,key)
        self.basis_box.setCurrentIndex(max(0,self.basis_box.findData(self.basis)));form.addRow('Bedeutung des Saldo-Wertes',self.basis_box)
        self.manual_edit=QLineEdit();self.manual_edit.setPlaceholderText('z. B. -02:15 oder +01:30');form.addRow('Eigener Übertrag (optional)',self.manual_edit)
        self.note=QLabel();self.note.setWordWrap(True);self.note.setTextFormat(Qt.TextFormat.PlainText);root.addWidget(self.note)
        for box in (self.display_box,self.source_box,self.basis_box):box.currentIndexChanged.connect(self.options_changed)
        self.manual_edit.textChanged.connect(self.options_changed)
        buttons=QHBoxLayout();root.addLayout(buttons)
        home=QPushButton('Zeiterfassung öffnen');home.clicked.connect(lambda:self.web.setUrl(QUrl(URL)) if self.web else None);buttons.addWidget(home)
        refresh=QPushButton('Neu laden');refresh.clicked.connect(lambda:self.web.reload() if self.web else None);buttons.addWidget(refresh)
        close=QPushButton('Zurück zu Repaintko');close.clicked.connect(self.dialog.hide);buttons.addWidget(close)
        try:
            from PySide6.QtWebEngineCore import QWebEnginePage
            from PySide6.QtWebEngineWidgets import QWebEngineView
            self.browser.ensure_profile()
            self.web=QWebEngineView(self.dialog)
            self.web.setPage(QWebEnginePage(self.browser.profile,self.web))
            self.web.page().newWindowRequested.connect(lambda r:self.web.setUrl(r.requestedUrl()) if r.requestedUrl().scheme()=='https' else None)
            root.addWidget(self.web,1)
            self.web.loadStarted.connect(self.load_started);self.web.loadFinished.connect(self.load_finished)
            self.web.setUrl(QUrl(URL))
        except Exception as exc:
            self.problem='Browser konnte nicht gestartet werden.';self.note.setText(self.problem+' '+str(exc))
        if show:self.dialog.show()
        self.render()

    def options_changed(self,*args):
        self.mode=self.display_box.currentData();self.source=self.source_box.currentText();self.basis=self.basis_box.currentData();self.manual=self.manual_edit.text().strip()
        self.manual_edit.setEnabled(self.source=='Eigener Übertrag vor heute')
        for key,value in [('display',self.mode),('source',self.source),('basis',self.basis)]:self.preferences.setValue('timesheet/'+key,value)
        self.render()

    def load_started(self):
        self.generation+=1;self.loading=True;self.data=None;self.fetched=None;self.problem='Zeiterfassung wird geladen …';self.render()

    def load_finished(self,ok):
        self.loading=False;self.loaded_at=datetime.now()
        if ok:self.read()
        else:self.problem='Verbindung fehlgeschlagen – neu laden';self.render()

    def read(self):
        if not self.enabled or not self.web or self.loading:return
        try:
            frames=[self.web.page().mainFrame()];found=None
            while frames:
                frame=frames.pop();frames.extend(frame.children())
                if frame.isValid() and is_record_url(frame.url().toString()):
                    # Prefer the observed legacy frame, which contains the form.
                    found=frame
                    if frame.url().host()=='legacy.extranet.bbcag.ch':break
            if found is None:
                self.data=None;self.problem='Bitte beim Bbc anmelden';self.render();return
            generation=self.generation
            found.runJavaScript(READ_TIMESHEET,1,lambda raw:self.received(raw,generation))
        except RuntimeError:
            self.data=None;self.problem='Zeiterfassung nicht verfügbar';self.render()

    def received(self,raw,generation):
        if not self.enabled or generation!=self.generation:return
        try:
            data=json.loads(raw)
            if not isinstance(data,dict):raise ValueError()
            self.data=data;self.fetched=datetime.now();self.problem=''
        except (ValueError,TypeError):
            self.data=None;self.problem='Zeiterfassung öffnen und heutigen Tag auswählen'
        self.render()

    def tick(self):
        if self.web and not self.loading:
            # Never automatically reload a visible form or changed input fields.
            age=(datetime.now()-self.loaded_at).total_seconds() if self.loaded_at else 0
            if is_record_url(self.web.url().toString()) and not (self.data and (self.data.get('dirty') or self.data.get('absence'))) and not self.dialog.isVisible() and age>=60:
                self.web.reload()
            else:self.read()
        self.render()

    def render(self):
        detail='Mindestens 30 min Pause insgesamt; fehlende Pause wird eingeplant. Zusätzliche Pausen verschieben die Gehzeit. Keine automatische Zeiterfassung.'
        text='Bbc · '+self.problem
        if self.data:
            try:
                if not self.loaded_at or (datetime.now()-self.loaded_at).total_seconds()>180:raise ValueError('Daten veraltet – Zeiterfassung neu laden')
                if self.loaded_at.date()!=datetime.now().date():raise ValueError('Neuer Tag – Zeiterfassung neu laden')
                balance=self.manual if self.source=='Eigener Übertrag vor heute' else self.data.get('balances',{}).get(self.source,'')
                basis='prior' if self.source=='Eigener Übertrag vor heute' else self.basis
                # A bad/unknown balance must not hide the independent daily target.
                now=datetime.now()
                result=calculate(self.data,now)
                zero='Grundlage wählen'
                if basis!='unknown':
                    try:zero=calculate(self.data,now,basis,balance,snapshot_at=self.loaded_at)['zero']
                    except ValueError:zero='Saldo prüfen'
                parts=[]
                if self.mode!='zero':parts.append('8:12 → '+result['daily'])
                if self.mode!='daily':parts.append('Saldo 0 → '+zero)
                text='\n'.join(parts)
                values=self.data.get('balances',{})
                detail=f"Stand {self.loaded_at:%H:%M} · Gleitzeit aktuell: {values.get('Gleitzeit aktuell','–')} · Gleitzeit Saldo: {values.get('Gleitzeit Saldo','–')}\nGrundlage: {self.source} · "+({'unknown':'noch nicht festgelegt','prior':'vor heute','live':'inklusive Arbeit beim Laden','badge':'seit letztem Ausbadgen; offene Arbeitszeit wird angerechnet'}.get(basis,'unbekannt'))+'\n'+detail
                if not result['open']:detail+=' Du bist derzeit nicht eingebucht; angezeigt wird die noch nötige Arbeitszeit.'
                detail+=f"\nErfasste Pause: {result['pause']} min · noch einzuplanen: {result['pause_missing']} min."
            except (ValueError,TypeError,KeyError) as exc:text='Bbc · '+str(exc)
        self.label.setText(text);self.setToolTip(detail)
        if self.dialog:self.note.setText(text+'\n'+detail)

    def shutdown(self):
        self.timer.stop();self.enabled=False;self.generation+=1
        if self.web:self.web.stop()
        if self.dialog:self.dialog.close()
