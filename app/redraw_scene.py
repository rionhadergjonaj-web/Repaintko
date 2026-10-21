"""Qt vector scene for ReDrawko: shapes, attached connectors and direct manipulation."""
import math,base64
from PySide6.QtCore import Qt,QRectF,QPointF,Signal,QMimeData
from PySide6.QtGui import QPainter,QPainterPath,QPen,QBrush,QColor,QFont,QImage,QPolygonF,QTransform
from PySide6.QtWidgets import QGraphicsScene,QGraphicsView,QGraphicsObject,QGraphicsPathItem,QGraphicsItem,QGraphicsRectItem,QGraphicsSimpleTextItem,QApplication

def outline(kind,w,h):
    p=QPainterPath();r=QRectF(0,0,w,h)
    if kind in ('ellipse','attribute','key_attribute','usecase'):p.addEllipse(r)
    elif kind in ('rounded','terminator','process'):p.addRoundedRect(r,min(20,h/2),min(20,h/2))
    elif kind in ('diamond','decision','relationship'):p.addPolygon(QPolygonF([QPointF(w/2,0),QPointF(w,h/2),QPointF(w/2,h),QPointF(0,h/2)]));p.closeSubpath()
    elif kind=='triangle':p.addPolygon(QPolygonF([QPointF(w/2,0),QPointF(w,h),QPointF(0,h)]));p.closeSubpath()
    elif kind in ('hexagon','pentagon','star'):
        count=10 if kind=='star' else (6 if kind=='hexagon' else 5)
        points=[]
        for i in range(count):
            radius=.43 if kind=='star' and i%2 else 1;a=-math.pi/2+i*2*math.pi/count
            points.append(QPointF(w/2+math.cos(a)*w/2*radius,h/2+math.sin(a)*h/2*radius))
        p.addPolygon(QPolygonF(points));p.closeSubpath()
    elif kind=='data':p.addPolygon(QPolygonF([QPointF(w*.2,0),QPointF(w,0),QPointF(w*.8,h),QPointF(0,h)]));p.closeSubpath()
    elif kind=='arrow':p.addPolygon(QPolygonF([QPointF(0,h*.25),QPointF(w*.6,h*.25),QPointF(w*.6,0),QPointF(w,h*.5),QPointF(w*.6,h),QPointF(w*.6,h*.75),QPointF(0,h*.75)]));p.closeSubpath()
    elif kind=='document':p.moveTo(0,0);p.lineTo(w,0);p.lineTo(w,h*.85);p.cubicTo(w*.5,h*.6,w*.5,h*1.1,0,h*.85);p.closeSubpath()
    elif kind=='note':p.addPolygon(QPolygonF([QPointF(0,0),QPointF(w-20,0),QPointF(w,20),QPointF(w,h),QPointF(0,h)]));p.closeSubpath()
    elif kind=='database':p.moveTo(0,15);p.cubicTo(0,-5,w,-5,w,15);p.lineTo(w,h-15);p.cubicTo(w,h+5,0,h+5,0,h-15);p.closeSubpath()
    elif kind=='cloud':
        p.moveTo(w*.15,h*.85);p.cubicTo(-w*.15,h*.7,0,h*.35,w*.15,h*.4);p.cubicTo(w*.1,0,w*.45,-h*.1,w*.52,h*.2);p.cubicTo(w*.75,0,w*1.1,h*.2,w*.87,h*.47);p.cubicTo(w*1.15,h*.65,w*.93,h,w*.7,h*.85);p.closeSubpath()
    elif kind=='delay':p.moveTo(0,0);p.lineTo(w*.5,0);p.cubicTo(w*1.15,0,w*1.15,h,w*.5,h);p.lineTo(0,h);p.closeSubpath()
    else:p.addRect(r)
    return p

