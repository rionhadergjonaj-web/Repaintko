"""Lossless, conflict-checked pixel transactions for the normal Paint editor."""
import base64,io,json,uuid,hashlib
from PIL import Image,ImageChops
from document import Document
from effects import EFFECTS

FIELDS=('name','visible','opacity','stack')
def clone(doc):
    out=Document(doc.image.size)
    out.layers=[dict(e,image=e['image'].copy(),base=e['base'].copy() if e.get('base') is not None else None) for e in doc.layers]
    out.active=doc.active;out.revision=doc.revision;out.next_revision=doc.revision
    return out

def identify(doc):
    used=set()
    for e in doc.layers:
        if e.get('_shared_id') in used or not e.get('_shared_id'):e['_shared_id']=uuid.uuid4().hex
        used.add(e['_shared_id'])

def meta(e):return json.loads(json.dumps({k:e[k] for k in FIELDS}))
def encode(im):
    if im is None:return None
    stream=io.BytesIO();im.save(stream,'PNG',compress_level=1)
    return base64.b64encode(stream.getvalue()).decode('ascii')
def decode(value,size):
    if not isinstance(value,str):raise ValueError('Ungültige Bilddaten.')
    with Image.open(io.BytesIO(base64.b64decode(value,validate=True))) as im:
        if im.format!='PNG' or im.size!=tuple(size):raise ValueError('Ungültige Bildgröße.')
        return im.convert('RGBA')
def difference(a,b):
    bands=ImageChops.difference(a.convert('RGBA'),b.convert('RGBA')).split()
    mask=bands[0]
    for band in bands[1:]:mask=ImageChops.lighter(mask,band)
    return mask.point(lambda x:255 if x else 0)
def signature(doc):
    digest=hashlib.sha256()
    digest.update(json.dumps([doc.image.size,doc.paper_color,doc.paper_opacity]).encode())
    for e in doc.layers:
        digest.update(e['_shared_id'].encode());digest.update(json.dumps(meta(e),sort_keys=True).encode())
        for k in ('image','base'):
            digest.update(e[k].convert('RGBA').tobytes() if e.get(k) is not None else b'none')
    return digest.hexdigest()
def snapshot(doc):
    return dict(size=list(doc.image.size),paper=doc.paper_color,paper_opacity=doc.paper_opacity,
                layers=[dict(meta(e),id=e['_shared_id'],png=encode(e['image']),base=encode(e.get('base'))) for e in doc.layers],revision=0)

def prepare(before,after,boxes=None):
    """Crop on the GUI thread; compression is performed later by a worker.

    Brush bounds avoid scanning/copying the entire image on each mouse move.
    The baseline is advanced only for the pixels included in this transaction.
    """
    identify(after)
    if before.image.size!=after.image.size or [e['_shared_id'] for e in before.layers]!=[e['_shared_id'] for e in after.layers]:
        return {'kind':'edit','replacement':(clone(before),clone(after))},clone(after)
    changes=[]
    for a,b in zip(before.layers,after.layers):
        key=a['_shared_id'];fields={};pixels=[]
        guard=None
        if meta(a)['stack']!=meta(b)['stack'] or (a.get('base') is None)!=(b.get('base') is None):
            guard={side:hashlib.sha256(entry['image'].convert('RGBA').tobytes()).hexdigest() for side,entry in [('before',a),('after',b)]}
        if meta(a)!=meta(b):fields={'before':meta(a),'after':meta(b)}
        for field in ('image','base'):
            old,new=a.get(field),b.get(field)
            if old is None and new is None:continue
            if (old is None)!=(new is None):
                pixels.append(dict(field=field,box=None,before=old.copy() if old is not None else None,after=new.copy() if new is not None else None))
                a[field]=new.copy() if new is not None else None;continue
            if boxes is not None and key not in boxes:continue
            box=boxes[key] if boxes is not None else (0,0,*new.size)
            left=old.crop(box).convert('RGBA');right=new.crop(box).convert('RGBA');bounds=difference(left,right).getbbox()
            if not bounds:continue
            x,y,r,bottom=bounds;actual=[box[0]+x,box[1]+y,box[0]+r,box[1]+bottom]
            pixels.append(dict(field=field,box=actual,before=left.crop(bounds),after=right.crop(bounds)))
            a[field].paste(new.crop(actual),actual[:2])
        if fields or pixels:changes.append(dict(layer=key,fields=fields,pixels=pixels,guard=guard))
        for k in FIELDS:a[k]=b[k]
    paper=None
    if (before.paper_color,before.paper_opacity)!=(after.paper_color,after.paper_opacity):
        paper={'before':[before.paper_color,before.paper_opacity],'after':[after.paper_color,after.paper_opacity]}
        before.layers[0]['paper_color']=after.paper_color;before.layers[0]['paper_opacity']=after.paper_opacity
    return (dict(kind='edit',changes=changes,paper=paper) if changes or paper else None),before

def compress(op):
    if 'replacement' in op:
        a,b=op['replacement'];return dict(kind='edit',replacement={'before':snapshot(a),'after':snapshot(b),'signature':signature(a)})
    for c in op['changes']:
        for p in c['pixels']:p['before']=encode(p['before']);p['after']=encode(p['after'])
    return op
