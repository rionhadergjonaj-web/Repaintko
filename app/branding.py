"""Local Plus activation and resolution-independent application branding."""
import hashlib
import hmac
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QIcon

KEY_DIGEST='e841ddb9d7035e169d3d9e6dbbb57988fb3e42b3d240a0b83b5c365a88a779c6'
SETTING='plus/activation'


def valid_key(key):
    return hmac.compare_digest(hashlib.sha256(key.strip().encode('utf-8')).hexdigest(),KEY_DIGEST)


def is_activated(settings):
    return hmac.compare_digest(str(settings.value(SETTING,'')),KEY_DIGEST)


def activate(settings,key):
    if not valid_key(key):return False
    settings.setValue(SETTING,KEY_DIGEST);settings.sync()
    if settings.status()!=settings.Status.NoError:
        raise OSError('Die Aktivierung konnte nicht gespeichert werden. Bitte die Schreibrechte der App-Einstellungen prüfen.')
    return True


def brand_icon(plus=False):
    pixmap=QPixmap(256,256);pixmap.fill(Qt.GlobalColor.transparent)
    p=QPainter(pixmap);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.scale(4,4)
    p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor('#3288ff' if plus else '#63e6be'));p.drawEllipse(3,3,56,56)
    p.setPen(QPen(QColor('#112b46' if plus else '#153d36'),8,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(23,41),QPointF(40,19))
    if plus:
        p.setPen(QPen(QColor('#edf5ff'),2));p.setBrush(QColor('#1652bb'));p.drawEllipse(39,39,23,23)
        p.setPen(QPen(QColor('white'),3,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(45,50.5),QPointF(56,50.5));p.drawLine(QPointF(50.5,45),QPointF(50.5,56))
    p.end();return QIcon(pixmap)