class ResizeHandle(QGraphicsRectItem):
    def __init__(self,parent):
        super().__init__(-5,-5,10,10,parent);self.setBrush(QColor('#4c9aff'));self.setPen(QPen(Qt.GlobalColor.white));self.setCursor(Qt.CursorShape.SizeFDiagCursor);self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
    def mousePressEvent(self,event):self.parentItem().owner.doc.begin();event.accept()
    def mouseMoveEvent(self,event):
        item=self.parentItem();pt=item.mapFromScene(event.scenePos());item.prepareGeometryChange();item.data['w']=max(40,pt.x());item.data['h']=max(30,pt.y());item.setTransformOriginPoint(item.data['w']/2,item.data['h']/2);self.setPos(item.data['w'],item.data['h']);item.position_ports();item.update();item.owner.update_edges()
    def mouseReleaseEvent(self,event):self.parentItem().owner.finish_change();event.accept()

class NodeItem(QGraphicsObject):
    def __init__(self,owner,data,layer):
        super().__init__();self.owner=owner;self.data=data;self.locked=layer.get('locked',False) or data.get('locked',False);self.setAcceptHoverEvents(True)
        flags=QGraphicsItem.GraphicsItemFlag.ItemIsSelectable|QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        if not self.locked:flags|=QGraphicsItem.GraphicsItemFlag.ItemIsMovable
        self.setFlags(flags);self.setPos(data['x'],data['y']);self.setTransformOriginPoint(data['w']/2,data['h']/2);self.setRotation(data.get('rotation',0));self.setOpacity(data.get('opacity',100)/100)
        self.handle=ResizeHandle(self);self.handle.setPos(data['w'],data['h']);self.handle.hide();self.picture=QImage()
        from diagram_ports import Port
        self.ports={side:Port(self,side) for side in ('left','right','top','bottom')};self.position_ports()
        for port in self.ports.values():port.hide()
        if data.get('image'):self.picture.loadFromData(base64.b64decode(data['image']))
        self.setToolTip(data.get('link') or data.get('text',''));self.setZValue(data.get('z',0))
    def boundingRect(self):return QRectF(-16,-16,self.data['w']+32,self.data['h']+(55 if self.data['shape']=='actor' else 32))
    def shape(self):return outline(self.data['shape'],self.data['w'],self.data['h'])
    def position_ports(self):
        w,h=self.data['w'],self.data['h']
        for side,point in {'left':(-18,h/2),'right':(w+18,h/2),'top':(w/2,-18),'bottom':(w/2,h+18)}.items():self.ports[side].setPos(*point)
    def hoverEnterEvent(self,event):
        self.position_ports()
        for port in self.ports.values():port.setVisible(not self.locked)
    def hoverLeaveEvent(self,event):
        if self.owner.views() and getattr(self.owner.views()[0],'link_source',None) and self.owner.views()[0].link_source[0] is self:return
        for port in self.ports.values():port.hide()
    def itemChange(self,change,value):
        if change==QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene() and not self.owner.loading:
            if self.owner.doc.page['snap'] and not QApplication.keyboardModifiers()&Qt.KeyboardModifier.AltModifier:
                step=self.owner.doc.page['grid_size'];value=QPointF(round(value.x()/step)*step,round(value.y()/step)*step)
            return value
        if change==QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and self.scene() and not self.owner.loading:
            self.data['x']=self.pos().x();self.data['y']=self.pos().y();self.owner.update_edges()
        if change==QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged and hasattr(self,'handle'):self.handle.setVisible(bool(value) and not self.locked)
        return super().itemChange(change,value)
    def mousePressEvent(self,event):
        self.owner.doc.begin()
        super().mousePressEvent(event)
        group=self.data.get('group')
        if group:
            for item in self.owner.nodes.values():
                if item.data.get('group')==group:item.setSelected(True)
    def mouseReleaseEvent(self,event):super().mouseReleaseEvent(event);self.owner.finish_change()
    def mouseDoubleClickEvent(self,event):self.owner.edit_requested.emit(self.data['id']);event.accept()
    def paint(self,p,option,widget=None):
        n=self.data;w=n['w'];h=n['h'];kind=n['shape'];rect=QRectF(0,0,w,h)
        pen=QPen(QColor(n['stroke']),n.get('line_width',2));pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        if n.get('dashed'):pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen);p.setBrush(Qt.BrushStyle.NoBrush if n['fill']=='none' else QBrush(QColor(n['fill'])))
        if kind not in ('text','actor','image'):p.drawPath(outline(kind,w,h))
        font=QFont(n.get('font','Segoe UI'));font.setPointSizeF(n.get('font_size',15));font.setBold(n.get('bold',False));font.setItalic(n.get('italic',False));font.setUnderline(kind=='key_attribute');p.setFont(font)
        if kind=='image' and not self.picture.isNull():p.drawImage(rect,self.picture)
        elif kind=='actor':
            p.drawEllipse(QRectF(w*.35,0,w*.3,h*.28));p.drawLine(QPointF(w*.5,h*.28),QPointF(w*.5,h*.66));p.drawLine(QPointF(w*.15,h*.4),QPointF(w*.85,h*.4));p.drawLine(QPointF(w*.5,h*.66),QPointF(w*.2,h*.9));p.drawLine(QPointF(w*.5,h*.66),QPointF(w*.8,h*.9))
        elif kind=='database':p.drawEllipse(QRectF(0,0,w,30))
        elif kind=='subprocess':p.drawLine(QPointF(12,0),QPointF(12,h));p.drawLine(QPointF(w-12,0),QPointF(w-12,h))
        elif kind=='weak_entity':p.drawRect(rect.adjusted(5,5,-5,-5))
        elif kind=='note':p.drawPolyline(QPolygonF([QPointF(w-20,0),QPointF(w-20,20),QPointF(w,20)]))
        elif kind=='server':
            for y in (h*.3,h*.55,h*.8):p.drawLine(QPointF(10,y),QPointF(w-10,y));p.drawEllipse(QPointF(w-20,y-7),2,2)
        elif kind=='computer':p.drawRect(rect.adjusted(8,8,-8,-20));p.drawLine(QPointF(w*.5,h-20),QPointF(w*.5,h));p.drawLine(QPointF(w*.3,h),QPointF(w*.7,h))
        if kind in ('entity','swimlane'):
            p.fillRect(QRectF(1,1,w-2,33),QColor(n['stroke']));p.setPen(QColor('#ffffff'));font.setBold(True);p.setFont(font);p.drawText(QRectF(8,1,w-16,32),Qt.AlignmentFlag.AlignCenter,n['text']);font.setBold(False);font.setPointSizeF(max(8,n.get('font_size',15)-2));p.setFont(font);p.setPen(QColor(n['text_color']))
            for i,row in enumerate(n.get('rows',[])):
                y=36+i*26
                if y+26>h:break
                label=f"{row.get('key',''):3}  {row['name']} : {row.get('type','')}"+(' ?' if row.get('nullable') else '')
                p.drawText(QRectF(10,y,w-20,26),Qt.AlignmentFlag.AlignVCenter,p.fontMetrics().elidedText(label,Qt.TextElideMode.ElideRight,int(w-20)))
                p.setPen(QColor('#bdced0'));p.drawLine(QPointF(0,y+26),QPointF(w,y+26));p.setPen(QColor(n['text_color']))
        elif kind!='image':
            p.setPen(QColor(n['text_color']));alignment={'left':Qt.AlignmentFlag.AlignLeft,'right':Qt.AlignmentFlag.AlignRight}.get(n.get('align'),Qt.AlignmentFlag.AlignHCenter)|Qt.AlignmentFlag.AlignVCenter|Qt.TextFlag.TextWordWrap
            textrect=rect.adjusted(12,8,-12,-8)
            if kind=='actor':textrect=QRectF(0,h,w,35)
            p.drawText(textrect,int(alignment),n.get('text',''))
        if self.isSelected():
            p.setPen(QPen(QColor('#3189ff'),1,Qt.PenStyle.DashLine));p.setBrush(Qt.BrushStyle.NoBrush);p.drawRect(rect.adjusted(-3,-3,3,3))
            for point in (QPointF(w/2,0),QPointF(w,h/2),QPointF(w/2,h),QPointF(0,h/2)):
                p.setBrush(QColor('#ffffff'));p.drawEllipse(point,4,4)
    def anchor(self,toward,port='auto'):
        w=self.data['w'];h=self.data['h'];center=self.mapToScene(QPointF(w/2,h/2))
        ports={'left':QPointF(0,h/2),'right':QPointF(w,h/2),'top':QPointF(w/2,0),'bottom':QPointF(w/2,h)}
        if port in ports:return self.mapToScene(ports[port])
        local=self.mapFromScene(toward)-QPointF(w/2,h/2);dx=local.x();dy=local.y()
        if abs(dx)+abs(dy)<.01:return self.mapToScene(QPointF(w,h/2))
        ratio=min(w/2/max(abs(dx),.001),h/2/max(abs(dy),.001))
        if self.data['shape'] in ('ellipse','attribute','usecase'):ratio=1/math.sqrt((dx/(w/2))**2+(dy/(h/2))**2)
        return self.mapToScene(QPointF(w/2+dx*ratio,h/2+dy*ratio))

