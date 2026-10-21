"""Native ReDrawko documents. No browser, web editor or network dependency."""
import copy,json,math,uuid,os,tempfile
from pathlib import Path

SHAPES={
 'entity':('ERM-Tabelle','ERM & UML'), 'weak_entity':('Schwache Entität','ERM & UML'),
 'attribute':('Attribut','ERM & UML'),'key_attribute':('Schlüsselattribut','ERM & UML'),
 'relationship':('Beziehung','ERM & UML'),'class':('UML-Klasse','ERM & UML'),
 'actor':('Akteur','ERM & UML'),'usecase':('Anwendungsfall','ERM & UML'),
 'rect':('Rechteck','Grundformen'),'rounded':('Abgerundet','Grundformen'),
 'ellipse':('Ellipse','Grundformen'),'diamond':('Raute','Grundformen'),
 'triangle':('Dreieck','Grundformen'),'hexagon':('Sechseck','Grundformen'),
 'pentagon':('Fünfeck','Grundformen'),'star':('Stern','Grundformen'),
 'cloud':('Wolke','Grundformen'),'text':('Text','Grundformen'),
 'process':('Prozess','Flussdiagramm'),'decision':('Entscheidung','Flussdiagramm'),
 'terminator':('Start / Ende','Flussdiagramm'),'data':('Daten','Flussdiagramm'),
 'document':('Dokument','Flussdiagramm'),'database':('Datenbank','Flussdiagramm'),
 'subprocess':('Unterprozess','Flussdiagramm'),'note':('Notiz','Flussdiagramm'),
 'swimlane':('Schwimmbahn','Flussdiagramm'),'delay':('Verzögerung','Flussdiagramm'),
 'server':('Server','Netzwerk'),'computer':('Computer','Netzwerk'),
 'router':('Router','Netzwerk'),'image':('Bild','Medien'),
 'arrow':('Blockpfeil','Grundformen')}
def uid():return uuid.uuid4().hex
def layer(name='Ebene 1'):return dict(id=uid(),name=name,visible=True,locked=False)
def page(name='Seite 1'):
    l=layer();return dict(id=uid(),name=name,width=1600,height=1000,background='#ffffff',grid=True,snap=True,grid_size=20,layers=[l],active_layer=l['id'],nodes=[],edges=[])
def document():
    p=page();return dict(format='ReDrawko',version=1,pages=[p],active_page=p['id'])
def node(shape,x,y,layer_id):
    return dict(id=uid(),shape=shape,x=x,y=y,w=220 if shape in ('entity','class') else 160,h=136 if shape in ('entity','class') else 90,
                text=SHAPES.get(shape,('Form',))[0],layer=layer_id,fill='#e7f6f1',stroke='#344b55',text_color='#172033',line_width=2,
                font='Segoe UI',font_size=15,bold=False,italic=False,align='center',opacity=100,rotation=0,dashed=False,z=0,group='',locked=False,link='',data={},
                rows=[dict(name='id',type='INTEGER',key='PK',nullable=False),dict(name='name',type='VARCHAR(100)',key='',nullable=False)] if shape=='entity' else [],image='')
def edge(source,target,layer_id):
    return dict(id=uid(),source=source,target=target,layer=layer_id,text='',source_label='',target_label='',stroke='#344b55',line_width=2,
                font_size=13,text_color='#172033',route='orthogonal',start='none',end='arrow',dashed=False,source_port='auto',target_port='auto',points=[],opacity=100,z=-1,label_x=0,label_y=0)

