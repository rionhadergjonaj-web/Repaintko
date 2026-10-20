"""Repaintko's hand-written Qt interface. No Tk dependency."""
import math
import os
import sys
import json
from pathlib import Path
from threading import Event
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFont
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt, QRectF, QPointF, QTimer, QStandardPaths, QSettings, QSize, QEvent, QUrl
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QAction, QActionGroup, QKeySequence, QPolygonF, QFontDatabase, QIcon, QImage, QFontMetrics, QPixmap, QPainterPath
from PySide6.QtWidgets import (QApplication, QMainWindow, QStackedWidget, QWidget, QScrollArea, QDockWidget,
    QToolBar, QComboBox, QSpinBox, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QFormLayout, QGridLayout, QFileDialog, QColorDialog, QMessageBox, QInputDialog, QLineEdit,
    QDialog, QDialogButtonBox, QListWidget, QListWidgetItem, QSlider, QCheckBox, QGroupBox, QFontComboBox, QSizePolicy, QProgressDialog)
from tool_icons import tool_icon
from fast_fill import filled_image
from browser_drop import browser_source, download_image
from placement import PlacementDialog
from branding import brand_icon, is_activated, activate
from desktop_icon import sync_desktop_icon, packaged_runtime
from removal_dialog import RemovalDialog
from designs import additional_themes, PLUS_DESIGNS, DesignScrollArea
from wallpaper_addon import WallpaperStore
from spotify import SpotifyWidget, SpotifyMonitor
from timesheet_ui import TimesheetWidget
from gif_editor import GifPanel
from document import Document, DEFAULT_SIZE, PRESETS, checked_size, load_image
from censor import CENSOR_MODES
from color_picker import ColorPicker
from pdf_import import PdfImportDialog, PdfPasswordRequired
from effects import EFFECTS, update_effect_stack, render_effect_stack

TOOLS = ['Pinsel','Füller','Bleistift','Airbrush','Radierer','Zensur','Füllen','Pipette',
         'Linie','Rechteck','Rundrechteck','Ellipse','Dreieck','Polygon','Text','Auswahl','Lupe']
BRUSHES = {'Pinsel','Füller','Bleistift','Airbrush','Radierer','Zensur'}
IMAGE_SUFFIXES = {'.png','.jpg','.jpeg','.bmp','.webp','.tif','.tiff','.gif'}
DROP_SUFFIXES = IMAGE_SUFFIXES | {'.pdf','.repaintko','.repainko'}
FILE_FILTER = 'Repaintko-Projekt (*.repaintko *.repainko);;PNG (*.png);;JPEG (*.jpg *.jpeg);;Bitmap (*.bmp);;WebP (*.webp);;TIFF (*.tif);;GIF (*.gif)'
STYLE = '''
QMainWindow,QDialog {background:#151b25;color:#edf3fa;}
QWidget {font-family:Segoe UI;font-size:10pt;color:#edf3fa;background:#202936;}
QMainWindow,QDialog {background:#151b25;}
QToolBar,QDockWidget,QGroupBox {background:#202936;border:0px;}
QToolBar {spacing:5px;padding:6px;}
QMenuBar,QMenu {background:#202936;color:#edf3fa;}
QMenu::item:selected {background:#38566a;}
QPushButton,QToolButton {background:#2e3b4e;border:0;border-radius:5px;padding:8px;}
QPushButton:hover,QToolButton:hover {background:#40556e;}
QPushButton:checked {background:#63e6be;color:#112a23;}
QPushButton#primary {background:#63e6be;color:#112a23;font-weight:bold;}
QComboBox,QSpinBox,QLineEdit,QListWidget {background:#111923;border:1px solid #3a4b62;border-radius:4px;padding:5px;}
QListWidget::item {padding:6px;}
QListWidget::item:selected {background:#397562;color:white;}
QScrollArea {border:0;}
QScrollBar:vertical {background:#18212d;width:12px;}
QScrollBar:horizontal {background:#18212d;height:12px;}
QScrollBar::handle {background:#506179;min-height:20px;min-width:20px;border-radius:5px;}
QGroupBox {margin-top:16px;padding-top:14px;}
QGroupBox::title {subcontrol-origin:margin;color:#9aacbf;}
QLabel#muted {color:#9aacbf;}
QSlider::groove:horizontal {height:5px;background:#3a4b62;}
QSlider::handle:horizontal {width:14px;margin:-5px 0;background:#63e6be;border-radius:7px;}
QStatusBar {background:#151b25;}
'''

LIGHT_STYLE = STYLE
for dark,light in {
    '#151b25':'#f4f6fa','#edf3fa':'#172033','#202936':'#ffffff',
    '#38566a':'#d9e8f0','#2e3b4e':'#e4eaf2','#40556e':'#d0dfec',
    '#63e6be':'#63d9b4','#111923':'#ffffff','#3a4b62':'#b4c1d1',
    '#397562':'#28745e','#18212d':'#e9eef5','#506179':'#a6b5c7',
    '#9aacbf':'#526477',
}.items():LIGHT_STYLE=LIGHT_STYLE.replace(dark,light)
LIGHT_STYLE+='\nQPushButton:disabled,QToolButton:disabled {color:#8491a2;background:#edf1f6;}\n'


def tinted_style(background,panel,button,hover,field,border,accent,selection,muted):
    replacements={'#151b25':background,'#202936':panel,'#2e3b4e':button,
                  '#40556e':hover,'#38566a':hover,'#111923':field,
                  '#3a4b62':border,'#63e6be':accent,'#397562':selection,
                  '#18212d':background,'#506179':border,'#9aacbf':muted}
    import re
    return re.sub(r'#[0-9a-f]{6}',lambda match:replacements.get(match.group(),match.group()),STYLE)


THEMES={
    'lavender':('Lavendel',tinted_style('#201b30','#302842','#443959','#5c4b78','#191426','#796694','#c7a6ff','#69508b','#c6b9de'),'#161021'),
    'amber':('Bernstein',tinted_style('#282016','#3a2f21','#51432f','#6e573a','#211a10','#88714a','#ffd17a','#826335','#dcc9a7'),'#1b150e'),
    'graphite':('Graphit',tinted_style('#1a1a1a','#292929','#3b3b3b','#505050','#121212','#686868','#d3e0e8','#596770','#c0c0c0'),'#101010'),
    'light':('Hell',LIGHT_STYLE,'#dce3ed'),
    'dark':('Dunkel',STYLE,'#101720'),
    'ocean':('Ozean',tinted_style('#0d1c30','#142b43','#21405e','#2d577a','#0b2035',
                                 '#456a8c','#67d5ff','#245c7a','#a8c5dd'),'#081525'),
    'forest':('Wald',tinted_style('#142019','#213329','#304b3b','#42634d','#10251a',
                                  '#557762','#a0db82','#386b47','#b4ccb9'),'#0c1811'),
    'sunset':('Abendrot',tinted_style('#291a29','#3b2638','#55384d','#724963','#261625',
                                      '#88617e','#ffb18d','#874961','#d8b8cb'),'#1d111e'),
}

THEMES.update(additional_themes(tinted_style))


def image_rect(a,b):
    return (min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0])+1,max(a[1],b[1])+1)


class Preview(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(str(Path(__file__).parent/'assets'/'repainko.ico')))
        self.picture = None
        self.native = False
        self.setMinimumSize(120,100)
    def set_image(self,image):
        self.picture = ImageQt(image)
        self.update()
    def paintEvent(self,event):
        p = QPainter(self)
        p.fillRect(self.rect(),self.palette().window())
        if self.picture is not None:
            ratio = 1 if self.native else min(self.width()/self.picture.width(),self.height()/self.picture.height())
            w,h = self.picture.width()*ratio,self.picture.height()*ratio
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            p.drawImage(QRectF((self.width()-w)/2,(self.height()-h)/2,w,h),self.picture)