class Waypoint(QGraphicsRectItem):
    def __init__(self,edge,index,point):
        super().__init__(-5,-5,10,10,edge);self.edge=edge;self.index=index;self.setBrush(QColor('#ffbd69'));self.setPen(QPen(Qt.GlobalColor.white));self.setPos(*point);self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
    def mousePressEvent(self,event):self.edge.owner.doc.begin();event.accept()
    def mouseMoveEvent(self,event):
        p=event.scenePos();self.edge.data['points'][self.index]=[p.x(),p.y()];self.setPos(p);self.edge.rebuild(False)
    def mouseReleaseEvent(self,event):self.edge.owner.finish_change();event.accept()

def marker(p,at,other,kind,color):
    if kind=='none':return
    angle=math.atan2(other.y()-at.y(),other.x()-at.x());p.save();p.translate(at);p.rotate(math.degrees(angle));p.setPen(QPen(color,1.7));p.setBrush(color)
    if kind in ('arrow','open'):
        if kind=='open':p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolygon(QPolygonF([QPointF(0,0),QPointF(13,-6),QPointF(13,6)]))
    elif kind=='diamond':p.drawPolygon(QPolygonF([QPointF(0,0),QPointF(8,-5),QPointF(16,0),QPointF(8,5)]))
    elif kind=='circle':p.setBrush(Qt.GlobalColor.white);p.drawEllipse(QPointF(6,0),5,5)
    else:
        if 'many' in kind:
            for y in (-7,0,7):p.drawLine(QPointF(0,y),QPointF(16,0))
        if kind in ('one','zero_one'):p.drawLine(QPointF(8,-7),QPointF(8,7))
        if kind.startswith('zero'):p.setBrush(Qt.GlobalColor.white);p.drawEllipse(QPointF(23,0),5,5)
        elif kind=='one':p.drawLine(QPointF(15,-7),QPointF(15,7))
    p.restore()