def validate(data):
    if not isinstance(data,dict) or data.get('format')!='ReDrawko' or data.get('version')!=1:raise ValueError('Keine unterstützte ReDrawko-Datei.')
    pages=data.get('pages',[])
    if not 1<=len(pages)<=100:raise ValueError('1 bis 100 Seiten sind erlaubt.')
    ids=set();count=0
    def identity(obj):
        key=obj.get('id')
        if not isinstance(key,str) or not key or len(key)>150 or key in ids:raise ValueError('Ungültige oder doppelte Objektkennung.')
        ids.add(key)
    def number(v,lo,hi):
        if not isinstance(v,(int,float)) or not math.isfinite(v) or not lo<=v<=hi:raise ValueError('Ungültige Objektgröße oder Position.')
    def text(obj,key,limit=100000):
        if not isinstance(obj.get(key),str) or len(obj[key])>limit:raise ValueError('Ungültiger Text: '+key)
    for p in pages:
        identity(p);number(p['width'],100,50000);number(p['height'],100,50000);number(p.get('grid_size',20),5,200)
        text(p,'name');text(p,'background',100)
        if not 1<=len(p['layers'])<=100:raise ValueError('Ungültige Ebenenanzahl.')
        for l in p['layers']:identity(l);text(l,'name')
        layers={l['id'] for l in p['layers']}
        if p['active_layer'] not in layers:raise ValueError('Aktive Ebene fehlt.')
        nodes={n['id'] for n in p['nodes']};count+=len(nodes)+len(p['edges'])
        for n in p['nodes']:
            identity(n)
            if n['shape'] not in SHAPES or n['layer'] not in layers:raise ValueError('Unbekannte Form oder Ebene.')
            for k in ('x','y'):number(n[k],-100000,100000)
            for k in ('w','h'):number(n[k],20,50000)
            number(n.get('rotation',0),-36000,36000);number(n.get('opacity',100),0,100);number(n.get('font_size',15),5,300);number(n.get('line_width',2),.1,30)
            if len(n.get('text',''))>100000 or len(n.get('rows',[]))>1000 or len(n.get('image',''))>40_000_000:raise ValueError('Objektinhalt zu groß.')
            for key in ('text','fill','stroke','text_color','font','align','group','link'):text(n,key)
            for row in n.get('rows',[]):
                for key in ('name','type','key'):text(row,key)
            if n['align'] not in ('left','center','right'):raise ValueError('Ungültige Textausrichtung.')
            number(n.get('z',0),-100000,100000)
        for e in p['edges']:
            identity(e)
            if e['source'] not in nodes or e['target'] not in nodes or e['layer'] not in layers:raise ValueError('Verbindung ohne passende Objekte.')
            if e.get('route') not in ('straight','orthogonal','curved'):raise ValueError('Ungültige Linienart.')
            if len(e.get('points',[]))>1000:raise ValueError('Zu viele Wegpunkte.')
            for point in e.get('points',[]):
                if len(point)!=2:raise ValueError('Ungültiger Wegpunkt.')
                for value in point:number(value,-100000,100000)
            number(e.get('line_width',2),.1,30);number(e.get('font_size',13),5,300);number(e.get('opacity',100),0,100)
            for key in ('text','source_label','target_label','stroke','text_color'):text(e,key)
            for key in ('start','end'):
                if e.get(key) not in ('none','arrow','open','diamond','circle','one','many','zero_one','zero_many'):raise ValueError('Ungültige Pfeilart.')
            for key in ('label_x','label_y','z'):number(e.get(key,0),-100000,100000)
    if count>20000:raise ValueError('Maximal 20.000 Diagrammobjekte.')
    if data['active_page'] not in {p['id'] for p in pages}:raise ValueError('Aktive Seite fehlt.')
    return data

def atomic_write(path,data):
    path=Path(path);fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

class DiagramDocument:
    def __init__(self):self.data=document();self.path=None;self.undo=[];self.redo=[];self.saved=self.serial();self.pending=None
    @property
    def page(self):return next(p for p in self.data['pages'] if p['id']==self.data['active_page'])
    def serial(self):return json.dumps(self.data,ensure_ascii=False,separators=(',',':'))
    @property
    def dirty(self):return self.serial()!=self.saved
    def begin(self):
        if self.pending is None:self.pending=self.serial()
    def commit(self):
        old=self.pending;self.pending=None
        if old is not None and old!=self.serial():
            self.undo.append(old);self.redo.clear()
            while len(self.undo)>1 and (len(self.undo)>200 or sum(map(len,self.undo))>100_000_000):self.undo.pop(0)
    def change(self,fn):
        self.begin()
        try:fn();validate(self.data);self.commit()
        except Exception:
            if self.pending is not None:self.data=json.loads(self.pending);self.pending=None
            raise
    def history(self,redo=False):
        self.commit();source=self.redo if redo else self.undo;target=self.undo if redo else self.redo
        if source:target.append(self.serial());self.data=json.loads(source.pop())
    def save(self,path):
        validate(self.data);raw=self.serial();atomic_write(path,raw.encode('utf-8'));self.saved=raw;self.path=str(path)
    def load(self,path):
        path=Path(path)
        if path.stat().st_size>100_000_000:raise ValueError('Diagrammdatei zu groß.')
        data=validate(json.loads(path.read_text(encoding='utf-8-sig')))
        self.data=data;self.path=str(path);self.undo=[];self.redo=[];self.pending=None;self.saved=self.serial()
    def delete(self,keys):
        p=self.page;p['nodes']=[n for n in p['nodes'] if n['id'] not in keys]
        p['edges']=[e for e in p['edges'] if e['id'] not in keys and e['source'] not in keys and e['target'] not in keys]
    def duplicate(self,keys,offset=30):
        p=self.page;mapping={n['id']:uid() for n in p['nodes'] if n['id'] in keys};groups={};new=[]
        for n in list(p['nodes']):
            if n['id'] not in mapping:continue
            c=copy.deepcopy(n);c['id']=mapping[n['id']];c['x']+=offset;c['y']+=offset
            if c.get('group'):c['group']=groups.setdefault(c['group'],uid())
            p['nodes'].append(c);new.append(c['id'])
        for e in list(p['edges']):
            if e['source'] in mapping and e['target'] in mapping:
                c=copy.deepcopy(e);c['id']=uid();c['source']=mapping[e['source']];c['target']=mapping[e['target']];c['points']=[[x+offset,y+offset] for x,y in c['points']];p['edges'].append(c);new.append(c['id'])
        return new

