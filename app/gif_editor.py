"""GIF mode controls using the editor's existing canvas and tools."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt,QTimer,QSize,QRectF,QEvent
from PySide6.QtGui import QIcon,QPixmap,QPainter,QPainterPath,QPen,QColor
from PySide6.QtWidgets import (QDockWidget,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QSpinBox,QListWidget,QListWidgetItem,QFileDialog,QMessageBox,QDialog,QProgressDialog,QScrollArea)
from animation import Animation

class GifPanel(QDockWidget):
    def __init__(self,host,source):
        super().__init__('GIF-Frames',host);self.host=host;self.animation=Animation(source)
        self.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        body=QWidget();self.setWidget(body);layout=QVBoxLayout(body);layout.setContentsMargins(6,3,6,3)
        row=QHBoxLayout();layout.addLayout(row)
        for title,callback in [('+ Frame',lambda:self.change(lambda:self.animation.add())),('Duplizieren',lambda:self.change(lambda:self.animation.add(True))),('Bilder als Frames',self.import_frames),('Löschen',lambda:self.change(self.animation.remove)),('←',lambda:self.change(lambda:self.animation.move(-1))),('→',lambda:self.change(lambda:self.animation.move(1)))]:
            button=QPushButton(title);button.clicked.connect(callback);row.addWidget(button)
        row=QHBoxLayout();layout.addLayout(row)
        fps_group=QWidget();fps_layout=QHBoxLayout(fps_group);fps_layout.setContentsMargins(0,0,0,0);fps_layout.setSpacing(6)
        fps_layout.addWidget(QLabel('FPS'));self.fps=QSpinBox();self.fps.setRange(1,50);self.fps.setValue(10);self.fps.setFixedWidth(80);fps_layout.addWidget(self.fps);row.addWidget(fps_group);row.addStretch()
        self.fps.valueChanged.connect(self.set_fps)
        for title,callback in [('Vorschau',self.preview),('GIF speichern',self.save)]:
            button=QPushButton(title);button.clicked.connect(callback);row.addWidget(button)
        self.onion=QPushButton();self.onion.setCheckable(True);self.onion.setFixedSize(36,32)
        self.onion.setToolTip('Vorherigen Frame mit 26 % Deckkraft anzeigen');self.onion.setAccessibleName('Zwiebelschicht')
        icon=QPixmap(32,32);icon.fill(Qt.GlobalColor.transparent);painter=QPainter(icon);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor('#714766'),1.5));painter.setBrush(QColor('#edc7df'))
        bulb=QPainterPath();bulb.moveTo(16,9);bulb.cubicTo(12,15,5,14,5,22);bulb.cubicTo(5,33,27,33,27,22);bulb.cubicTo(27,14,20,15,16,9);painter.drawPath(bulb)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for side in (-1,1):
            line=QPainterPath();line.moveTo(16,11);line.cubicTo(16+side*8,20,16+side*8,25,16,29);painter.drawPath(line)
        painter.setPen(QPen(QColor('#70bb80'),2));painter.drawLine(16,10,12,2);painter.drawLine(16,10,18,1);painter.drawLine(16,10,22,4);painter.end()
        self.onion.setIcon(QIcon(icon));self.onion.setIconSize(QSize(28,28));row.addWidget(self.onion)
        self.onion_cache=None;self.onion_key=None
        self.onion.toggled.connect(lambda checked:self.host.canvas.update())
        self.frames=QListWidget();self.frames.setFlow(QListWidget.Flow.LeftToRight);self.frames.setWrapping(False);self.frames.setFixedHeight(62)
        layout.addWidget(self.frames);self.frames.currentRowChanged.connect(self.select)
        self.note=QLabel('Alle Frames verwenden die gleiche Bildgröße. GIF unterstützt 256 Farben und nur vollständig transparente oder deckende Pixel.');self.note.setWordWrap(True);layout.addWidget(self.note)
        self.rebuild()
    def onion_image(self):
        if not self.onion.isChecked() or self.animation.index==0:return None
        previous=self.animation.frames[self.animation.index-1]
        key=(id(previous),previous.revision,previous.image.size)
        if key!=self.onion_key:
            self.onion_cache=ImageQt(previous.composite(transparent=True).convert('RGBA'));self.onion_key=key
        return self.onion_cache

    def set_fps(self,value):self.animation.fps=value;self.host.refresh(False)
    def rebuild(self):
        self.frames.blockSignals(True);self.frames.clear()
        for i,frame in enumerate(self.animation.frames):self.frames.addItem(f'Frame {i+1}')
        self.frames.setCurrentRow(self.animation.index);self.frames.blockSignals(False)
    def select(self,index):
        if index<0:return
        self.animation.index=index;self.host.doc=self.animation.frames[index];self.host.canvas.start=None;self.host.canvas.polygon=[];self.host.refresh()
    def change(self,action):
        try:action();self.rebuild();self.select(self.animation.index)
        except Exception as exc:QMessageBox.warning(self,'GIF-Frames',str(exc))
    def import_frames(self):
        paths,_=QFileDialog.getOpenFileNames(self,'Bilder als Frames hinzufügen','','Bilder (*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff *.gif)')
        for path in paths:
            try:self.animation.add(path=path)
            except Exception as exc:QMessageBox.warning(self,'Frames importieren',str(exc));break
        self.rebuild();self.select(self.animation.index)
    def save(self,as_new=False,copy=False):
        path=None if as_new or copy else self.animation.path
        if not path:
            path,_=QFileDialog.getSaveFileName(self,'Animation als GIF speichern',self.animation.path or 'Repaintko-Animation.gif','GIF-Animation (*.gif)')
            if not path:return False
        if not path.lower().endswith('.gif'):path+='.gif'
        if copy and self.animation.path and Path(path).resolve()==Path(self.animation.path).resolve():
            QMessageBox.warning(self,'Als Kopie speichern','Bitte einen anderen Dateinamen wählen.');return False
        progress=QProgressDialog('GIF wird berechnet …',None,0,0,self.host);progress.setWindowModality(Qt.WindowModality.ApplicationModal);progress.setMinimumDuration(0)
        pool=ThreadPoolExecutor(max_workers=1);future=pool.submit(self.animation.export,path,self.host.transparent_save.isChecked())
        timer=QTimer(progress);timer.timeout.connect(lambda:progress.accept() if future.done() else None);timer.start(30)
        progress.exec();timer.stop()
        try:
            future.result();self.host.refresh(False);self.host.statusBar().showMessage('GIF gespeichert: '+path,8000);return True
        except Exception as exc:QMessageBox.warning(self,'GIF speichern',str(exc));return False
        finally:pool.shutdown(wait=False)
    def preview(self):
        dialog=GifPreview(self.animation,self.host);dialog.exec();dialog.timer.stop()

class PreviewCanvas(QWidget):
    def __init__(self):
        super().__init__();self.image=None;self.zoom=1.0
    def update_size(self):
        if self.image is not None:self.setFixedSize(max(1,round(self.image.width()*self.zoom)),max(1,round(self.image.height()*self.zoom)))
        self.update()
    def paintEvent(self,event):
        painter=QPainter(self)
        tile=QPixmap(24,24);tile.fill(QColor('#eeeeee'));check=QPainter(tile);check.fillRect(0,0,12,12,QColor('#cccccc'));check.fillRect(12,12,12,12,QColor('#cccccc'));check.end()
        from PySide6.QtGui import QBrush
        painter.fillRect(event.rect(),QBrush(tile))
        if self.image is not None:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform,self.zoom<1)
            painter.drawImage(QRectF(0,0,self.width(),self.height()),self.image)

class GifPreview(QDialog):
    def __init__(self,animation,parent=None):
        super().__init__(parent);self.animation=animation;self.index=0;self.setWindowTitle('GIF-Vorschau');self.resize(700,500)
        layout=QVBoxLayout(self);self.scroll=QScrollArea();self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter);self.canvas=PreviewCanvas();self.scroll.setWidget(self.canvas);layout.addWidget(self.scroll,1)
        self.scroll.viewport().installEventFilter(self)
        row=QHBoxLayout();layout.addLayout(row)
        for title,callback in [('−',lambda:self.set_zoom(self.canvas.zoom/1.25)),('+',lambda:self.set_zoom(self.canvas.zoom*1.25)),('100 %',lambda:self.set_zoom(1)),('Einpassen',self.fit)]:
            button=QPushButton(title);button.clicked.connect(callback);row.addWidget(button)
        self.zoom_value=QSpinBox();self.zoom_value.setRange(1,1600);self.zoom_value.setSuffix(' %');self.zoom_value.setValue(100);self.zoom_value.valueChanged.connect(lambda value:self.set_zoom(value/100));row.addWidget(self.zoom_value)
        self.counter=QLabel();layout.addWidget(self.counter)
        self.timer=QTimer(self);self.timer.timeout.connect(self.tick);self.tick();QTimer.singleShot(0,self.fit)
    def set_zoom(self,value):
        self.canvas.zoom=max(.01,min(16,value));self.zoom_value.blockSignals(True);self.zoom_value.setValue(round(self.canvas.zoom*100));self.zoom_value.blockSignals(False);self.canvas.update_size()
    def fit(self):
        if self.canvas.image is not None:self.set_zoom(min((self.scroll.viewport().width()-4)/self.canvas.image.width(),(self.scroll.viewport().height()-4)/self.canvas.image.height(),1))
    def tick(self):
        frame=self.animation.frames[self.index].composite(preserve_alpha=True)
        self.canvas.image=ImageQt(frame.convert('RGBA'));self.canvas.update_size()
        self.counter.setText(f'Frame {self.index+1} / {len(self.animation.frames)} · {self.animation.fps} FPS')
        self.timer.start(self.animation.durations()[self.index]);self.index=(self.index+1)%len(self.animation.frames)
    def eventFilter(self,watched,event):
        if event.type()==QEvent.Type.Wheel and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.set_zoom(self.canvas.zoom*(1.25 if event.angleDelta().y()>0 else .8));return True
        return super().eventFilter(watched,event)
    def done(self,result):
        self.timer.stop();super().done(result)