class Canvas(QWidget):
    def __init__(self,window):
        super().__init__()
        self.window = window
        self.zoom = 1.0
        self.start = self.last = self.current = self.hover = self.moving = self.pan = None
        self.polygon = []
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.sync()

    @property
    def doc(self): return self.window.doc

    def sync(self, rebuild=True):
        if rebuild:
            self.surface = ImageQt(self.doc.composite(preserve_alpha=True).convert('RGBA'))
        self.setFixedSize(max(1,round(self.doc.image.width*self.zoom)),max(1,round(self.doc.image.height*self.zoom)))
        self.update()

    def point(self,event):
        return (max(0,min(self.doc.image.width-1,int(event.position().x()/self.zoom))),
                max(0,min(self.doc.image.height-1,int(event.position().y()/self.zoom))))

    def paintEvent(self,event):
        p = QPainter(self)
        r = event.rect()
        tile=QPixmap(24,24);tile.fill(QColor('#eeeeee'))
        checker=QPainter(tile);checker.fillRect(0,0,12,12,QColor('#cccccc'));checker.fillRect(12,12,12,12,QColor('#cccccc'));checker.end()
        p.fillRect(r,QBrush(tile))
        z = self.zoom
        panel=self.window.gif_panel
        onion=panel.onion_image() if panel else None
        if onion is not None:
            p.save();p.setOpacity(.26);p.drawImage(QRectF(0,0,onion.width()*z,onion.height()*z),onion);p.restore()
        box = (max(0,math.floor(r.left()/z)-1),max(0,math.floor(r.top()/z)-1),
               min(self.doc.image.width,math.ceil((r.right()+1)/z)+1),min(self.doc.image.height,math.ceil((r.bottom()+1)/z)+1))
        if box[2]>box[0] and box[3]>box[1]:
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform,z<1)
            p.drawImage(QRectF(box[0]*z,box[1]*z,(box[2]-box[0])*z,(box[3]-box[1])*z),
                        self.surface,QRectF(box[0],box[1],box[2]-box[0],box[3]-box[1]))
        p.scale(z,z)
        if self.window.grid.isChecked() and z>=8:
            p.setPen(QPen(QColor('#a0aaba'),1/z))
            for x in range(box[0],box[2]+1): p.drawLine(QPointF(x,box[1]),QPointF(x,box[3]))
            for y in range(box[1],box[3]+1): p.drawLine(QPointF(box[0],y),QPointF(box[2],y))
        if self.doc.selection:
            x,y,right,bottom = self.doc.selection
            p.setPen(QPen(QColor('#20c997'),2/z,Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(x,y,right-x,bottom-y))
        tool = self.window.tool.currentText()
        if self.start and self.current and tool not in BRUSHES and tool!='Auswahl':
            a,b = self.start,self.current
            x,y,right,bottom = image_rect(a,b)
            p.setPen(QPen(QColor(self.ink),self.window.brush_width.value()))
            p.setBrush(QColor(self.window.bg) if self.window.fill.currentIndex() else Qt.BrushStyle.NoBrush)
            if tool=='Linie': p.drawLine(QPointF(*a),QPointF(*b))
            elif tool=='Ellipse': p.drawEllipse(QRectF(x,y,right-x,bottom-y))
            elif tool=='Dreieck': p.drawPolygon(QPolygonF([QPointF((x+right)/2,y),QPointF(right,bottom),QPointF(x,bottom)]))
            else: p.drawRect(QRectF(x,y,right-x,bottom-y))
        if len(self.polygon)>1:
            p.setPen(QPen(QColor(self.window.fg),self.window.brush_width.value()))
            p.drawPolyline(QPolygonF([QPointF(*a) for a in self.polygon]))
        if self.hover and tool=='Zensur':
            radius = self.window.censor_size.value()/2
            p.setPen(QPen(QColor('#63e6be'),1/z))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(*self.hover),radius,radius)

        import time
        p.resetTransform()
        for message,received in getattr(self,'remote_cursors',{}).values():
            if time.monotonic()-received>3:continue
            x,y=message['x']*z,message['y']*z
            p.setPen(QPen(QColor('#9a78ff'),2));p.drawLine(QPointF(x,y),QPointF(x+9,y+14));p.drawLine(QPointF(x,y),QPointF(x+15,y+4))
            p.drawText(QPointF(x+16,y+18),message['name'][:40])

    def stroke(self,point):
        w = self.window
        bounds = self.doc.stroke(self.last,point,w.tool.currentText(),self.ink,w.bg,
                                w.censor_size.value() if w.tool.currentText()=='Zensur' else w.brush_width.value(),
                                w.censor_mode.currentText(),w.strength.value(),w.brush_opacity.value())
        self.last = point
        x,y,r,b = bounds
        x,y,r,b = max(0,x),max(0,y),min(self.doc.image.width,r),min(self.doc.image.height,b)
        if r>x and b>y:
            painter=QPainter(self.surface)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.drawImage(x,y,ImageQt(self.doc.composite((x,y,r,b),preserve_alpha=True)))
            painter.end()
        self.update(QRectF(x*self.zoom,y*self.zoom,(r-x)*self.zoom,(b-y)*self.zoom).toAlignedRect())
        if getattr(w,'shared_bridge',None):w.shared_bridge.changed((x,y,r,b))

    def mousePressEvent(self,event):
        self.setFocus()
        if event.button()==Qt.MouseButton.MiddleButton:
            self.pan = event.globalPosition()
            return
        if event.button() not in (Qt.MouseButton.LeftButton,Qt.MouseButton.RightButton): return
        a = self.point(event)
        w = self.window
        tool = w.tool.currentText()
        if not self.doc.layers[self.doc.active]['visible'] and tool not in ('Pipette','Lupe','Auswahl'):
            w.statusBar().showMessage('Die aktive Ebene ist ausgeblendet. Im Ebenenfenster sichtbar schalten.',6000)
            return
        self.ink = w.bg if event.button()==Qt.MouseButton.RightButton else w.fg
        if tool=='Pipette':
            w.set_color('#%02x%02x%02x'%self.doc.composite((*a,a[0]+1,a[1]+1)).getpixel((0,0)),event.button()==Qt.MouseButton.RightButton)
        elif tool=='Lupe': w.set_zoom(self.zoom*(0.8 if event.button()==Qt.MouseButton.RightButton else 1.25))
        elif tool=='Füllen':
            w.fill_area(a,self.ink)
        elif tool=='Text': w.add_text(a,self.ink)
        elif tool=='Polygon':
            self.polygon.append(a)
            self.update()
            w.statusBar().showMessage('Polygon: Punkte anklicken, Enter zum Abschließen, Esc zum Abbrechen.')
        else:
            self.start = self.last = self.current = a
            self.moving = None
            if tool in BRUSHES:
                self.doc.begin_stroke(tool)
                # Drawing may switch from the filtered result to the document base.
                if tool!='Zensur':self.sync()
                self.stroke(a)
            elif tool=='Auswahl':
                s = self.doc.selection
                if s and s[0]<=a[0]<s[2] and s[1]<=a[1]<s[3]: self.moving = s
                else: self.doc.selection = None

    def mouseMoveEvent(self,event):
        if self.pan is not None:
            delta = event.globalPosition()-self.pan
            for bar,change in [(self.window.scroll.horizontalScrollBar(),delta.x()),(self.window.scroll.verticalScrollBar(),delta.y())]:
                bar.setValue(bar.value()-round(change))
            self.pan = event.globalPosition()
            return
        old_hover = self.hover
        self.hover = point = self.point(event)
        if self.start:
            tool = self.window.tool.currentText()
            if tool in BRUSHES: self.stroke(point)
            else:
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier and tool!='Auswahl':
                    length = max(abs(point[0]-self.start[0]),abs(point[1]-self.start[1]))
                    point = (self.start[0]+length*(1 if point[0]>=self.start[0] else -1),self.start[1]+length*(1 if point[1]>=self.start[1] else -1))
                self.current = point
                if tool=='Auswahl':
                    self.doc.selection = self.moved_box(point) if self.moving else image_rect(self.start,point)
                self.update()
        if self.window.tool.currentText()=='Zensur':
            radius = self.window.censor_size.value()/2+4
            for pos in (old_hover,self.hover):
                if pos: self.update(QRectF((pos[0]-radius)*self.zoom,(pos[1]-radius)*self.zoom,2*radius*self.zoom,2*radius*self.zoom).toAlignedRect())

    def moved_box(self,point):
        x,y,r,b = self.moving
        nx = max(0,min(self.doc.image.width-(r-x),x+point[0]-self.start[0]))
        ny = max(0,min(self.doc.image.height-(b-y),y+point[1]-self.start[1]))
        return (nx,ny,nx+r-x,ny+b-y)

    def mouseReleaseEvent(self,event):
        if event.button()==Qt.MouseButton.MiddleButton:
            self.pan = None
            return
        if self.start is None: return
        tool = self.window.tool.currentText()
        point = self.point(event)
        if tool in BRUSHES:
            self.stroke(point)
            self.doc.finish_stroke()
        elif tool=='Auswahl':
            if self.moving:
                box = self.moved_box(point)
                self.doc.move_selection(self.moving,*box[:2],self.window.bg)
            else:
                self.doc.selection = image_rect(self.start,point)
                x,y,r,b = self.doc.selection
                if min((r-x)*self.zoom,(b-y)*self.zoom)<3: self.doc.selection=None
        else:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                length=max(abs(point[0]-self.start[0]),abs(point[1]-self.start[1]))
                point=(self.start[0]+length*(1 if point[0]>=self.start[0] else -1),
                       self.start[1]+length*(1 if point[1]>=self.start[1] else -1))
            self.doc.shape(tool,self.start,point,self.ink,self.window.bg,
                           self.window.brush_width.value(),self.window.fill.currentText())
        self.start = self.last = self.current = self.moving = None
        self.window.refresh(rebuild=tool not in BRUSHES)

    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_Escape:
            self.start = self.current = self.last = None
            self.polygon.clear()
            self.doc.selection=None
            self.doc.finish_stroke()
            self.update()
        elif event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter) and len(self.polygon)>=3:
            self.doc.shape('Polygon',self.polygon[0],self.polygon[-1],self.window.fg,self.window.bg,
                           self.window.brush_width.value(),self.window.fill.currentText(),self.polygon)
            self.polygon=[]
            self.window.refresh()
        else: super().keyPressEvent(event)

    def wheelEvent(self,event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.window.set_zoom(self.zoom*(1.25 if event.angleDelta().y()>0 else 0.8))
            event.accept()
        else: event.ignore()

    def leaveEvent(self,event):
        self.hover=None
        self.update()


class EffectsDialog(QDialog):
    def __init__(self,window):
        super().__init__(window)
        self.owner=window
        self.doc=window.doc
        self.base=(self.doc.effect_base if self.doc.effect_base is not None else self.doc.image).convert('RGB')
        self.stack=self.doc.effect_stack
        self.revision=self.doc.revision
        self.worker=ThreadPoolExecutor(max_workers=1)
        self.future=self.pending=None
        self.generation=0
        self.busy=False
        self.closed=False
        self.result=None
        self.setWindowTitle('Repaintko · Fotoeffekte')
        available=window.screen().availableGeometry()
        self.resize(min(1000,available.width()-40),min(700,available.height()-60))
        self.setMinimumSize(560,420)
        outer=QVBoxLayout(self)
        top=QHBoxLayout()
        top.addWidget(QLabel('Aktive Ebene · jeder Fotoeffekt nur einmal'))
        self.scope=QComboBox()
        self.scope.addItems(['Ganzes Bild']+(['Auswahl'] if self.doc.selection else []))
        if self.doc.selection: self.scope.setCurrentText('Auswahl')
        top.addWidget(self.scope)
        outer.addLayout(top)
        body=QHBoxLayout()
        self.list=QListWidget()
        self.list.setMaximumWidth(215)
        self.keys=[k for k,s in EFFECTS.items() if s.group!='Zensur']
        for key in self.keys: self.list.addItem(EFFECTS[key].title)
        body.addWidget(self.list)
        self.preview=Preview()
        body.addWidget(self.preview,1)
        outer.addLayout(body,1)
        self.description=QLabel()
        self.description.setWordWrap(True)
        outer.addWidget(self.description)
        row=QHBoxLayout()
        self.original=QCheckBox('Original anzeigen')
        row.addWidget(self.original)
        self.detail=QCheckBox('1:1-Detail')
        row.addWidget(self.detail)
        self.amount_label=QLabel()
        row.addStretch()
        row.addWidget(self.amount_label)
        outer.addLayout(row)
        self.slider=QSlider(Qt.Orientation.Horizontal)
        outer.addWidget(self.slider)
        self.note=QLabel('')
        self.note.setWordWrap(True)
        outer.addWidget(self.note)
        buttons=QHBoxLayout()
        reset=QPushButton('Standardstärke')
        self.reset_button=reset
        reset.clicked.connect(lambda:self.slider.setValue(EFFECTS[self.key].default))
        buttons.addWidget(reset)
        buttons.addStretch()
        cancel=QPushButton('Abbrechen')
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        self.apply_button=QPushButton('Übernehmen')
        self.apply_button.setObjectName('primary')
        self.apply_button.clicked.connect(self.apply)
        buttons.addWidget(self.apply_button)
        outer.addLayout(buttons)
        self.debounce=QTimer(self)
        self.debounce.setSingleShot(True)
        self.debounce.timeout.connect(self.queue_preview)
        self.poller=QTimer(self)
        self.poller.setInterval(30)
        self.poller.timeout.connect(self.poll)
        self.slider.valueChanged.connect(self.changed)
        self.list.currentRowChanged.connect(self.choose)
        self.scope.currentTextChanged.connect(self.changed)
        self.original.toggled.connect(self.show_preview)
        self.detail.toggled.connect(self.changed)
        self.list.setCurrentRow(0)

    @property
    def box(self): return self.doc.selection if self.scope.currentText()=='Auswahl' else (0,0,*self.base.size)

    def choose(self,index):
        if index<0:return
        self.key=self.keys[index]
        spec=EFFECTS[self.key]
        self.description.setText(spec.description)
        self.slider.blockSignals(True)
        self.slider.setRange(spec.minimum,spec.maximum)
        entry=next((e for e in self.stack if e[0]==self.key),None)
        self.slider.setValue(round(entry[1]) if entry else spec.default)
        self.slider.blockSignals(False)
        self.changed()

    def changed(self,*_):
        if self.busy:return
        self.generation+=1
        spec=EFFECTS[self.key]
        self.amount_label.setText(f'{self.slider.value()} {spec.unit}')
        self.note.setText('Vorschau wird berechnet …')
        self.debounce.start(80)

    def queue_preview(self):
        origin=(0,0)
        if self.detail.isChecked():
            x,y,right,bottom=self.box
            width,height=min(750,right-x),min(450,bottom-y)
            origin=(x+(right-x-width)//2,y+(bottom-y-height)//2)
            self.thumb=self.base.crop((*origin,origin[0]+width,origin[1]+height))
            ratio=1
        else:
            ratio=min(1,750/self.base.width,450/self.base.height)
            self.thumb=self.base.resize((max(1,round(self.base.width*ratio)),max(1,round(self.base.height*ratio))),Image.Resampling.LANCZOS,reducing_gap=3)
        stack=update_effect_stack(self.stack,self.key,self.slider.value(),self.box)
        self.pending=('preview',self.generation,self.thumb,stack,ratio,origin)
        self.poller.start()

    def show_preview(self,*_):
        if hasattr(self,'thumb'):
            self.preview.native=self.detail.isChecked()
            self.preview.set_image(self.thumb if self.original.isChecked() or self.result is None else self.result)

    def apply(self):
        if self.busy:return
        self.debounce.stop()
        self.busy=True
        self.generation+=1
        for widget in (self.list,self.scope,self.slider,self.apply_button,self.reset_button,self.detail):widget.setEnabled(False)
        self.commit_stack=update_effect_stack(self.stack,self.key,self.slider.value(),self.box)
        self.pending=('apply',self.generation,self.base,self.commit_stack,1,(0,0))
        self.note.setText('Berechnung in voller Auflösung …')
        self.poller.start()

    def poll(self):
        if self.closed:return
        if self.future is not None and self.future.done():
            future,self.future=self.future,None
            mode,generation=self.active
            try:
                result=future.result()
                if mode=='apply':
                    if self.doc.revision!=self.revision:raise ValueError('Das Bild wurde inzwischen verändert.')
                    self.doc.apply_stack(result,self.commit_stack)
                    self.owner.refresh()
                    self.accept()
                    return
                if generation==self.generation:
                    self.result=result
                    self.show_preview()
                    self.note.setText('Vorschau bereit. Neue Effekttypen ergänzen die Kombination, vorhandene werden aktualisiert.')
            except Exception as exc:
                self.busy=False
                for widget in (self.list,self.scope,self.slider,self.apply_button,self.reset_button,self.detail):widget.setEnabled(True)
                QMessageBox.warning(self,'Effekt fehlgeschlagen',str(exc))
        if self.future is None and self.pending:
            mode,generation,source,stack,scale,origin=self.pending
            self.pending=None
            self.active=(mode,generation)
            self.future=self.worker.submit(render_effect_stack,source,stack,scale,origin)
        if self.future is None and self.pending is None:self.poller.stop()

    def done(self,result):
        self.closed=True
        self.debounce.stop()
        self.poller.stop()
        self.worker.shutdown(wait=False,cancel_futures=True)
        super().done(result)


class Repainko(QMainWindow):
    def __init__(self,shared_editor=False):
        super().__init__()
        self.shared_editor=shared_editor;self.shared_bridge=None
        if not QFontDatabase.families():
            font_path=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/'segoeui.ttf'
            if font_path.exists():QFontDatabase.addApplicationFontFromData(font_path.read_bytes())
        self.doc=Document();self.gif_panel=None;self.paint_document=None
        self.auto_fit=True
        self.compact=False
        self.fg,self.bg='#172033','#ffffff'
        settings_path=os.environ.get('REPAINKO_SETTINGS_PATH')
        self.preferences=QSettings(settings_path,QSettings.Format.IniFormat) if settings_path else QSettings('Repainko','Repainko')
        self.wallpapers=WallpaperStore(Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))/'Addons')
        from redraw_addon import ReDrawkoStore
        self.redraw_store=ReDrawkoStore(Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))/'Addons')
        self.redrawko=None;self.redraw_active=False
        from redata_addon import ReDataStore
        self.redata_store=ReDataStore(Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))/'Addons');self.redatako=None;self.redata_active=False
        self.theme=self.preferences.value('appearance/theme','dark')
        if self.theme not in THEMES or (self.theme in PLUS_DESIGNS and not is_activated(self.preferences)):self.theme='dark'
        self.setMinimumSize(640,440)
        self.setStyleSheet(THEMES[self.theme][1])
        self.tool=QComboBox()
        self.tool.addItems(TOOLS)
        for i,name in enumerate(TOOLS):self.tool.setItemIcon(i,tool_icon(name))
        self.brush_sizes={'Pinsel':5,'Füller':14,'Bleistift':1,'Airbrush':20,'Radierer':30}
        self.previous_tool='Pinsel'
        self.brush_width=QSpinBox();self.brush_width.setRange(1,100);self.brush_width.setValue(5)
        self.brush_opacity=QSpinBox();self.brush_opacity.setRange(0,100);self.brush_opacity.setValue(100);self.brush_opacity.setSuffix(' %')
        self.censor_size=QSpinBox();self.censor_size.setRange(8,400);self.censor_size.setValue(80)
        self.strength=QSpinBox();self.strength.setRange(2,80);self.strength.setValue(18)
        self.censor_mode=QComboBox();self.censor_mode.addItems(CENSOR_MODES)
        self.censor_mode.setMaxVisibleItems(12)
        self.censor_mode.setStyleSheet('QComboBox {combobox-popup: 0;}')
        self.fill=QComboBox();self.fill.addItems(['Nur Kontur','Kontur + Füllung','Nur Füllung'])
        self.font=QFontComboBox();self.font.setMinimumWidth(100)
        self.font_size=QSpinBox();self.font_size.setRange(6,300);self.font_size.setValue(28)
        self.bold=QCheckBox('Fett')
        self.grid=QAction('Pixelraster ab 800 %',self);self.grid.setCheckable(True)
        self.scroll=DesignScrollArea();self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setStyleSheet('QScrollArea {background:#101720;border:0;}')
        self.canvas=Canvas(self);self.scroll.setWidget(self.canvas);self.workspace=QStackedWidget();self.workspace.addWidget(self.scroll);self.setCentralWidget(self.workspace);self.video_editor=None;self.video_active=False;self.browser=None;self.browser_active=False;self.help_center=None;self.help_active=False;self.help_previous=None;self.notebook=None;self.notebook_active=False;self.retexto=None;self.retexto_active=False;self.draw_together=None;self.draw_active=False
        self._drop_pending=False
        self.setAcceptDrops(True)
        for target in (self.canvas,self.scroll.viewport()):
            target.setAcceptDrops(True);target.installEventFilter(self)
        self.canvas.setToolTip('Bild aus Browser oder Explorer hierher ziehen und auf einer neuen Ebene platzieren.')
        self.build_actions()
        self.build_docks()
        toolbar=QToolBar('Schnellzugriff');toolbar.setMovable(False);self.addToolBar(toolbar)
        for action in (self.open_action,self.save_action,self.copy_save_action,self.undo_action,self.redo_action):toolbar.addAction(action)
        toolbar.setIconSize(QSize(24,24))
        for action in (self.undo_action,self.redo_action):
            toolbar.widgetForAction(action).setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        spacer=QWidget();spacer.setStyleSheet("background:transparent;");spacer.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Preferred);toolbar.addWidget(spacer)
        self.spotify=SpotifyWidget();self.spotify_action=toolbar.addWidget(self.spotify);self.spotify_action.setVisible(False)
        self.spotify.activeChanged.connect(self.spotify_action.setVisible)
        self.timesheet=TimesheetWidget(self.preferences,None,self)
        self.timesheet_action=toolbar.addWidget(self.timesheet);self.timesheet_action.setVisible(False)
        self.saldo_action.toggled.connect(self.toggle_timesheet)
        self.spotify_monitor=SpotifyMonitor(self);self.spotify_monitor.changed.connect(self.spotify.receive)
        self.spotify.commandRequested.connect(self.spotify_monitor.command)
        self.spotify_monitor.commandFinished.connect(self.spotify.command_finished)
        QApplication.instance().aboutToQuit.connect(self.spotify_monitor.stop)
        if not shared_editor and os.environ.get('QT_QPA_PLATFORM')!='offscreen':QTimer.singleShot(0,self.spotify_monitor.start)
        space=QWidget();space.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Preferred);space.setStyleSheet('background:transparent;');toolbar.addWidget(space)
        self.logo=QLabel();self.logo.setFixedSize(64,64);self.logo.setStyleSheet('background:transparent;')
        toolbar.addWidget(self.logo);self.refresh_branding()
        self.addToolBarBreak()
        drawing_bar=QToolBar('Zeichnen');drawing_bar.setMovable(False);self.addToolBar(drawing_bar)
        drawing_bar.addWidget(self.tool)
        drawing_bar.addAction(self.effects_action)
        drawing_bar.addAction(self.ai_action)
        drawing_bar.addAction(self.settings.toggleViewAction())
        drawing_bar.addAction(self.tools_dock.toggleViewAction())
        drawing_bar.addAction(self.layers_dock.toggleViewAction())
        self.settings.toggleViewAction().setText('Optionen')
        self.zoom_label=QLabel('100 %')
        self.statusBar().addPermanentWidget(self.zoom_label)
        for label,action in [('−',lambda:self.set_zoom(self.canvas.zoom/1.25)),('+',lambda:self.set_zoom(self.canvas.zoom*1.25)),('Einpassen',self.fit)]:
            button=QPushButton(label);button.clicked.connect(action);self.statusBar().addPermanentWidget(button)
        self.grid.toggled.connect(self.canvas.update)
        self.tool.currentTextChanged.connect(self.change_tool)
        available=self.screen().availableGeometry()
        self.resize(min(1400,available.width()-40),min(920,available.height()-70))
        if available.width()<1150:self.settings.hide();self.tools_dock.hide();self.layers_dock.hide()
        QTimer.singleShot(0,self.fit)
        self.refresh()
        self.set_theme(self.theme,False)
        self.desktop_job=None
        if shared_editor:
            self.mode_menu.menuAction().setVisible(False);self.saldo_action.setVisible(False)
            self.desktop_icon_action.setVisible(False);self.help_action.setVisible(False)
            for action in self.findChildren(QAction):
                if action.text() in ('DrawTogether …','Beenden'):action.setVisible(False);action.setEnabled(False)
            return
        # Check connectivity at startup without starting Chromium or opening a page.
        try:
            from browser_mode import Browser
            self.browser=Browser(self.workspace);self.browser.returnRequested.connect(self.leave_video_editor);self.workspace.addWidget(self.browser)
            self.browser.onlineChanged.connect(lambda online:self.browser_action.setText('ReBrowko · '+('Online' if online else 'Offline')))
        except Exception as exc:self.statusBar().showMessage('ReBrowko konnte nicht vorbereitet werden: '+str(exc),12000)
        self.timesheet.browser=self.browser
        if self.preferences.value('timesheet/enabled',False,type=bool):
            self.saldo_action.blockSignals(True);self.saldo_action.setChecked(True);self.saldo_action.blockSignals(False)
            self.timesheet_action.setVisible(True);self.timesheet.set_enabled(True)
            if os.environ.get('QT_QPA_PLATFORM')!='offscreen':QTimer.singleShot(0,lambda:self.timesheet.open_account(False))
        if self.plus_active and packaged_runtime(Path(__file__).parent):
            QTimer.singleShot(1000,self.auto_desktop_icon)

    def action(self,menu,text,slot,shortcut=None):
        a=QAction(text,self)
        if shortcut:a.setShortcut(QKeySequence(shortcut))
        a.triggered.connect(lambda checked=False:slot())
        menu.addAction(a)
        return a

    def toggle_timesheet(self,enabled):
        self.timesheet_action.setVisible(enabled);self.timesheet.set_enabled(enabled)
        if enabled:self.timesheet.open_account()

    def build_actions(self):
        file=self.menuBar().addMenu('Datei')
        self.action(file,'Neu',self.new,'Ctrl+N')
        self.open_action=self.action(file,'Öffnen',self.open,'Ctrl+O')
        self.save_action=self.action(file,'Speichern',self.save,'Ctrl+S')
        self.transparent_save=QAction('Mit transparentem Blatthintergrund speichern (PNG / WebP / TIFF)',self);self.transparent_save.setCheckable(True);file.addAction(self.transparent_save)
        self.action(file,'Speichern unter …',lambda:self.save(True),'Ctrl+Shift+S')
        self.action(file,'Projekt mit Ebenen speichern …',self.save_project_dialog)
        self.copy_save_action=self.action(file,'Als Kopie speichern',self.save_copy,'Ctrl+Alt+S')
        self.action(file,'Bild einfügen …',self.import_image)
        self.action(file,'Druckdatei (PDF) …',self.pdf)
        file.addSeparator()
        self.plus_action=self.action(file,'Repaintko Plus aktivieren …',self.activate_plus)
        self.desktop_icon_action=self.action(file,'Desktop-Symbol aktualisieren',lambda:self.update_desktop_icon(True))
        file.addSeparator()
        self.action(file,'DrawTogether …',self.open_draw_together)
        self.action(file,'Beenden',self.close)
        edit=self.menuBar().addMenu('Bearbeiten')
        self.undo_action=self.action(edit,'Zurück',lambda:self.edit(self.doc.undo),'Ctrl+Z')
        self.redo_action=self.action(edit,'Vor',lambda:self.edit(self.doc.redo),'Ctrl+Y')
        self.action(edit,'Kopieren',self.copy_image,'Ctrl+C')
        self.action(edit,'Ausschneiden',self.cut,'Ctrl+X')
        self.action(edit,'Einfügen',self.paste_image,'Ctrl+V')
        self.action(edit,'Alles auswählen',self.select_all,'Ctrl+A')
        self.action(edit,'Auswahl löschen',lambda:self.edit(lambda:self.doc.delete(self.bg)),'Delete')
        image=self.menuBar().addMenu('Bild')
        self.action(image,'Blattfarbe ändern …',self.choose_paper)
        self.action(image,'Größe ändern …',lambda:self.dimensions('Größe ändern',lambda size:self.doc.resize(size)))
        self.action(image,'Leinwandgröße …',lambda:self.dimensions('Leinwandgröße',lambda size:self.doc.resize(size,True,self.bg)))
        self.action(image,'Zuschneiden',lambda:self.edit(self.doc.crop))
        for label,key in [('90° rechts','right'),('90° links','left'),('Horizontal spiegeln','mirror'),('Vertikal spiegeln','flip'),('Farben umkehren','invert'),('Graustufen','gray')]:
            self.action(image,label,lambda key=key:self.edit(lambda:self.doc.transform(key)))
        self.action(image,'Aktive Ebene leeren',self.clear)
        fx=self.menuBar().addMenu('Effekte')
        self.effects_action=self.action(fx,'Fotoeffekte',self.effects)
        self.ai_action=self.action(fx,'KI entfernen (Plus)',self.remove_objects)
        self.ai_action.setToolTip('Repaintko Plus: Personen/Objekte markieren und lokal entfernen oder transparent machen.')
        censor_menu=fx.addMenu('Zensurpinsel')
        for mode in CENSOR_MODES[:7]:self.action(censor_menu,mode,lambda mode=mode:self.activate_censor(mode))
        for title,modes in [('Richtung & Bewegung',CENSOR_MODES[7:12]),
                            ('Fläche & Linse',CENSOR_MODES[12:15]),
                            ('Zoom & Glas',CENSOR_MODES[15:21]),
                            ('Doppelbild & Licht',CENSOR_MODES[21:])]:
            group=censor_menu.addMenu(title)
            for mode in modes:self.action(group,mode,lambda mode=mode:self.activate_censor(mode))
        mode=self.menuBar().addMenu('Modus');self.mode_menu=mode
        self.return_action=self.action(mode,'Zurück zum Bild / GIF',self.leave_video_editor);self.return_action.setVisible(False)
        self.gif_action=QAction('GIF-Editor',self);self.gif_action.setCheckable(True);self.gif_action.triggered.connect(self.toggle_gif);mode.addAction(self.gif_action)
        self.video_action=self.action(mode,'Video-Editor (Plus)',self.open_video_editor)
        self.browser_action=self.action(mode,'ReBrowko · Internet',self.open_browser)
        self.notebook_action=self.action(mode,'Notizbuch',self.open_notebook)
        self.retexto_action=self.action(mode,'ReTexto · Texteditor',self.open_retexto)
        self.draw_action=self.action(mode,'DrawTogether',self.open_draw_together)
        self.redraw_action=self.action(mode,'ReDrawko · Diagramme',self.open_redrawko)
        self.redraw_action.setVisible(self.redraw_store.installed())
        self.redata_action=self.action(mode,'ReDataKo · Datenbanken',self.open_redatako);self.redata_action.setVisible(self.redata_store.installed())
        self.view_menu=self.menuBar().addMenu('Ansicht')
        self.saldo_action=QAction('Saldo berechnen',self);self.saldo_action.setCheckable(True);self.view_menu.addAction(self.saldo_action)
        self.action(self.view_menu,'An Fenster anpassen',self.fit)
        self.action(self.view_menu,'100 %',lambda:self.set_zoom(1))
        self.view_menu.addAction(self.grid)
        theme_menu=self.view_menu.addMenu('Design')
        normal_menu=theme_menu.addMenu('Standard-Designs')
        plus_menu=theme_menu.addMenu('Plus-Designs')
        self.theme_actions={};self.theme_group=QActionGroup(self);self.theme_group.setExclusive(True)
        for value,(title,_,_) in THEMES.items():
            action=self.action(plus_menu if value in PLUS_DESIGNS else normal_menu,title,lambda value=value:self.set_theme(value))
            action.setCheckable(True);self.theme_group.addAction(action);self.theme_actions[value]=action
        self.help_action=self.action(self.menuBar(),'Hilfe',self.open_help,'F1')
        self.addons_action=self.action(self.menuBar(),'Add-ons',self.open_addons)

    def open_addons(self):
        from addon_ui import AddonHub
        AddonHub(self).exec()

    def open_redrawko(self):
        if self.redraw_active or not self.redraw_store.installed():return
        if self.video_active and self.video_editor.busy:return
        if self.notebook_active and not self.notebook.flush():return
        self.leave_video_editor()
        try:
            if self.redrawko is None:
                from redraw_ui import ReDrawko
                recovery=Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))/'ReDrawko'/'recovery.redrawko'
                self.redrawko=ReDrawko(self.workspace,self.preferences,self.redraw_store,recovery)
                self.redrawko.returnRequested.connect(self.leave_video_editor);self.workspace.addWidget(self.redrawko)
            self.enter_workspace(self.redrawko,'ReDrawko · Repaintko')
        except Exception as exc:QMessageBox.warning(self,'ReDrawko',str(exc))

    def open_redatako(self):
        if self.redata_active or not self.redata_store.installed():return
        if self.video_active and self.video_editor.busy:return
        if self.notebook_active and not self.notebook.flush():return
        self.leave_video_editor()
        try:
            if self.redatako is None:
                import redata_ui
                self.redatako=redata_ui.ReDataKo(self.workspace,self.preferences);self.redatako.returnRequested.connect(self.leave_video_editor);self.workspace.addWidget(self.redatako)
            self.enter_workspace(self.redatako,'ReDataKo · Repaintko')
        except Exception as exc:QMessageBox.warning(self,'ReDataKo',str(exc))

    def refresh_wallpaper(self):
        from wallpaper_modes import selected_modes,apply_background
        key=str(self.preferences.value('wallpaper/selected','color_mint'))
        enabled=self.preferences.value('wallpaper/enabled',False,type=bool)
        path=self.wallpapers.image(key,is_activated(self.preferences)) if enabled else None
        opacity=self.preferences.value('wallpaper/opacity',100,type=int);modes=selected_modes(self.preferences)
        mode='draw' if self.shared_editor else ('gif' if self.gif_panel is not None else 'paint')
        self.scroll.set_wallpaper(path if mode in modes else None,opacity)
        for mode,attribute in [('notebook','notebook'),('retexto','retexto'),('video','video_editor'),('browser','browser'),('help','help_center'),('redrawko','redrawko'),('redatako','redatako')]:
            widget=getattr(self,attribute,None);apply_background(widget,path if mode in modes else None,opacity)
            if mode=='redrawko' and widget is not None:widget.set_wallpaper(path if mode in modes else None,opacity)
        draw=getattr(self,'draw_together',None)
        if draw is not None:
            draw.editor.scroll.set_wallpaper(path if 'draw' in modes else None,opacity)

    def dock(self,title,content,side):
        d=QDockWidget(title,self)
        d.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea|Qt.DockWidgetArea.RightDockWidgetArea)
        d.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable|QDockWidget.DockWidgetFeature.DockWidgetMovable)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(content)
        d.setWidget(scroll);d.setMinimumWidth(150)
        self.addDockWidget(side,d);self.view_menu.addAction(d.toggleViewAction())
        return d

    def refresh_branding(self):
        self.plus_active=is_activated(self.preferences)
        icon=brand_icon(self.plus_active)
        self.logo.setPixmap(icon.pixmap(64,64));self.setWindowIcon(icon)
        self.logo.setToolTip('Repaintko'+(' Plus' if self.plus_active else '')+' 13.1.0')
        self.logo.setAccessibleName('Repaintko Plus' if self.plus_active else 'Repaintko')
        self.plus_action.setText('Repaintko Plus ist aktiviert' if self.plus_active else 'Repaintko Plus aktivieren …')
        self.plus_action.setEnabled(not self.plus_active)
        self.ai_action.setEnabled(self.plus_active)
        self.video_action.setEnabled(self.plus_active)
        self.refresh_wallpaper()
        for key,action in self.theme_actions.items():
            action.setEnabled(key not in PLUS_DESIGNS or self.plus_active)
        if self.theme in PLUS_DESIGNS and not self.plus_active:self.set_theme('dark',False)

    def activate_plus(self):
        if self.plus_active:return
        key,accepted=QInputDialog.getText(self,'Repaintko Plus aktivieren','Repaintko Plus Access Key:',QLineEdit.EchoMode.Password)
        if not accepted:return
        try:
            if not activate(self.preferences,key):
                QMessageBox.warning(self,'Ungültiger Access Key','Der eingegebene Schlüssel ist nicht gültig. Bitte Groß-/Kleinschreibung und Bindestriche prüfen.');return
        except OSError as exc:
            QMessageBox.warning(self,'Aktivierung fehlgeschlagen',str(exc));return
        self.refresh_branding()
        QMessageBox.information(self,'Repaintko Plus','Repaintko Plus ist aktiviert. Dein blaues Plus-Logo bleibt auch nach einem Neustart erhalten.')
        self.update_desktop_icon(True)

    def auto_desktop_icon(self):
        # Startup must never request administrator permission, including after
        # updates or when settings could not be persisted. Explicit actions can.
        self.update_desktop_icon(False)

    def update_desktop_icon(self,allow_elevation=False):
        if self.desktop_job is not None:return
        app_dir=Path(__file__).parent
        if not packaged_runtime(app_dir):
            self.statusBar().showMessage('Desktop-Symbole werden in der installierten App aktualisiert.',7000);return
        self.desktop_icon_action.setEnabled(False)
        self.statusBar().showMessage('Desktop-Symbol wird aktualisiert.'+(' Für den öffentlichen Desktop kann Windows Administratorrechte anfordern.' if allow_elevation else ''))
        pool=ThreadPoolExecutor(max_workers=1)
        future=pool.submit(sync_desktop_icon,app_dir,self.plus_active,allow_elevation)
        timer=QTimer(self);self.desktop_job=(pool,future,timer)
        def finished():
            if not future.done():return
            timer.stop();timer.deleteLater();self.desktop_job=None;pool.shutdown(wait=False)
            self.desktop_icon_action.setEnabled(True)
            try:result=future.result()
            except Exception:result={'status':'error'}
            messages={
                'updated':'Desktop-Symbol aktualisiert.', 'current':'Das Desktop-Symbol ist bereits aktuell.',
                'missing':'Keine Desktop-Verknüpfung für diese Installation gefunden. Bei Bedarf den Installer reparieren lassen.',
                'cancelled':'Symboländerung abgebrochen. Plus bleibt aktiv. Erneut versuchen unter Datei → Desktop-Symbol aktualisieren.',
                'denied':'Für das öffentliche Desktop-Symbol sind Administratorrechte nötig. Erneut versuchen unter Datei → Desktop-Symbol aktualisieren.',
                'error':'Desktop-Symbol konnte nicht aktualisiert werden. Erneut versuchen unter Datei → Desktop-Symbol aktualisieren.'}
            self.statusBar().showMessage(messages.get(result['status'],messages['error']),15000)
        timer.timeout.connect(finished);timer.start(100)

    def set_theme(self,theme,persist=True):
        if theme in PLUS_DESIGNS and not is_activated(self.preferences):return False
        if theme not in THEMES:theme='dark'
        self.theme=theme
        self.setStyleSheet(THEMES[theme][1])
        for action,mirror in ((self.undo_action,False),(self.redo_action,True)):
            pixmap=QPixmap(64,64);pixmap.fill(Qt.GlobalColor.transparent)
            painter=QPainter(pixmap);painter.setRenderHint(QPainter.RenderHint.Antialiasing);painter.scale(2,2)
            if mirror:painter.translate(32,0);painter.scale(-1,1)
            painter.setPen(QPen(QColor('#172033' if theme=='light' else '#edf3fa'),2.5,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
            path=QPainterPath();path.moveTo(18,25);path.cubicTo(29,25,29,10,17,10);path.lineTo(4,10);path.moveTo(10,4);path.lineTo(4,10);path.lineTo(10,16)
            painter.drawPath(path);painter.end();action.setIcon(QIcon(pixmap));action.setToolTip(action.text()+' ('+action.shortcut().toString()+')')
        self.scroll.setStyleSheet('QScrollArea {background:'+THEMES[theme][2]+';border:0;}')
        self.scroll.set_design(theme,THEMES[theme][2])
        self.refresh_wallpaper()
        self.theme_actions[theme].setChecked(True)
        if persist:
            self.preferences.setValue('appearance/theme',theme);self.preferences.sync()
        self.canvas.update()

    def build_docks(self):
        tools=QWidget();layout=QGridLayout(tools);layout.setSpacing(5)
        self.tool_buttons={}
        for i,tool in enumerate(TOOLS):
            b=QPushButton();b.setIcon(tool_icon(tool));b.setIconSize(QSize(30,30));b.setFixedSize(48,44);b.setToolTip(tool);b.setAccessibleName(tool);b.setCheckable(True);b.setChecked(tool=='Pinsel')
            b.clicked.connect(lambda checked=False,t=tool:self.tool.setCurrentText(t))
            layout.addWidget(b,i//2,i%2);self.tool_buttons[tool]=b
        layout.setRowStretch((len(TOOLS)+1)//2,1)
        self.tools_dock=self.dock('Werkzeuge',tools,Qt.DockWidgetArea.LeftDockWidgetArea)
        controls=QWidget();form=QFormLayout(controls)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        paper=QPushButton('Blattfarbe ändern …');paper.clicked.connect(self.choose_paper);form.addRow(paper)
        opacity=QPushButton('Blattdeckkraft …');opacity.clicked.connect(self.choose_paper_opacity);form.addRow(opacity)
        form.addRow('Strichstärke',self.brush_width);form.addRow('Formstil',self.fill)
        form.addRow('Stift-Deckkraft',self.brush_opacity)
        label=QLabel('ZENSURPINSEL');label.setObjectName('muted');form.addRow(label)
        form.addRow('Modus',self.censor_mode);form.addRow('Größe',self.censor_size);form.addRow('Stärke',self.strength)
        activate=QPushButton('Zensurpinsel aktivieren');activate.setObjectName('primary');activate.clicked.connect(lambda:self.tool.setCurrentText('Zensur'));form.addRow(activate)
        self.fg_button=QPushButton('Farbe 1');self.bg_button=QPushButton('Farbe 2')
        self.fg_button.clicked.connect(lambda:self.choose_color(False));self.bg_button.clicked.connect(lambda:self.choose_color(True))
        form.addRow(self.fg_button,self.bg_button)
        swap=QPushButton('Farben tauschen');swap.clicked.connect(self.swap);form.addRow(swap)
        palette=QWidget();grid=QGridLayout(palette);grid.setContentsMargins(0,0,0,0);grid.setSpacing(3)
        for i,color in enumerate(['#172033','#ffffff','#9aaabd','#ef4444','#f97316','#facc15','#22c55e','#63e6be','#06b6d4','#3b82f6','#8b5cf6','#ec4899']):
            button=QPushButton();button.setFixedSize(24,24);button.setStyleSheet('background:'+color+';border-radius:12px;')
            button.clicked.connect(lambda checked=False,c=color:self.set_color(c,False));grid.addWidget(button,i//6,i%6)
        form.addRow(palette)
        form.addRow('Schrift',self.font);form.addRow('Schriftgröße',self.font_size);form.addRow(self.bold)
        self.settings=self.dock('Einstellungen',controls,Qt.DockWidgetArea.RightDockWidgetArea)
        self.build_layers_dock()
        self.set_color(self.fg,False);self.set_color(self.bg,True)

    def build_layers_dock(self):
        panel=QWidget();layout=QVBoxLayout(panel)
        self.layer_list=QListWidget();self.layer_list.setMinimumHeight(100)
        layout.addWidget(self.layer_list)
        self.layer_opacity=QSpinBox();self.layer_opacity.setRange(0,100);self.layer_opacity.setSuffix(' %');self.layer_opacity.setKeyboardTracking(False)
        layout.addWidget(QLabel('Ebenen-Deckkraft'));layout.addWidget(self.layer_opacity)
        buttons=QGridLayout();layout.addLayout(buttons)
        for i,(title,callback) in enumerate([
            ('Neu',lambda:self.doc.add_layer()),('Duplizieren',lambda:self.doc.duplicate_layer()),
            ('Nach oben',lambda:self.doc.move_layer(1)),('Nach unten',lambda:self.doc.move_layer(-1)),
            ('Umbenennen',self.rename_layer),('Löschen',lambda:self.doc.remove_layer()),
            ('Nach unten vereinen',lambda:self.doc.merge_down())]):
            button=QPushButton(title);button.clicked.connect(lambda checked=False,callback=callback:self.layer_edit(callback))
            buttons.addWidget(button,i//2,i%2)
        note=QLabel('Oben liegt vorne. Häkchen = sichtbar.\nAls .repaintko speichern, um Ebenen zu behalten.');note.setWordWrap(True);layout.addWidget(note)
        self.layer_list.currentRowChanged.connect(self.select_layer)
        self.layer_list.itemChanged.connect(self.layer_visibility)
        self.layer_opacity.valueChanged.connect(lambda value:self.layer_edit(lambda:self.doc.set_layer('opacity',value)))
        self.layers_dock=self.dock('Ebenen',panel,Qt.DockWidgetArea.RightDockWidgetArea)
        self.tabifyDockWidget(self.settings,self.layers_dock);self.settings.raise_()

    def layer_edit(self,callback):
        if self.canvas.start is not None:return
        self.doc.selection=None
        self.edit(callback)

    def rename_layer(self):
        name,ok=QInputDialog.getText(self,'Ebene umbenennen','Name:',text=self.doc.layers[self.doc.active]['name'])
        if ok:self.doc.set_layer('name',name)

    def select_layer(self,row):
        if row<0 or self.canvas.start is not None:return
        self.doc.active=len(self.doc.layers)-1-row;self.doc.selection=None;self.refresh()

    def layer_visibility(self,item):
        index=item.data(Qt.ItemDataRole.UserRole)
        self.layer_edit(lambda:self.doc.set_layer('visible',item.checkState()==Qt.CheckState.Checked,index))

    def refresh_layers(self):
        if not hasattr(self,'layer_list'):return
        self.layer_list.blockSignals(True);self.layer_opacity.blockSignals(True)
        self.layer_list.clear()
        for index in reversed(range(len(self.doc.layers))):
            entry=self.doc.layers[index];item=QListWidgetItem(entry['name'])
            item.setData(Qt.ItemDataRole.UserRole,index)
            item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if entry['visible'] else Qt.CheckState.Unchecked)
            self.layer_list.addItem(item)
        self.layer_list.setCurrentRow(len(self.doc.layers)-1-self.doc.active)
        self.layer_opacity.setValue(self.doc.layers[self.doc.active]['opacity'])
        self.layer_list.blockSignals(False);self.layer_opacity.blockSignals(False)

    def change_tool(self,tool):
        self.brush_sizes[self.previous_tool]=self.brush_width.value()
        self.brush_width.setValue(self.brush_sizes.get(tool,5))
        self.previous_tool=tool
        self.canvas.start=self.canvas.last=self.canvas.current=None
        self.canvas.polygon=[]
        self.doc.finish_stroke()
        self.doc.selection=None
        for name,b in self.tool_buttons.items():b.setChecked(name==tool)
        self.canvas.update()

    def activate_censor(self,mode):
        self.censor_mode.setCurrentText(mode);self.tool.setCurrentText('Zensur');self.settings.show()

    def set_color(self,color,background):
        if background:self.bg=color
        else:self.fg=color
        if hasattr(self,'fg_button'):
            for button,value in [(self.fg_button,self.fg),(self.bg_button,self.bg)]:
                button.setStyleSheet(f'background:{value};color:{"black" if QColor(value).lightness()>140 else "white"};')

    def choose_paper_opacity(self):
        value,ok=QInputDialog.getInt(self,'Blattdeckkraft','Deckkraft des Blatthintergrunds (0–100 %):',self.doc.paper_opacity,0,100)
        if ok:self.edit(lambda:self.doc.set_paper_opacity(value))

    def choose_paper(self):
        picker=ColorPicker(self.doc.paper_color,self)
        if picker.exec()==QDialog.DialogCode.Accepted:self.edit(lambda:self.doc.set_paper_color(picker.color.name()))

    def choose_color(self,background):
        picker=ColorPicker(self.bg if background else self.fg,self)
        if picker.exec()==QDialog.DialogCode.Accepted:self.set_color(picker.color.name(),background)

    def swap(self):
        self.fg,self.bg=self.bg,self.fg;self.set_color(self.fg,False)

    def refresh(self,rebuild=True):
        self.canvas.sync(rebuild)
        self.refresh_layers()
        name=Path(self.doc.path).name if self.doc.path else 'Unbenannt'
        if self.gif_panel:name=f'GIF · Frame {self.gif_panel.animation.index+1}/{len(self.gif_panel.animation.frames)}'
        self.setWindowTitle(f'{"* " if (self.gif_panel.animation.dirty if self.gif_panel else self.doc.dirty) else ""}{name} · Repaintko')
        self.statusBar().showMessage(f'{self.doc.image.width} × {self.doc.image.height} px  |  {len(self.doc.layers)} Ebenen  |  {self.doc.layers[self.doc.active]["name"]}')
        if hasattr(self,'undo_action'):
            self.undo_action.setEnabled(bool(self.doc.history));self.redo_action.setEnabled(bool(self.doc.future))
        if self.shared_bridge:self.shared_bridge.changed()

    def edit(self,callback):
        try:callback();self.refresh()
        except Exception as exc:QMessageBox.warning(self,'Repaintko',str(exc))

    def open_video_editor(self):
        if self.draw_active:self.leave_video_editor()
        if self.retexto_active:self.leave_video_editor()
        if self.notebook_active:
            if not self.notebook.flush():return
            self.leave_video_editor()
        if self.video_active:return
        if self.browser_active or self.help_active:self.leave_video_editor()
        if not is_activated(self.preferences):
            QMessageBox.information(self,'Repaintko Plus','Der Video-Editor ist für Repaintko Plus verfügbar.');return
        try:
            if self.video_editor is None:
                from video_editor import VideoEditor
                self.video_editor=VideoEditor(self.preferences,self.workspace)
                self.video_editor.returnRequested.connect(self.leave_video_editor)
                self.workspace.addWidget(self.video_editor)
            self.enter_workspace(self.video_editor,'Repaintko Plus · Video-Editor')
        except Exception as exc:QMessageBox.warning(self,'Video-Editor',str(exc))

    def open_browser(self):
        if self.draw_active:self.leave_video_editor()
        if self.retexto_active:self.leave_video_editor()
        if self.notebook_active:
            if not self.notebook.flush():return
            self.leave_video_editor()
        if self.browser_active:return
        if self.help_active:self.leave_video_editor()
        if self.video_active:
            if self.video_editor.busy:return
            self.leave_video_editor()
        try:
            if self.browser is None:
                from browser_mode import Browser
                self.browser=Browser(self.workspace);self.browser.returnRequested.connect(self.leave_video_editor);self.workspace.addWidget(self.browser)
            self.enter_workspace(self.browser,'ReBrowko · Repaintko')
        except Exception as exc:QMessageBox.warning(self,'ReBrowko',str(exc))

    def open_help(self):
        from_draw=self.draw_active
        if self.draw_active:self.leave_video_editor()
        from_retexto=self.retexto_active
        if self.retexto_active:self.leave_video_editor()
        from_notebook=self.notebook_active
        if self.notebook_active:
            if not self.notebook.flush():return
            self.leave_video_editor()
        if self.help_active:return
        if self.video_active and self.video_editor.busy:return
        self.help_previous='redatako' if self.redata_active else 'redrawko' if self.redraw_active else 'draw' if from_draw else 'retexto' if from_retexto else 'notebook' if from_notebook else ('video' if self.video_active else ('browser' if self.browser_active else 'paint'))
        if self.video_active or self.browser_active:self.leave_video_editor()
        if self.help_center is None:
            from help_center import HelpCenter
            self.help_center=HelpCenter(self.workspace);self.help_center.returnRequested.connect(self.return_from_help);self.workspace.addWidget(self.help_center)
        self.enter_workspace(self.help_center,'Repaintko · Hilfezentrum')

    def return_from_help(self):
        previous=self.help_previous;self.leave_video_editor()
        if previous=='video':self.open_video_editor()
        elif previous=='browser':self.open_browser()
        elif previous=='notebook':self.open_notebook()
        elif previous=='retexto':self.open_retexto()
        elif previous=='draw':self.open_draw_together()
        elif previous=='redrawko':self.open_redrawko()
        elif previous=='redatako':self.open_redatako()

    def open_notebook(self):
        if self.draw_active:self.leave_video_editor()
        if self.retexto_active:self.leave_video_editor()
        if self.notebook_active:return
        if self.video_active and self.video_editor.busy:return
        if self.video_active or self.browser_active or self.help_active:self.leave_video_editor()
        try:
            if self.notebook is None:
                from notebook import Notebook
                self.notebook=Notebook(self.workspace);self.notebook.returnRequested.connect(self.leave_video_editor);self.workspace.addWidget(self.notebook)
            self.enter_workspace(self.notebook,'Repaintko · Notizbuch')
        except Exception as exc:QMessageBox.warning(self,'Notizbuch',str(exc))

    def open_retexto(self):
        if self.draw_active:self.leave_video_editor()
        if self.retexto_active:return
        if self.video_active and self.video_editor.busy:return
        if self.notebook_active and not self.notebook.flush():return
        self.leave_video_editor()
        try:
            if self.retexto is None:
                from retexto import ReTexto
                self.retexto=ReTexto(self.workspace);self.retexto.returnRequested.connect(self.leave_video_editor);self.workspace.addWidget(self.retexto)
            self.enter_workspace(self.retexto,'ReTexto · Repaintko')
        except Exception as exc:QMessageBox.warning(self,'ReTexto',str(exc))

    def open_draw_together(self):
        if self.draw_active:return
        if self.video_active and self.video_editor.busy:return
        if self.notebook_active and not self.notebook.flush():return
        self.leave_video_editor()
        try:
            if self.draw_together is None:
                from draw_together import DrawTogether
                self.draw_together=DrawTogether(self.workspace,source=lambda:self.doc)
                self.draw_together.returnRequested.connect(self.leave_video_editor)
                self.workspace.addWidget(self.draw_together)
            self.enter_workspace(self.draw_together,'DrawTogether · Repaintko')
        except Exception as exc:QMessageBox.warning(self,'DrawTogether',str(exc))

    def enter_workspace(self,widget,title):
        if self.redraw_active or self.redata_active:self.leave_video_editor()
        self._paint_title=self.windowTitle()
        self._paint_panels=[(w,not w.isHidden()) for w in self.findChildren(QDockWidget)+self.findChildren(QToolBar) if w not in widget.findChildren(QDockWidget)+widget.findChildren(QToolBar)]
        self._paint_menus=[(a,a.isVisible()) for a in self.menuBar().actions() if a not in (self.mode_menu.menuAction(),self.help_action,self.addons_action)]
        self._paint_actions=[(a,a.isEnabled()) for a in self.findChildren(QAction) if a not in widget.findChildren(QAction) and a not in self.mode_menu.actions() and a not in (self.mode_menu.menuAction(),self.help_action,self.addons_action)]
        for a,_ in self._paint_actions:a.setEnabled(False)
        for a,_ in self._paint_menus:a.setVisible(False)
        for w,_ in self._paint_panels:w.hide()
        self._paint_status=not self.statusBar().isHidden();self.statusBar().hide()
        self.gif_action.setEnabled(False);self.return_action.setVisible(True)
        self.video_active=widget is self.video_editor;self.browser_active=widget is self.browser;self.help_active=widget is self.help_center;self.notebook_active=widget is self.notebook;self.retexto_active=widget is self.retexto;self.draw_active=widget is self.draw_together;self.setAcceptDrops(False)
        self.workspace.setCurrentWidget(widget);self.setWindowTitle(title);widget.setFocus()
        self.redraw_active=widget is self.redrawko
        self.redata_active=widget is self.redatako
        self.refresh_wallpaper()
        self.mode_menu.menuAction().setVisible(not self.draw_active)

    def leave_video_editor(self):
        if not (self.video_active or self.browser_active or self.help_active or self.notebook_active or self.retexto_active or self.draw_active or self.redraw_active or self.redata_active):return
        if self.notebook_active and not self.notebook.flush():return
        if self.video_active:
            if self.video_editor.busy:return
            self.video_editor.player.pause()
        self.workspace.setCurrentWidget(self.scroll);self.video_active=False;self.browser_active=False;self.help_active=False;self.notebook_active=False;self.retexto_active=False;self.draw_active=False;self.setAcceptDrops(True)
        self.mode_menu.menuAction().setVisible(True)
        self.redraw_active=False
        self.redata_active=False
        for a,enabled in self._paint_actions:a.setEnabled(enabled)
        for a,visible in self._paint_menus:a.setVisible(visible)
        for w,visible in self._paint_panels:w.setVisible(visible)
        self.statusBar().setVisible(self._paint_status)
        self.gif_action.setEnabled(True);self.return_action.setVisible(False)
        self.setWindowTitle(self._paint_title);self.canvas.setFocus()

    def toggle_gif(self,enabled):
        if enabled and self.gif_panel is None:
            self.paint_document=self.doc
            self.gif_panel=GifPanel(self,self.doc);self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea,self.gif_panel)
            self.doc=self.gif_panel.animation.frames[0];self.gif_panel.show();self.refresh();self.fit()
        elif not enabled and self.gif_panel is not None:
            if not self.confirm():self.gif_action.setChecked(True);return False
            panel=self.gif_panel;self.gif_panel=None;self.removeDockWidget(panel);panel.deleteLater()
            self.doc=self.paint_document;self.paint_document=None;self.refresh();self.fit()
        self.gif_action.setChecked(enabled);self.refresh_wallpaper();return True

    def confirm(self):
        dirty=self.gif_panel.animation.dirty if self.gif_panel else self.doc.dirty
        if not dirty:return True
        answer=QMessageBox.question(self,'Änderungen speichern?','Möchtest du deine Änderungen speichern?',
                                   QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel)
        return self.save() if answer==QMessageBox.StandardButton.Save else answer==QMessageBox.StandardButton.Discard

    def new(self):
        if self.gif_panel and not self.toggle_gif(False):return
        if self.confirm():self.dimensions('Neues Bild',lambda size:self.doc.__init__(size))

    def open(self):
        if self.gif_panel and not self.toggle_gif(False):return
        if not self.confirm():return
        path,_=QFileDialog.getOpenFileName(self,'Bild, PDF oder Projekt öffnen','','Bilder, PDF und Projekte (*.pdf *.repaintko *.repainko *.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff *.gif)')
        if path:self.open_path(path)

    def open_path(self,path):
        if self.gif_panel and not self.toggle_gif(False):return
        if Path(path).suffix.lower()=='.pdf':self.open_pdf(path)
        else:self.edit(lambda:self.doc.open(path));self.fit()

    def drop_source(self,event):
        if self._drop_pending or self.canvas.start is not None or QApplication.activeModalWidget():return None
        if not event.possibleActions() & Qt.DropAction.CopyAction:return None
        mime=event.mimeData();urls=mime.urls()
        local=[url for url in urls if url.isLocalFile()]
        if local:
            if len(urls)!=1:return None
            path=Path(local[0].toLocalFile())
            if path.suffix.lower() in DROP_SUFFIXES and path.is_file():return ('file',str(path))
            return None
        try:return browser_source(mime)
        except (ValueError,TypeError):return None

    def dragEnterEvent(self,event):
        if self.drop_source(event):
            event.setDropAction(Qt.DropAction.CopyAction);event.accept()
            self.statusBar().showMessage('Loslassen: Bild auf einer neuen Ebene platzieren. PDF und Projekte werden geöffnet.')
        else:
            event.ignore();self.statusBar().showMessage('Bitte ein Bild aus Browser oder Explorer, eine PDF oder ein Projekt ziehen.',4000)

    def dragMoveEvent(self,event):self.dragEnterEvent(event)

    def dragLeaveEvent(self,event):
        self.statusBar().clearMessage();event.accept()

    @staticmethod
    def pil_image(image):
        if isinstance(image,QPixmap):image=image.toImage()
        if not isinstance(image,QImage) or image.isNull():raise ValueError('Die Zwischenablage enthält kein lesbares Bild.')
        checked_size(image.width(),image.height())
        image=image.convertToFormat(QImage.Format.Format_RGBA8888)
        return Image.frombytes('RGBA',(image.width(),image.height()),bytes(image.constBits()),'raw','RGBA',image.bytesPerLine())

    def dropEvent(self,event):
        source=self.drop_source(event)
        if not source:event.ignore();return
        if source[0]=='native':
            try:source=('image',self.pil_image(event.mimeData().imageData()))
            except Exception as exc:
                event.ignore();self.statusBar().showMessage(str(exc),6000);return
        event.setDropAction(Qt.DropAction.CopyAction);event.accept()
        self._drop_pending=True
        QTimer.singleShot(0,lambda:self.finish_drop(source))

    def finish_drop(self,source):
        try:
            kind,value=source
            if kind=='image':self.place_image(value)
            elif kind=='url':
                image=self.load_web_image(value)
                if image is not None:self.place_image(image,name='Browser-Bild')
            elif Path(value).suffix.lower() in IMAGE_SUFFIXES:self.place_image(load_image(value),name=Path(value).stem)
            elif self.confirm():self.open_path(value)
        except Exception as exc:QMessageBox.warning(self,'Bild einfügen',str(exc))
        finally:
            self._drop_pending=False;self.statusBar().clearMessage()

    def load_web_image(self,url):
        cancel=Event();pool=ThreadPoolExecutor(max_workers=1)
        future=pool.submit(download_image,url,cancel)
        progress=QProgressDialog('Browser-Bild wird geladen …','Abbrechen',0,0,self)
        progress.setWindowModality(Qt.WindowModality.WindowModal);progress.setMinimumDuration(0)
        timer=QTimer(progress);timer.timeout.connect(lambda:progress.accept() if future.done() else None);timer.start(30)
        try:
            if progress.exec() and future.done():return future.result()
            return None
        finally:
            cancel.set();timer.stop();pool.shutdown(wait=False,cancel_futures=True)

    def place_image(self,image,upscale=True,name='Eingefügtes Bild'):
        prepared=self.doc.prepare_import(image,upscale)
        dialog=PlacementDialog(self.doc,prepared,self)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        position=(dialog.x.value(),dialog.y.value())
        self.doc.paste(prepared,position=position,name=name)
        selection=self.doc.selection
        self.tool.setCurrentText('Auswahl');self.doc.selection=selection
        self.refresh();self.fit();self.canvas.setFocus()
        self.statusBar().showMessage('Bild auf eigener Ebene eingefügt. Mit Auswahl weiter verschieben; Strg+Z macht das Einfügen rückgängig.',8000)

    def copy_image(self):
        self.doc.copy()
        if self.doc.clipboard is not None:QApplication.clipboard().setImage(ImageQt(self.doc.clipboard).copy())

    def paste_image(self):
        try:
            mime=QApplication.clipboard().mimeData()
            if mime and mime.hasImage():self.place_image(self.pil_image(mime.imageData()),upscale=False)
            elif self.doc.clipboard is not None:self.place_image(self.doc.clipboard,upscale=False)
        except Exception as exc:QMessageBox.warning(self,'Bild einfügen',str(exc))

    def eventFilter(self,watched,event):
        handlers={QEvent.Type.DragEnter:self.dragEnterEvent,QEvent.Type.DragMove:self.dragMoveEvent,
                  QEvent.Type.DragLeave:self.dragLeaveEvent,QEvent.Type.Drop:self.dropEvent}
        if event.type() in handlers:
            handlers[event.type()](event);return True
        return super().eventFilter(watched,event)

    def open_pdf(self,path):
        password=''
        while True:
            try:
                dialog=PdfImportDialog(path,self,password)
                if dialog.exec()==QDialog.DialogCode.Accepted:
                    image=dialog.result_image
                    self.doc.__init__(image.size);self.doc.image=image
                    self.doc.layers[0]['name']=f'{Path(path).stem} · Seite {dialog.page.value()}'
                    # Imported pages are unsaved documents, never bound to the source PDF.
                    self.doc.revision=self.doc.next_revision=1
                    self.refresh();self.fit()
                dialog.release()
                dialog.deleteLater()
                return
            except PdfPasswordRequired:
                password,ok=QInputDialog.getText(self,'PDF-Passwort','Passwort für das PDF:',QLineEdit.EchoMode.Password)
                if not ok:return
            except Exception as error:
                QMessageBox.warning(self,'PDF öffnen',str(error));return

    def save(self,as_new=False,copy=False):
        if self.gif_panel:return self.gif_panel.save(as_new,copy)
        path=self.doc.path
        if not copy and len(self.doc.layers)>1 and (not path or Path(path).suffix.lower() not in ('.repainko','.repaintko')):
            as_new=True
            if path:path=str(Path(path).with_suffix('.repaintko'))
        if as_new or copy or not path:
            suggested=Path(path) if path else Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation))/('Repaintko.repaintko' if len(self.doc.layers)>1 else 'Repaintko.png')
            if copy:suggested=suggested.with_name(suggested.stem+' - Kopie'+suggested.suffix)
            path,selected=QFileDialog.getSaveFileName(self,'Als Kopie speichern' if copy else 'Bild speichern',str(suggested),FILE_FILTER)
            if not path:return False
            if not Path(path).suffix:path+={'Repaintko-Projekt':'.repaintko','JPEG':'.jpg','Bitmap':'.bmp','WebP':'.webp','TIFF':'.tif','GIF':'.gif'}.get(selected.split()[0],'.png')
        try:
            self.doc.save(path,copy,transparent=self.transparent_save.isChecked());self.refresh()
            if copy:self.statusBar().showMessage('Kopie gespeichert: '+path,8000)
            elif len(self.doc.layers)>1 and Path(path).suffix.lower() not in ('.repainko','.repaintko'):
                self.statusBar().showMessage('Bild exportiert. Ebenen bleiben ungespeichert: als .repaintko speichern.',12000)
                return False
            return True
        except Exception as exc:QMessageBox.warning(self,'Speichern fehlgeschlagen',str(exc));return False

    def save_copy(self):return self.save(copy=True)

    def save_project_dialog(self):
        if self.gif_panel:return self.gif_panel.save()
        path=Path(self.doc.path).with_suffix('.repaintko') if self.doc.path else Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation))/'Repaintko.repaintko'
        target,_=QFileDialog.getSaveFileName(self,'Projekt mit Ebenen speichern',str(path),'Repaintko-Projekt (*.repaintko *.repainko)')
        if target:self.edit(lambda:self.doc.save(target if target.lower().endswith(('.repainko','.repaintko')) else target+'.repaintko'))

    def import_image(self):
        path,_=QFileDialog.getOpenFileName(self,'Bild einfügen','','Bilder (*.png *.jpg *.jpeg *.bmp *.webp *.tif)')
        if path:
            self.edit(lambda:self.place_image(load_image(path),name=Path(path).stem))

    def pdf(self):
        suggested=Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation))/'Repaintko.pdf'
        path,_=QFileDialog.getSaveFileName(self,'Druckdatei exportieren',str(suggested),'PDF (*.pdf)')
        if path:self.edit(lambda:self.doc.composite().save(path if path.lower().endswith('.pdf') else path+'.pdf','PDF',resolution=150))

    def cut(self):
        self.copy_image()
        if not self.doc.selection:self.doc.selection=(0,0,*self.doc.image.size)
        self.edit(lambda:self.doc.delete(self.bg))

    def select_all(self):
        self.tool.setCurrentText('Auswahl');self.doc.selection=(0,0,*self.doc.image.size);self.canvas.update()

    def clear(self):
        self.doc.remember();self.doc.image=Image.new(self.doc.image.mode,self.doc.image.size,(0,0,0,0) if self.doc.image.mode=='RGBA' else self.bg);self.refresh()

    def dimensions(self,title,callback):
        dialog=QDialog(self);dialog.setWindowTitle(title)
        layout=QFormLayout(dialog)
        width,height=QSpinBox(),QSpinBox()
        for field,value in [(width,self.doc.image.width),(height,self.doc.image.height)]:field.setRange(1,64000);field.setValue(value)
        layout.addRow('Breite (px)',width);layout.addRow('Höhe (px)',height)
        presets=QComboBox();presets.addItems(['Vorlage wählen']+list(PRESETS))
        presets.currentTextChanged.connect(lambda name:(width.setValue(PRESETS[name][0]),height.setValue(PRESETS[name][1])) if name in PRESETS else None)
        layout.addRow('Auflösung',presets)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        layout.addRow(buttons);buttons.rejected.connect(dialog.reject)
        def apply():
            try:callback(checked_size(width.value(),height.value()));dialog.accept();self.refresh();self.fit()
            except Exception as exc:QMessageBox.warning(dialog,'Ungültige Größe',str(exc))
        buttons.accepted.connect(apply);dialog.exec()

    def add_text(self,point,color):
        text,ok=QInputDialog.getMultiLineText(self,'Text einfügen','Text:')
        if not ok or not text:return
        font=self.font.currentFont();font.setPixelSize(self.font_size.value());font.setBold(self.bold.isChecked())
        metrics=QFontMetrics(font)
        lines=text.split('\n')
        width=max(metrics.horizontalAdvance(line) for line in lines)+metrics.height()*2
        height=metrics.lineSpacing()*len(lines)+metrics.height()
        width=min(width,self.doc.image.width);height=min(height,self.doc.image.height)
        rendered=QImage(width,height,QImage.Format.Format_RGBA8888);rendered.fill(Qt.GlobalColor.transparent)
        painter=QPainter(rendered);painter.setFont(font);painter.setPen(QColor(color))
        for index,line in enumerate(lines):painter.drawText(0,metrics.ascent()+index*metrics.lineSpacing(),line)
        painter.end()
        tile=Image.frombytes('RGBA',(width,height),bytes(rendered.constBits()),'raw','RGBA',rendered.bytesPerLine())
        self.doc.remember('effect')
        self.doc.image=self.doc.image.convert('RGBA');self.doc.image.alpha_composite(tile,point)
        self.refresh()

    def fill_area(self,point,ink):
        color=tuple(bytes.fromhex(ink[1:]))
        source=self.doc.image
        if source.mode=='RGBA':color+=(255,)
        progress=QProgressDialog('Bereich wird gefüllt …','Abbrechen',0,0,self)
        progress.setWindowModality(Qt.WindowModality.WindowModal);progress.setMinimumDuration(0)
        executor=ThreadPoolExecutor(max_workers=1)
        future=executor.submit(filled_image,source,point,color)
        timer=QTimer(progress)
        timer.timeout.connect(lambda:progress.accept() if future.done() else None);timer.start(30)
        accepted=progress.exec();timer.stop()
        try:
            if accepted and future.done():
                result=future.result()
                if result is not source:
                    self.doc.remember('effect');self.doc.image=result;self.refresh()
        except Exception as exc:QMessageBox.warning(self,'Füllen',str(exc))
        finally:executor.shutdown(wait=False,cancel_futures=True)


    def effects(self):
        if self.canvas.start is None:EffectsDialog(self).exec()

    def remove_objects(self):
        if not self.plus_active:
            QMessageBox.information(self,'Repaintko Plus','Aktiviere Repaintko Plus unter Datei → Repaintko Plus aktivieren.');return
        if self.canvas.start is not None:return
        if not self.doc.layers[self.doc.active]['visible']:
            QMessageBox.information(self,'Ebene ausgeblendet','Bitte zuerst die zu bearbeitende Ebene sichtbar schalten.');return
        if len(self.doc.layers)>=32 or self.doc.image.width*self.doc.image.height*(len(self.doc.layers)+1)>128_000_000:
            QMessageBox.warning(self,'Ebenenlimit','Für das Original und das Ergebnis wird eine zusätzliche Ebene benötigt. Bitte vorher eine Ebene entfernen oder zusammenführen.');return
        dialog=RemovalDialog(self.doc.image,self)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            self.edit(lambda:self.doc.apply_removal(dialog.result_image))

    def set_zoom(self,zoom):
        if self.canvas.start is not None:return
        self.auto_fit=False
        self.canvas.zoom=max(0.01,min(16,zoom));self.canvas.sync(False);self.zoom_label.setText(f'{round(self.canvas.zoom*100)} %')

    def fit(self):
        self.set_zoom(min(1,max(1,self.scroll.viewport().width()-20)/self.doc.image.width,
                          max(1,self.scroll.viewport().height()-20)/self.doc.image.height))
        self.auto_fit=True

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'settings'):
            if self.width()<1000 and not self.compact:
                self.settings.hide();self.tools_dock.hide();self.layers_dock.hide();self.compact=True
            elif self.width()>=1050:self.compact=False
            if self.auto_fit:QTimer.singleShot(0,self.fit)

    def closeEvent(self,event):
        if self.redatako is not None and not self.redatako.confirm():event.ignore();return
        if self.redrawko is not None and not self.redrawko.confirm():event.ignore();return
        if self.draw_together is not None and not self.draw_together.confirm_shutdown():event.ignore();return
        if self.retexto is not None and not self.retexto.confirm_all():event.ignore();return
        if self.notebook is not None and not self.notebook.flush():event.ignore();return
        if self.video_editor is not None and (self.video_editor.busy or not self.video_editor.confirm()):event.ignore();return
        self.leave_video_editor()
        if self.gif_panel and not self.toggle_gif(False):event.ignore();return
        if self.confirm():
            if self.redatako is not None:self.redatako.shutdown()
            if self.redrawko is not None:self.redrawko.shutdown()
            self.timesheet.shutdown()
            if self.draw_together is not None:self.draw_together.shutdown()
            if self.browser is not None:self.browser.shutdown()
            self.spotify_monitor.stop()
            if self.video_editor is not None:self.video_editor.player.stop();self.video_editor.player.setSource(QUrl())
            event.accept()
        else:event.ignore()