class EdgeItem(QGraphicsPathItem):
    def __init__(self,owner,data):
        super().__init__();self.owner=owner;self.data=data;self.handles=[];self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable);self.setZValue(data.get('z',-1));self.setOpacity(data.get('opacity',100)/100);self.rebuild()
    def shape(self):
        from PySide6.QtGui import QPainterPathStroker
        stroke=QPainterPathStroker();stroke.setWidth(18);return stroke.createStroke(self.path())
    def boundingRect(self):return self.path().boundingRect().adjusted(-40,-40,40,40).united(self.label_rect if hasattr(self,'label_rect') else QRectF())
    def rebuild(self,handles=True):
        a=self.owner.nodes.get(self.data['source']);b=self.owner.nodes.get(self.data['target'])
        if not a or not b:return
        ac=a.mapToScene(QPointF(a.data['w']/2,a.data['h']/2));bc=b.mapToScene(QPointF(b.data['w']/2,b.data['h']/2))
        from diagram_ports import auto_port,normal,orthogonal
        points=[QPointF(*pt) for pt in self.data.get('points',[])]
        sp=self.data.get('source_port','auto');tp=self.data.get('target_port','auto')
        if sp=='auto':sp=auto_port(a,points[0] if points else bc)
        if tp=='auto':tp=auto_port(b,points[-1] if points else ac)
        start=a.anchor(bc,sp);end=b.anchor(ac,tp)
        if a is b and not points:points=[start+QPointF(70,-70),end+QPointF(70,70)]
        if not points and self.data['route']=='orthogonal':
            obstacles=[n.mapRectToScene(QRectF(0,0,n.data['w'],n.data['h'])).adjusted(-6,-6,6,6) for n in self.owner.nodes.values()]
            points=orthogonal(start,end,normal(a,sp),normal(b,tp),obstacles)[1:-1]
        route=[start]+points+[end];path=QPainterPath(start)
        if self.data['route']=='curved':
            distance=max(40,(end-start).manhattanLength()/3)
            c1=points[0] if points else start+normal(a,sp)*distance;c2=points[-1] if points else end+normal(b,tp)*distance;path.cubicTo(c1,c2,end)
        else:
            for pt in route[1:]:path.lineTo(pt)
        from PySide6.QtGui import QFontMetricsF
        self.prepareGeometryChange();font=QFont('Segoe UI');font.setPointSizeF(self.data.get('font_size',13));metrics=QFontMetricsF(font);self.label_rect=QRectF()
        for text,percent,dx,dy in [(self.data.get('text',''),.5,self.data.get('label_x',0),self.data.get('label_y',0)),(self.data.get('source_label',''),.1,0,-14),(self.data.get('target_label',''),.9,0,-14)]:
            if text:
                pt=path.pointAtPercent(percent)+QPointF(dx,dy);r=metrics.boundingRect(text);self.label_rect=self.label_rect.united(QRectF(pt.x()-r.width()/2-6,pt.y()-r.height()/2-5,r.width()+12,r.height()+10))
        self.setPath(path);self.route_points=route;self.update()
        if handles:
            for handle in self.handles:
                if handle.scene():handle.scene().removeItem(handle)
            self.handles=[Waypoint(self,i,pt) for i,pt in enumerate(self.data.get('points',[]))]
            for h in self.handles:h.setVisible(self.isSelected())
    def paint(self,p,option,widget=None):
        e=self.data;color=QColor('#3189ff') if self.isSelected() else QColor(e['stroke']);pen=QPen(color,e.get('line_width',2));pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        if e.get('dashed'):pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen);p.setBrush(Qt.BrushStyle.NoBrush);p.drawPath(self.path())
        if self.path().length()>1:
            marker(p,self.path().pointAtPercent(0),self.path().pointAtPercent(.03),e.get('start','none'),color);marker(p,self.path().pointAtPercent(1),self.path().pointAtPercent(.97),e.get('end','arrow'),color)
        font=QFont('Segoe UI');font.setPointSizeF(e.get('font_size',13));p.setFont(font)
        for text,percent,dx,dy in [(e.get('text',''),.5,e.get('label_x',0),e.get('label_y',0)),(e.get('source_label',''),.1,0,-14),(e.get('target_label',''),.9,0,-14)]:
            if not text:continue
            pt=self.path().pointAtPercent(percent)+QPointF(dx,dy);rect=p.fontMetrics().boundingRect(text);r=QRectF(pt.x()-rect.width()/2-5,pt.y()-rect.height()/2-3,rect.width()+10,rect.height()+6)
            p.fillRect(r,QColor('#ffffff'));p.setPen(QColor(e.get('text_color','#172033')));p.drawText(r,Qt.AlignmentFlag.AlignCenter,text)
    def itemChange(self,change,value):
        if change==QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            for h in self.handles:h.setVisible(bool(value))
        return super().itemChange(change,value)
    def mouseDoubleClickEvent(self,event):
        if event.modifiers()&Qt.KeyboardModifier.ControlModifier:
            self.owner.doc.begin();pt=event.scenePos();points=self.data['points'];points.append([pt.x(),pt.y()]);self.rebuild();self.owner.finish_change()
        else:self.owner.edit_requested.emit(self.data['id'])
        event.accept()