def template(key):
    d=document();p=d['pages'][0];l=p['active_layer']
    def n(shape,text,x,y):
        item=node(shape,x,y,l);item['text']=text;p['nodes'].append(item);return item
    def e(a,b,text='',start='none',end='arrow'):
        item=edge(a['id'],b['id'],l);item.update(text=text,start=start,end=end);p['edges'].append(item);return item
    if key=='erm':
        a=n('entity','Kunde',140,200);b=n('entity','Bestellung',540,200);c=n('entity','Position',940,200);z=n('entity','Produkt',940,540)
        a['rows']=[dict(name='kunde_id',type='INTEGER',key='PK',nullable=False),dict(name='name',type='VARCHAR(100)',key='',nullable=False),dict(name='email',type='VARCHAR(255)',key='UQ',nullable=True)]
        b['rows']=[dict(name='bestellung_id',type='INTEGER',key='PK',nullable=False),dict(name='kunde_id',type='INTEGER',key='FK',nullable=False),dict(name='datum',type='DATE',key='',nullable=False)]
        c['rows']=[dict(name='position_id',type='INTEGER',key='PK',nullable=False),dict(name='bestellung_id',type='INTEGER',key='FK',nullable=False),dict(name='produkt_id',type='INTEGER',key='FK',nullable=False),dict(name='menge',type='INTEGER',key='',nullable=False)]
        z['rows']=[dict(name='produkt_id',type='INTEGER',key='PK',nullable=False),dict(name='bezeichnung',type='VARCHAR(100)',key='',nullable=False),dict(name='preis',type='DECIMAL(10,2)',key='',nullable=False)]
        for v in (a,b,c,z):v['h']=42+26*len(v['rows'])
        e(a,b,'bestellt','one','many');e(b,c,'enthält','one','many');e(z,c,'erscheint in','one','many')
    elif key=='flow':
        a=n('terminator','Start',620,80);b=n('process','Eingabe prüfen',620,250);c=n('decision','Gültig?',620,440);x=n('process','Korrigieren',960,440);z=n('terminator','Ende',620,680)
        e(a,b);e(b,c);e(c,z,'Ja');e(c,x,'Nein');e(x,b)
    elif key=='uml':
        a=n('class','Person\nname: String\ngeburtsdatum: Date\n────────────\n+ getAlter(): int',180,200);b=n('class','Kunde\nkundennummer: int\n────────────\n+ bestellen()',620,200);e(b,a,'erbt von','none','open')
    elif key=='network':
        a=n('router','Router',620,350)
        for shape,text,x,y in [('cloud','Internet',620,80),('server','Server',220,350),('computer','Arbeitsplatz 1',1000,190),('computer','Arbeitsplatz 2',1000,510)]:e(a,n(shape,text,x,y),'','none','none')
    elif key=='mindmap':
        a=n('rounded','Meine Idee',620,400)
        for text,x,y in [('Ziele',240,160),('Aufgaben',1020,160),('Ressourcen',240,650),('Termine',1020,650)]:
            line=e(a,n('rounded',text,x,y));line['route']='curved'
    return d