def inverse(op):
    out=json.loads(json.dumps(op))
    if 'replacement' in out:
        from draw_state import SharedDrawing
        r=out['replacement'];r['before'],r['after']=r['after'],r['before'];r['signature']=signature(SharedDrawing.restore(r['before']).doc)
    else:
        for c in out['changes']:
            if c.get('guard'):c['guard']['before'],c['guard']['after']=c['guard']['after'],c['guard']['before']
            for p in c['pixels']:p['before'],p['after']=p['after'],p['before']
            if c['fields']:c['fields']['before'],c['fields']['after']=c['fields']['after'],c['fields']['before']
        if out['paper']:out['paper']['before'],out['paper']['after']=out['paper']['after'],out['paper']['before']
    return out

def valid_meta(value,size):
    if set(value)!=set(FIELDS) or not isinstance(value['name'],str) or len(value['name'])>100 or type(value['visible']) is not bool or type(value['opacity']) is not int or not 0<=value['opacity']<=100:raise ValueError('Ungültige Ebeneneinstellungen.')
    stack=value['stack']
    if not isinstance(stack,list) or len(stack)>len(EFFECTS):raise ValueError('Ungültige Effekte.')
    seen=set()
    for item in stack:
        if not isinstance(item,list) or len(item)!=3 or item[0] not in EFFECTS or item[0] in seen or not isinstance(item[1],(int,float)) or not EFFECTS[item[0]].minimum<=item[1]<=EFFECTS[item[0]].maximum:raise ValueError('Ungültiger Fotoeffekt.')
        seen.add(item[0]);box=item[2]
        if len(box)!=4 or not all(type(n) is int for n in box) or not 0<=box[0]<box[2]<=size[0] or not 0<=box[1]<box[3]<=size[1]:raise ValueError('Ungültiger Effektbereich.')
    return dict(value,stack=tuple((v[0],v[1],tuple(v[2])) for v in stack))

def apply_edit(state,op,dry_run=False):
    """Validate everything before touching shared pixels. No blind layer replacement."""
    from draw_state import SharedDrawing
    conflict='Gleichzeitige Änderung an derselben Stelle. Dein Entwurf bleibt erhalten; bitte erneut synchronisieren.'
    if 'replacement' in op:
        r=op['replacement']
        if signature(state.doc)!=r['signature']:raise ValueError(conflict)
        restored=SharedDrawing.restore(r['after']);state.doc=restored.doc;state.size=restored.size;state.ids=restored.ids
        return
    changes=op.get('changes');paper=op.get('paper')
    if not isinstance(changes,list) or len(changes)>32:raise ValueError('Ungültige Änderungen.')
    prepared=[];seen=set()
    for c in changes:
        key=c['layer']
        if key in seen or key not in state.ids:raise ValueError(conflict)
        seen.add(key);entry=state.doc.layers[state.ids.index(key)];fields=c['fields'];updates=[]
        if c.get('guard') and hashlib.sha256(entry['image'].convert('RGBA').tobytes()).hexdigest()!=c['guard']['before']:raise ValueError(conflict)
        if fields:
            if meta(entry)!=fields['before']:raise ValueError(conflict)
            fields=valid_meta(fields['after'],state.size)
        if not isinstance(c['pixels'],list) or len(c['pixels'])>2:raise ValueError('Ungültige Pixeländerung.')
        seen_fields=set()
        for p in c['pixels']:
            field=p['field'];box=p['box']
            if field not in ('image','base') or field in seen_fields:raise ValueError('Ungültiges Bildfeld.')
            seen_fields.add(field);current=entry.get(field)
            if box is None:
                old=decode(p['before'],state.size) if p['before'] is not None else None
                new=decode(p['after'],state.size) if p['after'] is not None else None
                if field=='image' and new is None:raise ValueError('Ebenenbild fehlt.')
                if (old is None)!=(current is None) or (old is not None and difference(old,current).getbbox()):raise ValueError(conflict)
                updates.append((field,None,new,None));continue
            if not isinstance(box,list) or len(box)!=4 or not all(type(n) is int for n in box) or not 0<=box[0]<box[2]<=state.size[0] or not 0<=box[1]<box[3]<=state.size[1] or current is None:raise ValueError('Ungültiger Pixelbereich.')
            size=(box[2]-box[0],box[3]-box[1]);old=decode(p['before'],size);new=decode(p['after'],size);mask=difference(old,new)
            if ImageChops.multiply(difference(current.crop(box),old),mask).getbbox():raise ValueError(conflict)
            updates.append((field,box,new,mask))
        prepared.append((entry,fields,updates))
    if paper:
        if [state.doc.paper_color,state.doc.paper_opacity]!=paper['before']:raise ValueError(conflict)
        from PIL import ImageColor
        color,opacity=paper['after'];ImageColor.getrgb(color)
        if type(opacity) is not int or not 0<=opacity<=100:raise ValueError('Ungültige Blattdeckkraft.')
    if dry_run:return
    for entry,fields,updates in prepared:
        if fields:entry.update(fields)
        for field,box,new,mask in updates:
            if box is None:entry[field]=new
            else:entry[field].paste(new,box[:2],mask)
    if paper:state.doc.layers[0]['paper_color'],state.doc.layers[0]['paper_opacity']=paper['after']
