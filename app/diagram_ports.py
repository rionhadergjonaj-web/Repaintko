"""Four draggable connector ports and orthogonal routing."""
import math
from PySide6.QtCore import Qt,QPointF,QRectF
from PySide6.QtGui import QColor,QPen,QPolygonF,QPainterPath
from PySide6.QtWidgets import QGraphicsObject,QGraphicsItem

DIRECTIONS={'left':(-1,0),'right':(1,0),'top':(0,-1),'bottom':(0,1)}

class Port(QGraphicsObject):
    def __init__(self,node,side):
        super().__init__(node);self.node=node;self.side=side
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.setAcceptHoverEvents(True);self.setCursor(Qt.CursorShape.CrossCursor);self.setZValue(100)
        self.setToolTip('Verbindung ziehen');self.setOpacity(.48)
    def boundingRect(self):return QRectF(-12,-12,24,24)
    def paint(self,p,option,widget=None):
        if self.node.owner.exporting:return
        dx,dy=DIRECTIONS[self.side];p.rotate(math.degrees(math.atan2(dy,dx)))
        p.setPen(QPen(QColor('#76b9ff'),1));p.setBrush(QColor('#4c9aff'))
        p.drawPolygon(QPolygonF([QPointF(-8,-4),QPointF(1,-4),QPointF(1,-9),QPointF(10,0),QPointF(1,9),QPointF(1,4),QPointF(-8,4)]))
    def hoverEnterEvent(self,event):self.setOpacity(1)
    def hoverLeaveEvent(self,event):self.setOpacity(.48)
    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:
            self.node.owner.views()[0].begin_link(self.node,self.side);event.accept()
    def mouseMoveEvent(self,event):self.node.owner.views()[0].move_link(event.scenePos());event.accept()
    def mouseReleaseEvent(self,event):self.node.owner.views()[0].finish_link(event.scenePos());event.accept()

def auto_port(node,toward):
    p=node.mapFromScene(toward)-QPointF(node.data['w']/2,node.data['h']/2)
    if abs(p.y())/node.data['h']>abs(p.x())/node.data['w']:return 'bottom' if p.y()>=0 else 'top'
    return 'right' if p.x()>=0 else 'left'

def normal(node,side):
    dx,dy=DIRECTIONS[side];origin=node.mapToScene(QPointF(0,0))
    return node.mapToScene(QPointF(dx,dy))-origin

def orthogonal(start,end,source_normal,target_normal,obstacles):
    a=start+source_normal*32;b=end+target_normal*32
    candidates=[[a,QPointF(b.x(),a.y()),b],[a,QPointF(a.x(),b.y()),b]]
    xs=[(a.x()+b.x())/2,min(a.x(),b.x())-64,max(a.x(),b.x())+64]
    ys=[(a.y()+b.y())/2,min(a.y(),b.y())-64,max(a.y(),b.y())+64]
    for r in obstacles[:12]:xs.extend([r.left()-12,r.right()+12]);ys.extend([r.top()-12,r.bottom()+12])
    candidates += [[a,QPointF(x,a.y()),QPointF(x,b.y()),b] for x in xs]
    candidates += [[a,QPointF(a.x(),y),QPointF(b.x(),y),b] for y in ys]
    def score(points):
        cost=0
        for p,q in zip(points,points[1:]):
            cost+=abs(p.x()-q.x())+abs(p.y()-q.y())
            for r in obstacles:
                if abs(p.x()-q.x())<.01:
                    hit=r.left()<p.x()<r.right() and max(p.y(),q.y())>r.top() and min(p.y(),q.y())<r.bottom()
                else:hit=r.top()<p.y()<r.bottom() and max(p.x(),q.x())>r.left() and min(p.x(),q.x())<r.right()
                if hit:cost+=100000
        return cost+len(points)*3
    route=[start]+min(candidates,key=score)+[end];clean=[]
    for p in route:
        if not clean or (p-clean[-1]).manhattanLength()>.01:clean.append(p)
    return clean
