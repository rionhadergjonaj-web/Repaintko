"""Small vector tool symbols, rendered at high DPI without font glyphs."""
from PySide6.QtCore import Qt,QPointF,QRectF
from PySide6.QtGui import QIcon,QPixmap,QPainter,QPen,QColor,QPolygonF

def tool_icon(name):
    pix=QPixmap(64,64);pix.fill(Qt.GlobalColor.transparent)
    p=QPainter(pix);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.scale(2,2)
    p.setBrush(QColor('#203449'));p.setPen(Qt.PenStyle.NoPen);p.drawRoundedRect(QRectF(1,1,30,30),6,6)
    p.setPen(QPen(QColor('#eef8ff'),1.8,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin));p.setBrush(Qt.BrushStyle.NoBrush)
    def line(a,b):p.drawLine(QPointF(*a),QPointF(*b))
    def poly(points):p.drawPolygon(QPolygonF([QPointF(*a) for a in points]))
    if name=='Füller':
        poly([(7,25),(11,10),(23,5),(27,9),(22,21)]);line((7,25),(18,14));p.drawEllipse(QPointF(18,14),2,2);line((22,6),(26,10))
    elif name in ('Pinsel','Bleistift','Pipette'):
        poly([(8,20),(21,6),(26,11),(12,25),(6,27)]);line((18,9),(23,14))
        if name=='Pinsel':line((7,21),(12,25));line((6,27),(14,27))
        if name=='Pipette':line((19,5),(27,13))
    elif name=='Airbrush':
        poly([(7,12),(17,12),(17,25),(7,25)]);line((10,8),(15,8));line((13,8),(13,12))
        for x,y in [(22,9),(25,6),(27,12),(23,16),(28,19)]:p.drawPoint(x,y)
    elif name=='Radierer':poly([(5,20),(17,7),(27,17),(18,26),(11,26)]);line((11,14),(21,23))
    elif name=='Zensur':
        for x,y in [(7,7),(16,7),(7,16),(16,16)]:p.drawRect(x,y,7,7)
    elif name=='Füllen':poly([(6,15),(16,5),(25,14),(15,24)]);line((7,16),(23,16));p.drawEllipse(QPointF(25,24),2,3)
    elif name=='Linie':line((7,25),(25,7))
    elif name=='Rechteck':p.drawRect(6,8,20,16)
    elif name=='Rundrechteck':p.drawRoundedRect(QRectF(6,8,20,16),5,5)
    elif name=='Ellipse':p.drawEllipse(QRectF(5,8,22,16))
    elif name=='Dreieck':poly([(16,6),(27,25),(5,25)])
    elif name=='Polygon':poly([(6,12),(19,5),(27,17),(19,26),(7,23)])
    elif name=='Text':line((7,7),(25,7));line((16,7),(16,25));line((11,25),(21,25))
    elif name=='Auswahl':p.setPen(QPen(QColor('#eef8ff'),1.8,Qt.PenStyle.DashLine));p.drawRect(6,6,20,20)
    elif name=='Lupe':p.drawEllipse(QRectF(5,5,16,16));line((19,19),(27,27))
    p.end();return QIcon(pix)
