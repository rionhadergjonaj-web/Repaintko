"""Movable, non-destructive preview before inserting a new image layer."""
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt,QRectF
from PySide6.QtGui import QPainter,QColor,QPen
from PySide6.QtWidgets import QWidget,QDialog,QVBoxLayout,QHBoxLayout,QLabel,QSpinBox,QDialogButtonBox,QMessageBox
from document import MAX_PIXELS


class PlacementPreview(QWidget):
    def __init__(self,dialog,document,image):
        super().__init__();self.dialog=dialog;self.original_size=document.image.size;self.image_size=image.size
        base=document.composite().copy();base.thumbnail((1000,700));self.base=ImageQt(base)
        preview=image.copy();preview.thumbnail((1000,700));self.overlay=ImageQt(preview)
        self.paper=QColor(document.paper_color);self.drag=None
        self.extent=(max(document.image.width,image.width)*1.5,max(document.image.height,image.height)*1.5)
        self.setMinimumSize(240,160);self.setCursor(Qt.CursorShape.OpenHandCursor)

    def geometry_values(self):
        d=self.dialog
        width=max(self.extent[0],d.x.value()+self.image_size[0])
        height=max(self.extent[1],d.y.value()+self.image_size[1])
        scale=min((self.width()-16)/width,(self.height()-16)/height)
        return scale,(self.width()-width*scale)/2,(self.height()-height*scale)/2

    def paintEvent(self,event):
        p=QPainter(self);p.fillRect(self.rect(),QColor('#121923'))
        scale,ox,oy=self.geometry_values();p.translate(ox,oy);p.scale(scale,scale)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        x,y=self.dialog.x.value(),self.dialog.y.value();w,h=self.image_size
        p.fillRect(QRectF(0,0,max(self.original_size[0],x+w),max(self.original_size[1],y+h)),self.paper)
        p.drawImage(QRectF(0,0,*self.original_size),self.base)
        p.drawImage(QRectF(x,y,w,h),self.overlay)
        p.setPen(QPen(QColor('#63e6be'),2/scale,Qt.PenStyle.DashLine));p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(x,y,w,h))

    def mousePressEvent(self,event):
        if event.button()!=Qt.MouseButton.LeftButton:return
        scale,ox,oy=self.geometry_values();x=(event.position().x()-ox)/scale;y=(event.position().y()-oy)/scale
        dx,dy=self.dialog.x.value(),self.dialog.y.value()
        if dx<=x<=dx+self.image_size[0] and dy<=y<=dy+self.image_size[1]:
            self.drag=(event.position(),dx,dy,scale);self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self,event):
        if self.drag:
            start,x,y,scale=self.drag;delta=event.position()-start
            self.dialog.x.setValue(max(0,round(x+delta.x()/scale)))
            self.dialog.y.setValue(max(0,round(y+delta.y()/scale)))

    def mouseReleaseEvent(self,event):
        self.drag=None;self.setCursor(Qt.CursorShape.OpenHandCursor)


class PlacementDialog(QDialog):
    def __init__(self,document,image,parent=None):
        super().__init__(parent);self.document=document;self.image=image
        self.setWindowTitle('Bild platzieren · neue Ebene')
        layout=QVBoxLayout(self)
        hint=QLabel('Bild mit der Maus verschieben. „Platzieren“ legt eine eigene Ebene an.\nDer bisherige Inhalt bleibt unverändert. Esc bricht ab.');hint.setWordWrap(True);layout.addWidget(hint)
        row=QHBoxLayout();self.x=QSpinBox();self.y=QSpinBox()
        for title,field in (('X',self.x),('Y',self.y)):
            field.setRange(0,64000);field.setSuffix(' px');row.addWidget(QLabel(title));row.addWidget(field)
        layout.addLayout(row)
        self.preview=PlacementPreview(self,document,image);layout.addWidget(self.preview,1)
        self.x.valueChanged.connect(self.preview.update);self.y.valueChanged.connect(self.preview.update)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Platzieren')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Abbrechen')
        buttons.accepted.connect(self.validate);buttons.rejected.connect(self.reject);layout.addWidget(buttons)
        available=self.screen().availableGeometry();self.resize(min(900,available.width()-40),min(650,available.height()-70))

    def validate(self):
        width=max(self.document.image.width,self.x.value()+self.image.width)
        height=max(self.document.image.height,self.y.value()+self.image.height)
        if width*height>min(MAX_PIXELS,128_000_000//(len(self.document.layers)+1)):
            QMessageBox.warning(self,'Bild zu groß','Diese Position überschreitet das Pixel-Limit. Bitte das Bild weiter nach links oder oben verschieben.');return
        self.accept()
