"""Plus object-removal mask editor with a local, cancellable preview."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from PIL import Image,ImageDraw
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt,QRectF,QTimer
from PySide6.QtGui import QPainter,QColor,QPen,QPointingDevice
from PySide6.QtWidgets import QWidget,QDialog,QVBoxLayout,QHBoxLayout,QLabel,QSpinBox,QComboBox,QPushButton,QCheckBox,QDialogButtonBox,QMessageBox
from local_ai import inpaint,transparent_remove


class MaskView(QWidget):
    def __init__(self,dialog,source):
        super().__init__();self.dialog=dialog
        preview=source.copy();preview.thumbnail((1600,1200))
        self.original=ImageQt(preview);self.picture=self.original;self.mask=Image.new('L',preview.size)
        self.overlay=None;self.previous=None;self.erase=False
        self.setMinimumSize(220,150);self.setCursor(Qt.CursorShape.CrossCursor)

    def rectangle(self):
        scale=min(self.width()/self.mask.width,self.height()/self.mask.height)
        return QRectF((self.width()-self.mask.width*scale)/2,(self.height()-self.mask.height*scale)/2,self.mask.width*scale,self.mask.height*scale)

    def paintEvent(self,event):
        p=QPainter(self);p.fillRect(self.rect(),QColor('#151b25'));rect=self.rectangle()
        p.save();p.setClipRect(rect)
        for y in range(int(rect.top()),int(rect.bottom())+1,18):
            for x in range(int(rect.left()),int(rect.right())+1,18):
                color='#c2c8d0' if ((x-int(rect.left()))//18+(y-int(rect.top()))//18)%2 else '#e8ecf1'
                p.fillRect(x,y,18,18,QColor(color))
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        original=self.dialog.show_original.isChecked()
        p.drawImage(rect,self.original if original else self.picture)
        if self.overlay is not None and self.dialog.result_image is None:p.drawImage(rect,self.overlay)
        p.restore()

    def point(self,event):
        rect=self.rectangle()
        if not rect.contains(event.position()):return None
        return (min(self.mask.width-1,max(0,int((event.position().x()-rect.left())*self.mask.width/rect.width()))),
                min(self.mask.height-1,max(0,int((event.position().y()-rect.top())*self.mask.height/rect.height()))))

    def mark(self,point):
        if point is None:return
        self.dialog.invalidate();pen=ImageDraw.Draw(self.mask)
        width=self.dialog.brush.value();fill=0 if self.erase else 255
        pen.line([self.previous or point,point],fill=fill,width=width)
        radius=width/2
        for x,y in (self.previous or point,point):pen.ellipse((x-radius,y-radius,x+radius,y+radius),fill=fill)
        overlay=Image.new('RGBA',self.mask.size,(255,60,80,0));overlay.putalpha(self.mask.point(lambda p:round(p*0.48)))
        self.overlay=ImageQt(overlay);self.previous=point;self.update()

    def mousePressEvent(self,event):
        if self.dialog.busy or event.button() not in (Qt.MouseButton.LeftButton,Qt.MouseButton.RightButton):return
        self.erase=event.button()==Qt.MouseButton.RightButton;self.previous=self.point(event);self.mark(self.previous)

    def mouseMoveEvent(self,event):
        if self.previous is not None and not self.dialog.busy:self.mark(self.point(event))

    def mouseReleaseEvent(self,event):
        if self.previous is not None and not self.dialog.busy:self.mark(self.point(event))
        self.previous=None


class RemovalDialog(QDialog):
    def __init__(self,source,parent=None):
        super().__init__(parent);self.source=source.copy();self.result_image=None
        self.busy=False;self.cancel=Event();self.control={};self.future=None
        self.setWindowTitle('Repaintko Plus · Objekte entfernen')
        layout=QVBoxLayout(self)
        hint=QLabel('Person oder Objekt vollständig rot übermalen, dann Vorschau berechnen.\nRechte Maustaste entfernt Markierungen. Bearbeitet wird die aktive Ebene; das Original bleibt erhalten.');hint.setWordWrap(True);layout.addWidget(hint)
        row=QHBoxLayout();self.mode=QComboBox();self.mode.addItems(['Hintergrund ergänzen (lokale KI)','Transparent entfernen'])
        self.brush=QSpinBox();self.brush.setRange(3,200);self.brush.setValue(35)
        row.addWidget(self.mode,1);row.addWidget(QLabel('Pinsel'));row.addWidget(self.brush);layout.addLayout(row)
        self.show_original=QCheckBox('Original zum Vergleichen anzeigen')
        self.view=MaskView(self,source);layout.addWidget(self.view,1)
        self.show_original.toggled.connect(self.view.update);layout.addWidget(self.show_original)
        row=QHBoxLayout();self.clear=QPushButton('Markierung löschen');self.calculate=QPushButton('Vorschau berechnen')
        row.addWidget(self.clear);row.addWidget(self.calculate);layout.addLayout(row)
        self.status=QLabel('Läuft auf deinem Rechner. Keine Bild-Uploads.');self.status.setWordWrap(True);layout.addWidget(self.status)
        self.buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        self.apply=self.buttons.button(QDialogButtonBox.StandardButton.Ok);self.apply.setText('Als neue Ebene übernehmen');self.apply.setEnabled(False)
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Abbrechen')
        self.buttons.accepted.connect(self.accept);self.buttons.rejected.connect(self.reject);layout.addWidget(self.buttons)
        self.clear.clicked.connect(self.clear_mask);self.calculate.clicked.connect(self.compute);self.mode.currentIndexChanged.connect(self.invalidate)
        available=self.screen().availableGeometry();self.resize(min(980,available.width()-40),min(760,available.height()-70))

    def invalidate(self):
        self.result_image=None;self.apply.setEnabled(False);self.view.picture=self.view.original;self.view.update()

    def clear_mask(self):
        self.invalidate();self.view.mask=Image.new('L',self.view.mask.size);self.view.overlay=None;self.view.update()

    def set_busy(self,value):
        self.busy=value
        for widget in (self.mode,self.brush,self.clear,self.calculate):widget.setEnabled(not value)
        self.apply.setEnabled(not value and self.result_image is not None)

    def compute(self):
        if self.busy:return
        if not self.view.mask.getbbox():
            self.status.setText('Markiere zuerst die Person oder das Objekt.');return
        self.result_image=None;self.cancel=Event();self.control={};self.set_busy(True)
        self.show_original.setChecked(False)
        mask=self.view.mask.resize(self.source.size,Image.Resampling.NEAREST)
        self.pool=ThreadPoolExecutor(max_workers=1)
        if self.mode.currentIndex()==0:
            self.status.setText('Die lokale KI ergänzt den Hintergrund … Beim ersten Mal wird das Modell geladen.')
            self.future=self.pool.submit(inpaint,self.source,mask,self.cancel,self.control)
        else:
            self.status.setText('Transparenz wird berechnet …');self.future=self.pool.submit(transparent_remove,self.source,mask)
        self.timer=QTimer(self);self.timer.timeout.connect(self.poll);self.timer.start(100)

    def poll(self):
        if not self.future.done():return
        self.timer.stop();self.timer.deleteLater();self.pool.shutdown(wait=False)
        if self.cancel.is_set():return
        try:
            self.result_image=self.future.result()
            preview=self.result_image.resize(self.view.mask.size,Image.Resampling.LANCZOS)
            self.view.picture=ImageQt(preview);self.view.update()
            self.status.setText('Vorschau fertig. Vergleiche mit dem Original und übernimm das Ergebnis, wenn es passt.')
        except Exception as exc:
            self.status.setText('Die Berechnung ist fehlgeschlagen. Das Original wurde nicht verändert.')
            QMessageBox.warning(self,'Objekte entfernen',str(exc))
        self.set_busy(False)

    def accept(self):
        if self.result_image is not None and not self.busy:super().accept()

    def reject(self):
        self.cancel.set()
        run=self.control.get('run')
        if run is not None:run.terminate=True
        super().reject()
