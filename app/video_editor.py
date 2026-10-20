"""Plus video editor with a non-destructive timeline and rendered playback."""
import copy,tempfile,threading
from pathlib import Path
from PySide6.QtCore import Qt,QTimer,QUrl,Signal,QRectF
from PySide6.QtGui import QAction,QKeySequence,QPainter,QColor,QPen
from PySide6.QtWidgets import (QDialog,QWidget,QVBoxLayout,QHBoxLayout,QSplitter,QLabel,QPushButton,QSlider,QListWidget,QTabWidget,QFormLayout,QDoubleSpinBox,QComboBox,QCheckBox,QFileDialog,QMessageBox,QProgressDialog,QScrollArea)
from PySide6.QtMultimedia import QMediaPlayer,QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from concurrent.futures import ThreadPoolExecutor
from video_engine import Timeline,Clip,TRANSITIONS,EFFECTS,KEYFRAMES,render,Cancelled,interpolate
from branding import is_activated

def timestamp(t):
    minutes,seconds=divmod(max(0,t),60);return f'{int(minutes):02d}:{seconds:06.3f}'

class Track(QWidget):
    seek=Signal(float,int)
    def __init__(self,editor):super().__init__();self.editor=editor;self.setMinimumHeight(100);self.setMouseTracking(True)
    def paintEvent(self,event):
        p=QPainter(self);p.fillRect(self.rect(),QColor('#101721'));timeline=self.editor.timeline
        if not timeline.clips:return
        scale=self.width()/max(.1,timeline.duration)
        for i,(start,clip) in enumerate(zip(timeline.starts(),timeline.clips)):
            x=start*scale;w=max(2,clip.duration*scale)
            p.setBrush(QColor('#396d92' if i==self.editor.selected else '#30445e'));p.setPen(QPen(QColor('#9bd5ff' if i==self.editor.selected else '#668099'),2 if i==self.editor.selected else 1));p.drawRoundedRect(QRectF(x+1,22,w-2,50),4,4)
            p.setPen(QColor('white'));p.drawText(QRectF(x+5,25,w-10,42),Qt.TextFlag.TextWordWrap, f'{i+1}  {Path(clip.path).name}\n{clip.duration:.2f} s')
            for effect in clip.effects:p.fillRect(QRectF((start+effect['start'])*scale,75,max(1,(effect['end']-effect['start'])*scale),5),QColor('#aa7de0'))
            for points in clip.keyframes.values():
                for time,value in points:p.fillRect(QRectF((start+time)*scale-2,84,4,5),QColor('#ffd377'))
            overlap=timeline.overlap(i)
            if overlap:p.fillRect(QRectF((start+clip.duration-overlap)*scale,12,overlap*scale,6),QColor('#70c9b3'))
        p.setPen(QPen(QColor('#ffbd66'),2));x=self.editor.position*scale;p.drawLine(int(x),0,int(x),self.height());p.drawText(5,12,'Clips · violett: Effekte · gelb: Keyframes · grün: Übergänge')
    def mousePressEvent(self,event):
        t=max(0,min(self.editor.timeline.duration,event.position().x()/max(1,self.width())*self.editor.timeline.duration));index,_=self.editor.timeline.locate(t);self.seek.emit(t,index)