def main():
    app=QApplication.instance() or QApplication([])
    app.setApplicationName('Repaintko')
    browser_launch='--browser' in sys.argv
    address=next((arg for arg in sys.argv[1:] if arg.startswith(('https://','http://'))),'') if browser_launch else ''
    from browser_ipc import forward,listen
    if browser_launch and forward(address):return
    window=Repainko();window.show()
    if getattr(sys,"frozen",False) and "--smoke-test" not in sys.argv:
        from update_ui import Updater
        window.updater=Updater(window)
    window.browser_ipc=listen(window)
    if browser_launch:
        window.open_browser()
        if address:window.browser.open_external(address)
    if '--smoke-test' in sys.argv and not browser_launch:
        report=Path(sys.argv[sys.argv.index('--smoke-test')+1])
        def verify():
            try:
                window.resize(800,600);window.fit();app.processEvents()
                modes=[window.censor_mode.itemText(i) for i in range(window.censor_mode.count())]
                assert 'Schwarz' not in modes
                assert 'Feine Wischstreifen' in modes and 'Malpinsel-Blur' in modes
                assert window.canvas.width()>100 and window.canvas.height()>100
                from sql_schema import parse_schema,export_schema
                import sqlite3,pymysql,pyodbc
                import redata_ui
                sample=parse_schema('CREATE TABLE a(id INTEGER PRIMARY KEY); CREATE TABLE b(id INTEGER PRIMARY KEY, a_id INTEGER REFERENCES a(id));')
                assert len(sample['edges'])==1
                connection=sqlite3.connect(':memory:');connection.executescript(export_schema(sample));connection.close()
                window.grab().save(str(report.with_suffix('.png')))
                report.write_text(json.dumps({'ok':True,'modes':modes,'size':[window.width(),window.height()],
                                              'frozen':bool(getattr(sys,'frozen',False))},ensure_ascii=False),encoding='utf-8')
                app.exit(0)
            except Exception as exc:
                report.write_text(json.dumps({'ok':False,'error':str(exc)}),encoding='utf-8');app.exit(1)
        QTimer.singleShot(300,verify)
    sys.exit(app.exec())
