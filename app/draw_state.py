"""Deterministic DrawTogether state. Stable layer IDs, server-ordered operations."""
import base64,io,re,uuid
from PIL import Image,ImageDraw,ImageChops,ImageOps
from document import Document
from layers import layer
MAX_PIXELS=16_000_000
MAX_LAYER_PIXELS=64_000_000

def integer(value,lo,hi):
    if type(value) is not int or not lo<=value<=hi:raise ValueError('Zahl außerhalb des erlaubten Bereichs.')
    return value

def name(value):
    if not isinstance(value,str):raise ValueError('Ungültiger Name.')
    return ''.join(c for c in value if c.isprintable()).strip()[:80] or 'Ebene'

class SharedDrawing:
    def __init__(self,document=None,size=(1920,1080)):
        self.doc=Document(size) if document is None else document
        self.size=self.doc.image.size;w,h=self.size
        if w*h>MAX_PIXELS or w*h*len(self.doc.layers)>MAX_LAYER_PIXELS:raise ValueError('DrawTogether: maximal 16 Millionen Pixel pro Blatt und 64 Millionen Ebenenpixel.')
        self.ids=[uuid.uuid4().hex for _ in self.doc.layers];self.revision=0
        for key,entry in zip(self.ids,self.doc.layers):entry['image']=entry['image'].convert('RGBA');entry['_shared_id']=key
    def metadata(self):return [{'id':key,'name':e['name'],'visible':e['visible'],'opacity':e['opacity']} for key,e in zip(self.ids,self.doc.layers)]
    def export(self):
        from draw_edits import snapshot
        result=snapshot(self.doc);result['revision']=self.revision;return result
    def legacy_export(self):
        records=self.metadata()
        for record,e in zip(records,self.doc.layers):
            stream=io.BytesIO();e['image'].save(stream,'PNG',compress_level=1);record['png']=base64.b64encode(stream.getvalue()).decode('ascii')
        return {'size':list(self.size),'layers':records,'paper':self.doc.paper_color,'paper_opacity':self.doc.paper_opacity,'revision':self.revision}
    @classmethod
    def restore(cls,data):
        w,h=data['size'];integer(w,1,16384);integer(h,1,16384);records=data['layers']
        if w*h>MAX_PIXELS or not 1<=len(records)<=32 or w*h*len(records)>MAX_LAYER_PIXELS:raise ValueError('Ungültige Größe der gemeinsamen Zeichnung.')
        doc=Document((w,h));entries=[];ids=[]
        for r in records:
            key=r['id']
            if not isinstance(key,str) or not re.fullmatch(r'[0-9a-f]{32}',key) or key in ids:raise ValueError('Ungültige Ebenenkennung.')
            raw=base64.b64decode(r['png'],validate=True)
            with Image.open(io.BytesIO(raw)) as im:
                if im.size!=(w,h) or im.format!='PNG':raise ValueError('Ungültige Ebenenpixel.')
                e=layer(im.convert('RGBA'),name(r['name']))
            e['opacity']=integer(r['opacity'],0,100);e['visible']=bool(r['visible']);entries.append(e);ids.append(key)
            from draw_edits import decode,valid_meta
            if r.get('base') is not None:e['base']=decode(r['base'],(w,h))
            if 'stack' in r:e.update(valid_meta({k:r[k] for k in ('name','visible','opacity','stack')},(w,h)))
        if not isinstance(data['paper'],str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',data['paper']):raise ValueError('Ungültige Blattfarbe.')
        doc.layers=entries;doc.layers[0]['paper_color']=data['paper'];doc.layers[0]['paper_opacity']=integer(data['paper_opacity'],0,100)
        state=cls(doc);state.ids=ids
        for key,e in zip(ids,state.doc.layers):e['_shared_id']=key
        state.revision=integer(data['revision'],0,2**53);return state
    def normalize(self,op):
        if not isinstance(op,dict):raise ValueError('Ungültige Aktion.')
        kind=op.get('kind');key=op.get('layer')
        if kind in ('edit','batch'):return op
        if kind=='add':
            if len(self.ids)>=32 or self.size[0]*self.size[1]*(len(self.ids)+1)>MAX_LAYER_PIXELS:raise ValueError('Ebenenlimit erreicht.')
            return {'kind':'add','id':uuid.uuid4().hex,'name':name(op.get('name','Neue Ebene'))}
        if key not in self.ids:raise ValueError('Diese Ebene wurde inzwischen gelöscht.')
        index=self.ids.index(key)
        if kind=='stroke':
            pts=op.get('points');width=integer(op.get('width'),1,200);opacity=integer(op.get('opacity'),1,100);color=op.get('color');tool=op.get('tool')
            if tool not in ('Pinsel','Radierer','Linie','Füller'):raise ValueError('Unbekanntes Werkzeug.')
            if not isinstance(color,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',color):raise ValueError('Ungültige Farbe.')
            if not isinstance(pts,list) or not 1<=len(pts)<=64:raise ValueError('Zu viele Punkte.')
            clean=[]
            for p in pts:
                if not isinstance(p,list) or len(p)!=2:raise ValueError('Ungültiger Punkt.')
                clean.append([integer(p[0],0,self.size[0]-1),integer(p[1],0,self.size[1]-1)])
            if not self.doc.layers[index]['visible']:raise ValueError('Die Ebene ist ausgeblendet.')
            return dict(kind=kind,layer=key,points=clean,width=width,opacity=opacity,color=color,tool=tool)
        if kind=='delete':
            if len(self.ids)==1:raise ValueError('Mindestens eine Ebene muss bleiben.')
            return dict(kind=kind,layer=key)
        if kind=='rename':return dict(kind=kind,layer=key,name=name(op.get('name')))
        if kind=='visible':
            if type(op.get('value')) is not bool:raise ValueError('Ungültige Sichtbarkeit.')
            return dict(kind=kind,layer=key,value=op['value'])
        if kind=='opacity':return dict(kind=kind,layer=key,value=integer(op.get('value'),0,100))
        if kind=='move':return dict(kind=kind,layer=key,offset=integer(op.get('offset'),-1,1))
        raise ValueError('Unbekannte Aktion.')
    def apply(self,op):
        if op.get('kind')=='edit':
            from draw_edits import apply_edit
            apply_edit(self,op);self.revision+=1;self.doc.revision=self.revision;return
        if op.get('kind')=='batch':
            from draw_edits import clone
            ops=op.get('ops')
            if not isinstance(ops,list) or not 1<=len(ops)<=2048 or any(not isinstance(e,dict) or e.get('kind')!='edit' for e in ops):raise ValueError('Ungültiger Verlauf.')
            draft=SharedDrawing(clone(self.doc));draft.ids=list(self.ids)
            for key,e in zip(draft.ids,draft.doc.layers):e['_shared_id']=key
            for entry in ops:draft.apply(entry)
            self.doc,self.ids,self.size=draft.doc,draft.ids,draft.size;self.revision+=1;self.doc.revision=self.revision;return
        validated=self.normalize(op)
        if validated['kind']=='add':
            key=op.get('id')
            if not isinstance(key,str) or not re.fullmatch(r'[0-9a-f]{32}',key) or key in self.ids:raise ValueError('Ungültige neue Ebenenkennung.')
            validated['id']=key
        op=validated
        kind=op['kind'];paper=self.doc.paper_color;paper_opacity=self.doc.paper_opacity
        if kind=='add':self.ids.append(op['id']);self.doc.layers.append(dict(layer(Image.new('RGBA',self.size),op['name']),_shared_id=op['id']))
        else:
            i=self.ids.index(op['layer']);e=self.doc.layers[i]
            if kind=='stroke':
                points=[tuple(p) for p in op['points']];width=op['width'];pad=width+2
                box=(max(0,min(p[0] for p in points)-pad),max(0,min(p[1] for p in points)-pad),min(self.size[0],max(p[0] for p in points)+pad+1),min(self.size[1],max(p[1] for p in points)+pad+1))
                points=[(x-box[0],y-box[1]) for x,y in points];mask=Image.new('L',(box[2]-box[0],box[3]-box[1]));pen=ImageDraw.Draw(mask);alpha=round(op['opacity']*255/100)
                if op['tool']=='Füller':
                    dx=width*.35;dy=-dx;thin=max(1,width*.07)
                    corners=[(-dx-thin,-dy-thin),(dx-thin,dy-thin),(dx+thin,dy+thin),(-dx+thin,-dy+thin)]
                    prev=None
                    for x,y in points:
                        now=[(x+a,y+b) for a,b in corners];pen.polygon(now,fill=alpha)
                        if prev:
                            for j in range(4):pen.polygon([prev[j],prev[(j+1)%4],now[(j+1)%4],now[j]],fill=alpha)
                        prev=now
                else:
                    pen.line(points,fill=alpha,width=width,joint='curve');radius=(width-1)/2
                    for x,y in points:pen.ellipse((x-radius,y-radius,x+radius,y+radius),fill=alpha)
                original=e['image'].crop(box)
                if op['tool']=='Radierer':original.putalpha(ImageChops.multiply(original.getchannel('A'),ImageOps.invert(mask)));result=original
                else:
                    paint=Image.new('RGBA',original.size,op['color']);paint.putalpha(mask);result=Image.alpha_composite(original,paint)
                e['image'].paste(result,box[:2])
            elif kind=='delete':self.ids.pop(i);self.doc.layers.pop(i)
            elif kind=='rename':e['name']=op['name']
            elif kind in ('visible','opacity'):e[kind]=op['value']
            elif kind=='move':
                j=max(0,min(len(self.ids)-1,i+op['offset']));self.ids.insert(j,self.ids.pop(i));self.doc.layers.insert(j,self.doc.layers.pop(i))
        self.doc.active=0;self.doc.layers[0]['paper_color']=paper;self.doc.layers[0]['paper_opacity']=paper_opacity;self.revision+=1;self.doc.revision=self.revision