class VideoEditor(QWidget):
    returnRequested=Signal()
    def __init__(self,preferences,parent=None):
        if not is_activated(preferences):raise PermissionError('Der Videomodus benötigt Repaintko Plus.')
        super().__init__(parent);self.preferences=preferences;self.timeline=Timeline();self.selected=-1;self.position=0.;self.preview_state=None;self.rendered=False;self.temp=tempfile.TemporaryDirectory(prefix='repaintko-preview-');self.busy=False;self.pending_seek=None
        self.setWindowTitle('Repaintko Plus · Video-Editor');self.resize(1180,800);self.setMinimumSize(640,440)
        root=QVBoxLayout(self);root.setContentsMargins(8,8,8,8);top=QHBoxLayout();root.addLayout(top)
        self.button(top,'← Bild / GIF',self.returnRequested.emit)
        for title,callback in [('Clips hinzufügen',self.import_clips),('Projekt öffnen',self.open_project),('Projekt speichern',self.save_project),('MP4 exportieren',self.export)]:self.button(top,title,callback)
        top=QHBoxLayout();root.addLayout(top);self.button(top,'Rückgängig',self.undo);self.button(top,'Wiederholen',self.redo)
        self.resolution=QComboBox();self.resolution.addItems(['HD 1280 × 720','Full HD 1920 × 1080','4K 3840 × 2160','Hochkant 1080 × 1920']);self.resolution.currentIndexChanged.connect(self.output_settings);top.addWidget(self.resolution)
        self.fps=QComboBox();self.fps.addItems(['24 FPS','25 FPS','30 FPS','50 FPS','60 FPS']);self.fps.setCurrentIndex(2);self.fps.currentIndexChanged.connect(self.output_settings);top.addWidget(self.fps)
        split=QSplitter();root.addWidget(split,1);viewer=QWidget();view=QVBoxLayout(viewer);view.setContentsMargins(0,0,0,0);split.addWidget(viewer)
        self.video=QVideoWidget();self.video.setMinimumSize(240,140);view.addWidget(self.video,1)
        self.player=QMediaPlayer(self);self.audio=QAudioOutput(self);self.player.setAudioOutput(self.audio);self.player.setVideoOutput(self.video);self.player.positionChanged.connect(self.playback_position);self.player.mediaStatusChanged.connect(self.media_status);self.player.errorOccurred.connect(lambda *args:self.hint.setText('Vorschau: '+self.player.errorString()))
        self.hint=QLabel('Clips hinzufügen. Strg+S teilt am Abspielkopf. Projekte speichern mit Strg+Umschalt+S.');self.hint.setWordWrap(True);view.addWidget(self.hint)
        play=QHBoxLayout();view.addLayout(play)
        self.play_button=self.button(play,'Wiedergabe / Pause',self.play_pause);self.button(play,'− 1 Frame',lambda:self.seek(self.position-1/self.timeline.fps));self.button(play,'+ 1 Frame',lambda:self.seek(self.position+1/self.timeline.fps));self.time=QLabel('00:00.000');play.addWidget(self.time)
        self.slider=QSlider(Qt.Orientation.Horizontal);self.slider.setRange(0,0);self.slider.valueChanged.connect(lambda v:self.seek(v/1000));view.addWidget(self.slider)
        tabs=QTabWidget();tabs.setMinimumWidth(280);tabs.setMaximumWidth(410);split.addWidget(tabs);split.setSizes([780,320])
        form=self.tab(tabs,'Clip');self.inpoint=self.spin(form,'In in Quelldatei',0,100000,3);self.outpoint=self.spin(form,'Out in Quelldatei',0,100000,3);self.speed=self.spin(form,'Geschwindigkeit',.25,4,2,1);self.volume=self.spin(form,'Lautstärke',0,2,2,1);self.mute=QCheckBox('Stummschalten');form.addRow(self.mute);self.form_button(form,'Clip-Einstellungen anwenden',self.apply_clip)
        self.form_button(form,'Hier teilen · Strg+S',self.split_clip);self.form_button(form,'Clip duplizieren',self.duplicate);self.form_button(form,'Clip entfernen',self.delete_clip);self.form_button(form,'Clip nach links',lambda:self.move(-1));self.form_button(form,'Clip nach rechts',lambda:self.move(1))
        form=self.tab(tabs,'Effekte');self.effect=QComboBox();self.effect.addItems(EFFECTS);form.addRow('Bildeffekt',self.effect);self.fx_start=self.spin(form,'Von im Clip',0,100000,3);self.fx_end=self.spin(form,'Bis im Clip',0,100000,3);self.form_button(form,'Effekt hinzufügen',self.add_effect);self.fx_list=QListWidget();form.addRow(self.fx_list);self.form_button(form,'Gewählten Effekt entfernen',self.remove_effect)
        form=self.tab(tabs,'Keyframes');self.property=QComboBox();self.property.addItems(KEYFRAMES);self.property.currentTextChanged.connect(self.property_changed);form.addRow('Eigenschaft',self.property);self.key_value=self.spin(form,'Wert',1,4,3,1);self.key_time=self.spin(form,'Zeit im Clip',0,100000,3);self.form_button(form,'Zeit vom Abspielkopf',self.key_at_head);self.form_button(form,'Keyframe setzen / ersetzen',self.add_key);self.keys=QListWidget();form.addRow(self.keys);self.form_button(form,'Gewählten Keyframe entfernen',self.remove_key);text=QLabel('Zwischen Keyframes wird linear interpoliert. Position X/Y: 0 bis 1. Verschiebung ist bei Zoom > 1 sichtbar.');text.setWordWrap(True);form.addRow(text)
        form=self.tab(tabs,'Übergang');self.transition=QComboBox();self.transition.addItems(TRANSITIONS);form.addRow('Zum nächsten Clip',self.transition);self.transition_length=self.spin(form,'Dauer in Sekunden',.05,5,2,.5);self.form_button(form,'Übergang anwenden',self.apply_transition);text=QLabel('Überlappende Übergänge verkürzen die Gesamtlänge. Die Dauer wird auf höchstens die halbe Länge der beteiligten Clips begrenzt. Am letzten Clip gibt es keinen Übergang.');text.setWordWrap(True);form.addRow(text)
        self.track=Track(self);self.track.seek.connect(self.track_seek);root.addWidget(self.track);self.clips=QListWidget();self.clips.setFlow(QListWidget.Flow.LeftToRight);self.clips.setWrapping(False);self.clips.setFixedHeight(58);self.clips.currentRowChanged.connect(self.select_and_seek);root.addWidget(self.clips)
        for sequence,callback in [('Ctrl+S',self.split_clip),('Ctrl+Shift+S',self.save_project),('Ctrl+I',self.import_clips),('Ctrl+E',self.export),('Ctrl+Z',self.undo),('Ctrl+Y',self.redo),('Space',self.play_pause)]:
            action=QAction(self);action.setShortcut(QKeySequence(sequence));action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut);action.triggered.connect(callback);self.addAction(action)
        self.sync()
    def button(self,row,title,callback):
        button=QPushButton(title);button.clicked.connect(lambda checked=False:callback());row.addWidget(button);return button
    def tab(self,tabs,title):
        content=QWidget();form=QFormLayout(content);scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(content);tabs.addTab(scroll,title);return form
    def form_button(self,form,title,callback):
        button=QPushButton(title);button.clicked.connect(lambda checked=False:callback());form.addRow(button)
    def spin(self,form,title,minimum,maximum,decimals,value=0):
        box=QDoubleSpinBox();box.setRange(minimum,maximum);box.setDecimals(decimals);box.setValue(value);form.addRow(title,box);return box
    def clip(self):return self.timeline.clips[self.selected] if 0<=self.selected<len(self.timeline.clips) else None
    def failure(self,error):QMessageBox.warning(self,'Video-Editor',str(error))
    def sync(self):
        self.clips.blockSignals(True);self.clips.clear()
        for i,c in enumerate(self.timeline.clips):self.clips.addItem(f'{i+1} · {Path(c.path).name}  ({c.duration:.2f} s)')
        self.selected=min(self.selected,len(self.timeline.clips)-1)
        if self.timeline.clips and self.selected<0:self.selected=0
        self.clips.setCurrentRow(self.selected);self.clips.blockSignals(False);self.slider.setMaximum(round(self.timeline.duration*1000));self.position=min(self.position,self.timeline.duration)
        self.resolution.blockSignals(True);self.resolution.setCurrentIndex([(1280,720),(1920,1080),(3840,2160),(1080,1920)].index((self.timeline.width,self.timeline.height)));self.resolution.blockSignals(False);self.fps.blockSignals(True);self.fps.setCurrentIndex([24,25,30,50,60].index(self.timeline.fps));self.fps.blockSignals(False)
        self.select(self.selected);self.track.update();self.setWindowTitle(('• ' if self.timeline.dirty else '')+'Repaintko Plus · Video-Editor');self.update_time()
    def changed(self):
        self.player.pause();self.rendered=False;self.preview_state=None;self.hint.setText('Quellvorschau. Wiedergabe berechnet die Vorschau mit Effekten, Keyframes und Übergängen.');self.sync()
    def select(self,index):
        self.selected=index;c=self.clip()
        if c:
            self.inpoint.setValue(c.start);self.outpoint.setValue(c.end);self.speed.setValue(c.speed);self.volume.setValue(c.volume);self.mute.setChecked(c.mute);self.fx_start.setMaximum(c.duration);self.fx_end.setMaximum(c.duration);self.fx_start.setValue(0);self.fx_end.setValue(c.duration);self.key_time.setMaximum(c.duration);self.key_at_head();self.transition.setCurrentText(next(name for name,code in TRANSITIONS.items() if code==c.transition));self.transition_length.setValue(c.transition_duration)
        self.refresh_effects();self.refresh_keys();self.track.update()
    def select_and_seek(self,index):
        self.select(index)
        if 0<=index<len(self.timeline.clips):self.seek(self.timeline.starts()[index])
    def update_time(self):
        self.time.setText(timestamp(self.position)+' / '+timestamp(self.timeline.duration));self.slider.blockSignals(True);self.slider.setValue(round(self.position*1000));self.slider.blockSignals(False);self.track.update()
    def seek(self,time):
        if not self.timeline.clips:return
        self.position=max(0,min(self.timeline.duration,time));self.update_time();self.player.pause()
        if self.rendered:self.player.setPosition(round(self.position*1000));return
        index,local=self.timeline.locate(self.position);clip=self.timeline.clips[index];url=QUrl.fromLocalFile(clip.path);target=round((clip.start+local*clip.speed)*1000)
        if self.player.source()!=url:self.pending_seek=target;self.player.setSource(url)
        else:self.player.setPosition(target)
    def track_seek(self,time,index):self.clips.setCurrentRow(index);self.seek(time)
    def media_status(self,status):
        if status in (QMediaPlayer.MediaStatus.LoadedMedia,QMediaPlayer.MediaStatus.BufferedMedia) and self.pending_seek is not None:
            position=self.pending_seek;self.pending_seek=None;self.player.setPosition(position)
    def playback_position(self,ms):
        if self.rendered:self.position=min(self.timeline.duration,ms/1000);self.update_time()
    def task(self,title,callback):
        if self.busy:return None
        self.busy=True;cancel=threading.Event();status=[0,title];pool=ThreadPoolExecutor(max_workers=1)
        future=pool.submit(callback,cancel,lambda value,text:status.__setitem__(slice(None),[value,text]));dialog=QProgressDialog(title,'Abbrechen',0,100,self);dialog.setWindowModality(Qt.WindowModality.ApplicationModal);dialog.setMinimumDuration(0);dialog.canceled.connect(cancel.set)
        timer=QTimer(dialog)
        def poll():
            dialog.setLabelText(status[1]);dialog.setValue(min(99,status[0]))
            if future.done():dialog.accept()
        timer.timeout.connect(poll);timer.start(80);dialog.exec();timer.stop()
        if not future.done():cancel.set()
        # Pump a modal wait until FFmpeg has acknowledged cancellation.
        if not future.done():
            waiting=QProgressDialog('Vorgang wird beendet …',None,0,0,self);waiting.setWindowModality(Qt.WindowModality.ApplicationModal);waiter=QTimer(waiting);waiter.timeout.connect(lambda:waiting.accept() if future.done() else None);waiter.start(50);waiting.exec();waiter.stop()
        timer.stop();self.busy=False;pool.shutdown(wait=False)
        try:return future.result()
        except Cancelled:return None
        except Exception as exc:self.failure(exc);return None
    def import_clips(self):
        paths,_=QFileDialog.getOpenFileNames(self,'Videoclips hinzufügen','','Videos (*.mp4 *.mov *.mkv *.avi *.webm *.m4v *.wmv)')
        if not paths:return
        def load(cancel,progress):
            clips=[]
            for i,path in enumerate(paths):
                if cancel.is_set():raise Cancelled()
                progress(int(i/len(paths)*100),'Lese '+Path(path).name);clips.append(Clip.from_file(path))
            return clips
        clips=self.task('Clips laden',load)
        if clips:
            try:self.timeline.add(clips);self.selected=len(self.timeline.clips)-len(clips);self.changed();self.seek(self.timeline.starts()[self.selected])
            except Exception as exc:self.failure(exc)
    def apply_clip(self):
        if not self.clip():return
        try:self.timeline.trim(self.selected,self.inpoint.value(),self.outpoint.value(),self.speed.value(),self.volume.value(),self.mute.isChecked());self.changed()
        except Exception as exc:self.failure(exc)
    def split_clip(self):
        if not self.clip():return
        self.selected=self.timeline.locate(self.position)[0]
        try:self.timeline.split(self.selected,self.position);self.selected+=1;self.changed()
        except Exception as exc:self.failure(exc)
    def duplicate(self):
        if not self.clip():return
        if len(self.timeline.clips)>=100:self.failure('Maximal 100 Clips.');return
        import uuid
        self.timeline.remember();clip=copy.deepcopy(self.clip());clip.uid=uuid.uuid4().hex;self.timeline.clips.insert(self.selected+1,clip);self.selected+=1;self.changed()
    def delete_clip(self):
        if self.clip():self.timeline.remember();self.timeline.clips.pop(self.selected);self.changed()
    def move(self,offset):
        target=self.selected+offset
        if self.clip() and 0<=target<len(self.timeline.clips):
            self.timeline.remember();self.timeline.clips[self.selected],self.timeline.clips[target]=self.timeline.clips[target],self.timeline.clips[self.selected];self.selected=target;self.changed()
    def undo(self):self.timeline.undo();self.changed()
    def redo(self):self.timeline.redo();self.changed()
    def output_settings(self):
        self.timeline.remember();self.timeline.width,self.timeline.height=[(1280,720),(1920,1080),(3840,2160),(1080,1920)][self.resolution.currentIndex()];self.timeline.fps=[24,25,30,50,60][self.fps.currentIndex()];self.changed()
    def add_effect(self):
        c=self.clip()
        if not c:return
        start,end=self.fx_start.value(),self.fx_end.value()
        if start>=end:self.failure('Das Ende muss nach dem Anfang liegen.');return
        self.timeline.remember();c.effects.append(dict(name=self.effect.currentText(),start=start,end=end));self.changed()
    def refresh_effects(self):
        self.fx_list.clear()
        if self.clip():
            for fx in self.clip().effects:self.fx_list.addItem(f"{fx['name']} · {fx['start']:.2f}–{fx['end']:.2f} s")
    def remove_effect(self):
        if self.clip() and self.fx_list.currentRow()>=0:self.timeline.remember();self.clip().effects.pop(self.fx_list.currentRow());self.changed()
    def property_changed(self,name):
        default,low,high=KEYFRAMES[name];self.key_value.setRange(low,high);self.key_value.setValue(default);self.refresh_keys()
    def key_at_head(self):
        if self.clip():self.key_time.setValue(max(0,min(self.clip().duration,self.position-self.timeline.starts()[self.selected])))
    def add_key(self):
        c=self.clip()
        if not c:return
        self.timeline.remember();name=self.property.currentText();time=self.key_time.value();points=[p for p in c.keyframes.get(name,[]) if abs(p[0]-time)>.0001];points.append([time,self.key_value.value()]);c.keyframes[name]=sorted(points);self.changed()
    def refresh_keys(self):
        if not hasattr(self,'keys'):return
        self.keys.clear()
        if self.clip():
            for t,value in self.clip().keyframes.get(self.property.currentText(),[]):self.keys.addItem(f'{t:.3f} s → {value:.3f}')
    def remove_key(self):
        if self.clip() and self.keys.currentRow()>=0:self.timeline.remember();self.clip().keyframes[self.property.currentText()].pop(self.keys.currentRow());self.changed()
    def apply_transition(self):
        if not self.clip():return
        if self.selected==len(self.timeline.clips)-1:self.failure('Ein Übergang benötigt einen folgenden Clip.');return
        self.timeline.remember();self.clip().transition=TRANSITIONS[self.transition.currentText()];self.clip().transition_duration=self.transition_length.value();self.changed()
    def play_pause(self):
        if not self.timeline.clips:return
        if self.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState:self.player.pause();return
        if self.preview_state!=self.timeline.state():
            self.player.stop();self.player.setSource(QUrl());path=Path(self.temp.name)/'preview.mp4';snapshot=copy.deepcopy(self.timeline)
            def job(cancel,progress):render(snapshot,path,cancel,progress,preview=True);return True
            if not self.task('Vorschau berechnen',job):return
            self.preview_state=self.timeline.state();self.rendered=True;self.pending_seek=round(self.position*1000);self.player.setSource(QUrl.fromLocalFile(str(path)));self.hint.setText('Berechnete Vorschau mit Ton, Effekten, Keyframes und Übergängen · 640 × 360')
        self.rendered=True
        if self.position>=self.timeline.duration-.02:self.position=0;self.player.setPosition(0)
        self.player.play()
    def save_project(self):
        path=self.timeline.path
        if not path:path,_=QFileDialog.getSaveFileName(self,'Video-Projekt speichern','Repaintko.repaintvideo','Repaintko Video (*.repaintvideo)')
        if not path:return False
        if not path.lower().endswith('.repaintvideo'):path+='.repaintvideo'
        try:self.timeline.save(path);self.sync();return True
        except Exception as exc:self.failure(exc);return False
    def confirm(self):
        if not self.timeline.dirty:return True
        answer=QMessageBox.question(self,'Video-Projekt speichern?','Ungespeicherte Schnittänderungen speichern?',QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel)
        return self.save_project() if answer==QMessageBox.StandardButton.Save else answer==QMessageBox.StandardButton.Discard
    def open_project(self):
        if not self.confirm():return
        path,_=QFileDialog.getOpenFileName(self,'Video-Projekt öffnen','','Repaintko Video (*.repaintvideo)')
        if path:
            try:self.timeline=Timeline.load(path);self.selected=0;self.position=0;self.changed();self.seek(0)
            except Exception as exc:self.failure(exc)
    def export(self):
        if not is_activated(self.preferences):self.failure('Repaintko Plus ist erforderlich.');return
        if not self.timeline.clips:return
        path,_=QFileDialog.getSaveFileName(self,'Video exportieren','Repaintko.mp4','MP4 Video (*.mp4)')
        if not path:return
        if not path.lower().endswith('.mp4'):path+='.mp4'
        snapshot=copy.deepcopy(self.timeline)
        def job(cancel,progress):render(snapshot,path,cancel,progress);return True
        if self.task('MP4 exportieren',job):self.hint.setText('MP4 exportiert: '+path+' · Das editierbare Projekt separat speichern.')
    def closeEvent(self,event):
        if self.busy or not self.confirm():event.ignore();return
        self.player.stop();self.player.setSource(QUrl());event.accept()