class DiagramScene(QGraphicsScene):
    edit_requested=Signal(str)
    changed=Signal()
    def __init__(self,doc):super().__init__();self.doc=doc;self.nodes={};self.edges={};self.loading=False;self.exporting=False;self.reload()
    def reload(self,selection=()):
        self.loading=True;self.clear();self.nodes={};self.edges={};p=self.doc.page;layers={l['id']:l for l in p['layers']};order={l['id']:i*10000 for i,l in enumerate(p['layers'])}
        for n in p['nodes']:
            if not layers[n['layer']]['visible']:continue
            item=NodeItem(self,n,layers[n['layer']]);self.nodes[n['id']]=item;self.addItem(item);item.setZValue(order[n['layer']]+n.get('z',0));item.setSelected(n['id'] in selection)
        for e in p['edges']:
            if not layers[e['layer']]['visible'] or e['source'] not in self.nodes or e['target'] not in self.nodes:continue
            item=EdgeItem(self,e);self.edges[e['id']]=item;self.addItem(item);item.setZValue(order[e['layer']]+e.get('z',-1));item.setSelected(e['id'] in selection)
        self.setSceneRect(QRectF(-100,-100,p['width']+200,p['height']+200).united(self.itemsBoundingRect().adjusted(-80,-80,80,80)));self.loading=False
    def update_edges(self):
        if not self.loading:
            for edge in self.edges.values():edge.rebuild(False)
    def finish_change(self):self.doc.commit();self.changed.emit()
    def selected_ids(self):return [i.data['id'] for i in self.selectedItems() if isinstance(i,(NodeItem,EdgeItem))]
    def drawBackground(self,p,rect):
        page=self.doc.page;paper=QRectF(0,0,page['width'],page['height'])
        if not self.exporting:
            p.fillRect(rect,QColor('#121b26'))
            wallpaper=getattr(self,'wallpaper',None)
            if wallpaper is not None and not wallpaper.isNull():
                view=self.views()[0] if self.views() else None
                target=view.mapToScene(view.viewport().rect()).boundingRect() if view else rect
                p.save();p.setOpacity(getattr(self,'wallpaper_opacity',1));source=QRectF(wallpaper.rect());factor=max(target.width()/source.width(),target.height()/source.height());source.setSize(target.size()/factor);source.moveCenter(QRectF(wallpaper.rect()).center());p.drawPixmap(target,wallpaper,source);p.restore()
        if not (self.exporting and getattr(self,'transparent_export',False)):p.fillRect(paper,QColor(page['background']))
        if page['grid'] and not self.exporting:
            r=rect.intersected(paper);step=page['grid_size'];p.setPen(QPen(QColor('#dce4e8'),0))
            for x in range(int(r.left()//step)*step,int(r.right())+1,step):
                for y in range(int(r.top()//step)*step,int(r.bottom())+1,step):p.drawPoint(QPointF(x,y))

class DiagramView(QGraphicsView):
    add_requested=Signal(str,object)
    connect_requested=Signal(str,str)
    ports_connected=Signal(str,str,str,str)
    zoom_changed=Signal(int)
    def __init__(self,scene):
        super().__init__(scene);self.setRenderHints(QPainter.RenderHint.Antialiasing|QPainter.RenderHint.TextAntialiasing|QPainter.RenderHint.SmoothPixmapTransform);self.setDragMode(QGraphicsView.DragMode.RubberBandDrag);self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse);self.setAcceptDrops(True);self.connecting=False;self.source=None;self.pan=None;self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    def begin_link(self,node,side):
        self.cancel_link();self.link_source=(node,side);self.link_preview=QGraphicsPathItem();self.link_preview.setPen(QPen(QColor('#4c9aff'),2));self.link_preview.setZValue(1e9);self.scene().addItem(self.link_preview)
    def cancel_link(self):
        preview=getattr(self,'link_preview',None)
        if preview is not None and preview.scene():self.scene().removeItem(preview)
        self.link_preview=None;self.link_source=None;self.link_target=None;self.viewport().update()
    def snap_port(self,point):
        choices=[];radius=26/max(.05,self.transform().m11())
        for n in self.scene().nodes.values():
            if n is self.link_source[0] or n.locked:continue
            for side in ('left','right','top','bottom'):
                anchor=n.anchor(point,side);distance=(anchor-point).manhattanLength()
                if distance<=radius:choices.append((distance,n,side,anchor))
        return min(choices,key=lambda x:x[0])[1:] if choices else None
    def move_link(self,point):
        if not getattr(self,'link_source',None):return
        n,side=self.link_source;self.link_target=self.snap_port(point);end=self.link_target[2] if self.link_target else point
        path=QPainterPath(n.anchor(point,side));path.lineTo(end);self.link_preview.setPath(path);self.viewport().update()
    def finish_link(self,point):
        self.move_link(point);source=self.link_source;target=self.link_target;self.cancel_link()
        if source:
            for port in source[0].ports.values():port.hide()
        if source and target:
            from PySide6.QtCore import QTimer
            args=(source[0].data['id'],target[0].data['id'],source[1],target[1]);QTimer.singleShot(0,lambda:self.ports_connected.emit(*args))
    def drawForeground(self,p,rect):
        super().drawForeground(p,rect)
        if getattr(self,'link_source',None):
            for n in self.scene().nodes.values():
                if n is self.link_source[0]:continue
                p.setPen(QPen(QColor('#4c9aff'),1));p.setBrush(QColor('#c8e8ff'))
                for side in ('left','right','top','bottom'):p.drawEllipse(n.anchor(QPointF(),side),5,5)
            if self.link_target:p.setBrush(QColor('#63e6be'));p.drawEllipse(self.link_target[2],9,9)
            path=self.link_preview.path()
            if path.length()>1:marker(p,path.pointAtPercent(1),path.pointAtPercent(.95),'arrow',QColor('#4c9aff'))
    def zoom(self,value):
        value=max(5,min(800,value));self.resetTransform();self.scale(value/100,value/100);self.zoom_changed.emit(round(value))
    def wheelEvent(self,event):
        if event.modifiers()&Qt.KeyboardModifier.ControlModifier:self.zoom(self.transform().m11()*100*(1.15 if event.angleDelta().y()>0 else 1/1.15));event.accept()
        else:super().wheelEvent(event)
    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.MiddleButton:self.pan=event.position();self.setCursor(Qt.CursorShape.ClosedHandCursor);event.accept();return
        if self.connecting and event.button()==Qt.MouseButton.LeftButton:
            item=self.itemAt(event.position().toPoint())
            while item and not isinstance(item,NodeItem):item=item.parentItem()
            if item:
                if self.source:self.connect_requested.emit(self.source,item.data['id']);self.source=None
                else:self.source=item.data['id'];item.setSelected(True)
            event.accept();return
        super().mousePressEvent(event)
    def mouseMoveEvent(self,event):
        if self.pan is not None:
            delta=event.position()-self.pan;self.pan=event.position();self.horizontalScrollBar().setValue(self.horizontalScrollBar().value()-round(delta.x()));self.verticalScrollBar().setValue(self.verticalScrollBar().value()-round(delta.y()));event.accept()
        else:super().mouseMoveEvent(event)
    def mouseReleaseEvent(self,event):
        if self.pan is not None:self.pan=None;self.unsetCursor();event.accept()
        else:super().mouseReleaseEvent(event)
    def dragEnterEvent(self,event):
        if event.mimeData().hasFormat('application/x-redrawko-shape'):event.acceptProposedAction()
        else:event.ignore()
    def dragMoveEvent(self,event):self.dragEnterEvent(event)
    def dropEvent(self,event):
        if event.mimeData().hasFormat('application/x-redrawko-shape'):
            shape=bytes(event.mimeData().data('application/x-redrawko-shape')).decode();self.add_requested.emit(shape,self.mapToScene(event.position().toPoint()));event.acceptProposedAction()
        else:event.ignore()
    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_Escape:self.cancel_link();self.source=None;self.scene().clearSelection();event.accept()
        elif event.key() in (Qt.Key.Key_Left,Qt.Key.Key_Right,Qt.Key.Key_Up,Qt.Key.Key_Down):
            scene=self.scene();step=scene.doc.page['grid_size'] if scene.doc.page['snap'] else 1
            if event.modifiers()&Qt.KeyboardModifier.ShiftModifier:step*=5
            dx,dy={Qt.Key.Key_Left:(-step,0),Qt.Key.Key_Right:(step,0),Qt.Key.Key_Up:(0,-step),Qt.Key.Key_Down:(0,step)}[event.key()]
            scene.doc.begin()
            for item in scene.selectedItems():
                if isinstance(item,NodeItem) and not item.locked:item.setPos(item.pos()+QPointF(dx,dy))
            scene.finish_change();event.accept()
        else:super().keyPressEvent(event)
