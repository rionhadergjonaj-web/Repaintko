"""Offline, searchable help center. Uses Qt rich text, not a web engine."""
import re
from PySide6.QtCore import Qt,QUrl,Signal,QSize
from PySide6.QtGui import QImage,QPainter,QColor,QPen,QFont,QTextDocument,QTextCursor
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLineEdit,QSplitter,QTreeWidget,QTreeWidgetItem,QTextBrowser,QLabel
from help_content import articles
from tool_icons import tool_icon

def figure(key):
    image=QImage(640,220,QImage.Format.Format_ARGB32);image.fill(QColor('#edf3fa'))
    p=QPainter(image);p.setRenderHint(QPainter.RenderHint.Antialiasing)
    def text(x,y,w,h,label,size=13):
        p.setPen(QColor('#183047'));p.setFont(QFont('Segoe UI',size));p.drawText(x,y,w,h,Qt.AlignmentFlag.AlignCenter|Qt.TextFlag.TextWordWrap,label)
    def box(x,y,w,h,color):p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor(color));p.drawRoundedRect(x,y,w,h,10,10)
    if key=='tools':
        names=['Pinsel','Füller','Bleistift','Airbrush','Radierer','Zensur','Füllen','Pipette','Linie','Rechteck','Rundrechteck','Ellipse','Dreieck','Polygon','Text','Auswahl','Lupe']
        for i,name in enumerate(names):
            x=8+(i%9)*70;y=8+(i//9)*105;p.drawPixmap(x+13,y,tool_icon(name).pixmap(QSize(42,42)));text(x,y+45,68,48,name,9)
    elif key=='layers':
        for i,(label,color) in enumerate([('3 · Text / Details','#9bd9ca'),('2 · Foto','#b3c9ed'),('1 · Hintergrund','#d3c6ef')]):
            box(32+i*20,18+i*57,260,48,color);text(32+i*20,18+i*57,260,48,label)
        text(345,30,270,150,'Oben liegt vorne\n\nHäkchen = sichtbar\nKlick = aktive Ebene\nDeckkraft = Durchsichtigkeit')
    elif key=='alpha':
        for i,amount in enumerate([25,60,100]):
            x=25+i*205
            for r in range(4):
                for c in range(6):box(x+c*28,22+r*28,28,28,'#ffffff' if (r+c)%2 else '#d3dce5')
            p.setOpacity(amount/100);box(x+15,40,130,75,'#347cdc');p.setOpacity(1);text(x,145,170,50,f'{amount} % Deckkraft')
    elif key=='gif':
        for i in range(3):
            x=25+i*205;box(x,20,175,125,'#ffffff');p.setBrush(QColor('#67d8b5'));p.drawEllipse(x+20+i*35,62,40,40)
            if i:p.setBrush(QColor(70,130,210,66));p.drawEllipse(x+20+(i-1)*35,62,40,40)
            text(x,155,175,45,f'Frame {i+1}'+('\nVorheriger: 26 %' if i else ''))
    elif key=='video':
        box(25,28,360,65,'#a8c7eb');box(360,28,250,65,'#b4dece');box(360,28,25,65,'#e7d598')
        text(25,35,300,45,'Clip 1');text(400,35,190,45,'Clip 2')
        p.setPen(QPen(QColor('#ce4f43'),3));p.drawLine(230,10,230,120)
        text(35,125,320,60,'Abspielkopf → Strg+S teilt hier');text(375,125,240,60,'Überlappung = Übergang')
    else:
        labels={'together':['Anna · Ebene 1\nRote Striche','Ben · Ebene 2\nBlaue Striche','Host ordnet Aktionen\nAlle sehen dasselbe Bild'], 'modes':['Bild\nZeichnen & Fotos','GIF\nFrames & FPS','Video · Plus\nClips & Keyframes'], 'plus':['1 · Datei\nPlus aktivieren','2 · Access-Key\nEingeben & bestätigen','3 · Blaues Logo +\nPlus ist aktiv'], 'ai':['1 · Markieren\nObjekt übermalen','2 · Modus wählen\nErgänzen / Transparent','3 · Vorschau prüfen\nNeue Ebene übernehmen']}[key]
        for i,label in enumerate(labels):
            x=15+i*210;box(x,30,190,145,['#bed4f3','#c2e6da','#dacdf1'][i]);text(x+8,48,174,110,label)
        if key=='modes':text(20,180,600,35,'ReBrowko: Internet & Google · Hilfe: offline nachschlagen',11)
    p.end();return image

class ArticleView(QTextBrowser):
    def loadResource(self,kind,url):
        if kind==QTextDocument.ResourceType.ImageResource and url.scheme()=='help':
            key=url.path()
            if key in ('tools','modes','layers','alpha','gif','video','ai','plus','together'):return figure(key)
        return super().loadResource(kind,url)
    def resizeEvent(self,event):
        super().resizeEvent(event);self.fit_images()
    def fit_images(self):
        width=min(640,max(120,self.viewport().width()-40));block=self.document().begin()
        while block.isValid():
            it=block.begin()
            while not it.atEnd():
                fragment=it.fragment()
                if fragment.isValid() and fragment.charFormat().isImageFormat():
                    fmt=fragment.charFormat().toImageFormat();fmt.setWidth(width);fmt.setHeight(width*220/640)
                    cursor=QTextCursor(self.document());cursor.setPosition(fragment.position());cursor.setPosition(fragment.position()+fragment.length(),QTextCursor.MoveMode.KeepAnchor);cursor.setCharFormat(fmt)
                it+=1
            block=block.next()

class HelpCenter(QWidget):
    returnRequested=Signal()
    def __init__(self,parent=None):
        super().__init__(parent);self.pages=articles();self.by_key={p['key']:p for p in self.pages};self.history=[];self.position=-1
        root=QVBoxLayout(self);top=QHBoxLayout();root.addLayout(top)
        for label,fn in [('← Zur Arbeit',self.returnRequested.emit),('Startseite',lambda:self.show_page('home')),('Zurück',lambda:self.move(-1)),('Vor',lambda:self.move(1))]:
            b=QPushButton(label);b.clicked.connect(lambda checked=False,fn=fn:fn());top.addWidget(b)
            if label=='Zurück':self.back=b
            if label=='Vor':self.forward=b
        self.search=QLineEdit();self.search.setPlaceholderText('Hilfe durchsuchen …');self.search.setClearButtonEnabled(True);self.search.textChanged.connect(self.filter);top.addWidget(self.search,1)
        split=QSplitter();root.addWidget(split,1);self.tree=QTreeWidget();self.tree.setHeaderHidden(True);self.tree.setMinimumWidth(150);split.addWidget(self.tree)
        self.body=ArticleView();self.body.setOpenLinks(False);self.body.setOpenExternalLinks(False);self.body.anchorClicked.connect(self.follow);self.body.setStyleSheet('QTextBrowser {background:#ffffff;color:#203044;border:0;padding:16px;}');split.addWidget(self.body);split.setSizes([240,760])
        self.body.document().setDefaultStyleSheet('h1 {color:#173957;} h2 {color:#245d7b;margin-top:24px;} a {color:#1263b2;} td,th {padding:7px;border:1px solid #cbd5e1;} p,li {line-height:145%;}')
        for key in ('tools','modes','layers','alpha','gif','video','ai','plus','together'):self.body.document().addResource(QTextDocument.ResourceType.ImageResource,QUrl('help:'+key),figure(key))
        self.count=QLabel();root.addWidget(self.count);self.tree.itemClicked.connect(self.selected);self.filter('');self.show_page('home')
    def filter(self,query):
        words=query.casefold().split();self.tree.clear();groups={};count=0
        for page in self.pages:
            if not all(word in (page['title']+' '+page['group']+' '+page['text']).casefold() for word in words):continue
            group=groups.get(page['group'])
            if group is None:group=QTreeWidgetItem(self.tree,[page['group']]);groups[page['group']]=group
            item=QTreeWidgetItem(group,[page['title']]);item.setData(0,Qt.ItemDataRole.UserRole,page['key']);count+=1
        self.tree.expandAll();self.count.setText(f'{count} Artikel'+(' · Keine Treffer. Versuche ein kürzeres Suchwort.' if not count else ' · Hilfe funktioniert auch ohne Internet.'))
    def selected(self,item,column):
        key=item.data(0,Qt.ItemDataRole.UserRole)
        if key:self.show_page(key)
    def follow(self,url):
        if url.scheme()=='help':self.show_page(url.path())
    def show_page(self,key,record=True):
        if key not in self.by_key:return
        if record:
            self.history=self.history[:self.position+1]
            if not self.history or self.history[-1]!=key:self.history.append(key)
            self.position=len(self.history)-1
        self.body.setMarkdown(self.by_key[key]['text']);self.body.fit_images();self.body.verticalScrollBar().setValue(0)
        self.back.setEnabled(self.position>0);self.forward.setEnabled(self.position<len(self.history)-1)
    def move(self,delta):
        target=self.position+delta
        if 0<=target<len(self.history):self.position=target;self.show_page(self.history[target],False)
