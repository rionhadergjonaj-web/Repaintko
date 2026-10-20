"""RGB color picker with a saturation/value field and hue strip."""
from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QLinearGradient
from PySide6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLabel, QSpinBox, QLineEdit, QDialogButtonBox)


class ColorField(QWidget):
    changed = Signal(float, float)

    def __init__(self):
        super().__init__()
        self.hue, self.saturation, self.value = 0.0, 1.0, 1.0
        self.setMinimumSize(180,150)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setAccessibleName('Sättigung und Helligkeit')

    def paintEvent(self,event):
        painter=QPainter(self)
        horizontal=QLinearGradient(0,0,max(1,self.width()-1),0)
        horizontal.setColorAt(0,QColor('white'))
        horizontal.setColorAt(1,QColor.fromHsvF(self.hue,1,1))
        painter.fillRect(self.rect(),horizontal)
        vertical=QLinearGradient(0,0,0,max(1,self.height()-1))
        vertical.setColorAt(0,QColor(0,0,0,0));vertical.setColorAt(1,QColor('black'))
        painter.fillRect(self.rect(),vertical)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        point=QPointF(self.saturation*(self.width()-1),(1-self.value)*(self.height()-1))
        painter.setPen(QPen(QColor('#101720'),3));painter.drawEllipse(point,7,7)
        painter.setPen(QPen(QColor('white'),1.5));painter.drawEllipse(point,7,7)

    def select(self,event):
        self.changed.emit(max(0,min(1,event.position().x()/max(1,self.width()-1))),
                          1-max(0,min(1,event.position().y()/max(1,self.height()-1))))

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:self.select(event)

    def mouseMoveEvent(self,event):
        if event.buttons() & Qt.MouseButton.LeftButton:self.select(event)


class HueStrip(QWidget):
    changed=Signal(float)

    def __init__(self):
        super().__init__();self.hue=0.0;self.setFixedHeight(30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName('Farbton; Pfeiltasten ändern den Farbton')

    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient=QLinearGradient(10,0,max(11,self.width()-10),0)
        for i in range(7):gradient.setColorAt(i/6,QColor.fromHsvF((i/6)%1,1,1))
        painter.setPen(Qt.PenStyle.NoPen);painter.setBrush(gradient)
        painter.drawRoundedRect(10,11,self.width()-20,8,4,4)
        painter.setBrush(QColor.fromHsvF(self.hue,1,1));painter.setPen(QPen(QColor('white'),2))
        painter.drawEllipse(QPointF(10+self.hue*(self.width()-20),15),9,9)

    def select(self,event):self.changed.emit(max(0,min(.999999,(event.position().x()-10)/max(1,self.width()-20))))
    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:self.setFocus();self.select(event)
    def mouseMoveEvent(self,event):
        if event.buttons() & Qt.MouseButton.LeftButton:self.select(event)
    def keyPressEvent(self,event):
        if event.key() in (Qt.Key.Key_Left,Qt.Key.Key_Right):
            self.changed.emit((self.hue+(1 if event.key()==Qt.Key.Key_Right else -1)/360)%1)
        else:super().keyPressEvent(event)


class ColorPicker(QDialog):
    def __init__(self,initial,parent=None):
        super().__init__(parent)
        self.setWindowTitle('Farbe auswählen');self.resize(570,400)
        self.color=QColor(initial);self.original=QColor(initial);self.hue=max(0,self.color.hsvHueF())
        layout=QVBoxLayout(self);top=QHBoxLayout();layout.addLayout(top,1)
        previews=QVBoxLayout();top.addLayout(previews)
        previews.addWidget(QLabel('Bisher'));self.old=QLabel();self.old.setMinimumWidth(85)
        self.old.setStyleSheet('background:'+self.original.name()+';');previews.addWidget(self.old,1)
        previews.addWidget(QLabel('Neue Farbe'));self.swatch=QLabel();previews.addWidget(self.swatch,1)
        self.field=ColorField();top.addWidget(self.field,1)
        self.strip=HueStrip();layout.addWidget(self.strip)
        rgb=QHBoxLayout();layout.addLayout(rgb);self.channels=[]
        for label in ('R','G','B'):
            rgb.addWidget(QLabel(label));spin=QSpinBox();spin.setRange(0,255)
            spin.setAccessibleName({'R':'Rot','G':'Grün','B':'Blau'}[label]);rgb.addWidget(spin)
            self.channels.append(spin);spin.valueChanged.connect(self.from_rgb)
        form=QFormLayout();layout.addLayout(form);self.hex=QLineEdit();self.hex.setMaxLength(7)
        self.hex.setPlaceholderText('#RRGGBB');form.addRow('Hex',self.hex)
        self.hex.textEdited.connect(self.from_hex)
        self.error=QLabel('');layout.addWidget(self.error)
        self.buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept);self.buttons.rejected.connect(self.reject);layout.addWidget(self.buttons)
        self.field.changed.connect(self.from_field);self.strip.changed.connect(self.from_hue)
        self.sync()

    def sync(self,hex_text=True):
        for spin,value in zip(self.channels,(self.color.red(),self.color.green(),self.color.blue())):
            spin.blockSignals(True);spin.setValue(value);spin.blockSignals(False)
        if hex_text:self.hex.setText(self.color.name().upper())
        self.error.clear();self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
        self.swatch.setStyleSheet('background:'+self.color.name()+';')
        self.field.hue=self.strip.hue=self.hue
        self.field.saturation=self.color.hsvSaturationF();self.field.value=self.color.valueF()
        self.field.update();self.strip.update()

    def from_rgb(self):
        self.color=QColor(*(spin.value() for spin in self.channels))
        if self.color.hsvHueF()>=0:self.hue=self.color.hsvHueF()
        self.sync()

    def from_hex(self,text):
        value=text.lstrip('#')
        if len(value)==6 and all(c in '0123456789abcdefABCDEF' for c in value):
            self.color=QColor('#'+value)
            if self.color.hsvHueF()>=0:self.hue=self.color.hsvHueF()
            self.sync(False)
        else:
            self.error.setText('Bitte sechs Hex-Zeichen eingeben, z. B. #6B92B8.')
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def from_field(self,saturation,value):
        self.color=QColor.fromHsvF(self.hue,saturation,value);self.sync()

    def from_hue(self,hue):
        self.hue=hue;self.color=QColor.fromHsvF(hue,self.field.saturation,self.field.value);self.sync()
