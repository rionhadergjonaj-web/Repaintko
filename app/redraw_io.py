"""Local diagram interchange, SQL schema generation and vector exports."""
import base64,copy,html,json,re,zlib
import xml.etree.ElementTree as ET
from urllib.parse import unquote
from pathlib import Path
from redraw_model import document,page,layer,node,edge,uid,validate,atomic_write

def plain(text):
    text=re.sub(r'<(?:br\s*/?|/div|/p|/tr)>','\n',str(text),flags=re.I)
    return html.unescape(re.sub('<[^>]+>','',text)).strip()
def xml_parse(raw):
    if len(raw)>50_000_000 or re.search(br'<!\s*(?:DOCTYPE|ENTITY)',raw,re.I):raise ValueError('Nicht unterstützte oder zu große XML-Datei.')
    return ET.fromstring(raw)
def drawio_import(path):
    raw=Path(path).read_bytes();root=xml_parse(raw);out=document();out['pages']=[];warnings=[]
    diagrams=list(root.findall('diagram')) if root.tag=='mxfile' else [root]
    if not diagrams:raise ValueError('Keine Diagrammseiten gefunden.')
    for diagram in diagrams:
        model=diagram if diagram.tag=='mxGraphModel' else diagram.find('mxGraphModel')
        if model is None:
            encoded=(diagram.text or '').strip()
            if encoded.startswith('<'):model=xml_parse(encoded.encode())
            else:
                decompressor=zlib.decompressobj(-15);data=decompressor.decompress(base64.b64decode(encoded,validate=True),50_000_001)
                if len(data)>50_000_000 or decompressor.unconsumed_tail:raise ValueError('Komprimierte Diagrammseite zu groß.')
                model=xml_parse(unquote(data.decode('utf-8')).encode())
        p=page(diagram.get('name','Seite '+str(len(out['pages'])+1)));p['width']=max(100,min(50000,float(model.get('pageWidth',1600))));p['height']=max(100,min(50000,float(model.get('pageHeight',1000))))
        cells={c.get('id'):c for c in model.findall('.//mxCell')};mapping={};layers={};p['layers']=[]
        for key,c in cells.items():
            if c.get('parent')=='0' and not c.get('vertex') and not c.get('edge'):
                l=layer(plain(c.get('value','Ebene')) or 'Ebene');l['visible']=c.get('visible','1')!='0';p['layers'].append(l);layers[key]=l['id']
        if not p['layers']:p['layers']=[layer()]
        p['active_layer']=p['layers'][0]['id']
        def origin(key,seen=None):
            seen=set() if seen is None else seen
            if key in seen:return 0,0
            seen.add(key);c=cells.get(key)
            if c is None or not c.get('vertex'):return 0,0
            g=c.find('mxGeometry');a,b=origin(c.get('parent'),seen)
            return a+float(g.get('x',0) if g is not None else 0),b+float(g.get('y',0) if g is not None else 0)
        def layer_for(c):
            seen=set();parent=c.get('parent')
            while parent in cells and parent not in seen:
                if parent in layers:return layers[parent]
                seen.add(parent);parent=cells[parent].get('parent')
            return p['active_layer']
        for key,c in cells.items():
            if c.get('vertex')!='1':continue
            g=c.find('mxGeometry')
            if g is None:continue
            style=dict(v.split('=',1) for v in c.get('style','').split(';') if '=' in v);rawstyle=c.get('style','');shape=style.get('shape','rect')
            mapping_shape={'rhombus':'diamond','cylinder':'database','umlActor':'actor','swimlane':'swimlane','parallelogram':'data','process':'subprocess','note':'note','cloud':'cloud','hexagon':'hexagon','triangle':'triangle','ellipse':'ellipse','rectangle':'rect','mxgraph.er.entity':'entity'}
            shape=mapping_shape.get(shape,shape)
            from redraw_model import SHAPES
            if 'ellipse;' in rawstyle:shape='ellipse'
            elif 'rhombus;' in rawstyle:shape='diamond'
            elif rawstyle.startswith('text;'):shape='text'
            elif style.get('rounded')=='1' and shape=='rect':shape='rounded'
            if shape not in SHAPES:warnings.append('Nicht unterstützte Spezialform als Rechteck importiert: '+shape);shape='rect'
            x,y=origin(key);n=node(shape,x,y,layer_for(c));n.update(text=plain(c.get('value','')),w=max(20,float(g.get('width',160))),h=max(20,float(g.get('height',90))))
            n.update(fill=style.get('fillColor','#e7f6f1'),stroke=style.get('strokeColor','#344b55'),text_color=style.get('fontColor','#172033'),font_size=float(style.get('fontSize',15)),line_width=float(style.get('strokeWidth',2)),rotation=float(style.get('rotation',0)),dashed=style.get('dashed')=='1',align=style.get('align','center'))
            n['bold']=bool(int(style.get('fontStyle',0))&1);n['italic']=bool(int(style.get('fontStyle',0))&2);n['data']['drawio_style']=rawstyle
            if c.get('parent') not in layers and c.get('parent')!='1':n['group']='import-'+str(c.get('parent'))
            mapping[key]=n['id'];p['nodes'].append(n)
        for key,c in cells.items():
            if c.get('edge')!='1':continue
            if c.get('source') not in mapping or c.get('target') not in mapping:warnings.append('Freie Verbindung ohne zwei zugeordnete Formen wurde übersprungen.');continue
            e=edge(mapping[c.get('source')],mapping[c.get('target')],layer_for(c));style=dict(v.split('=',1) for v in c.get('style','').split(';') if '=' in v)
            arrows={'classic':'arrow','block':'arrow','open':'open','diamond':'diamond','oval':'circle','ERone':'one','ERmany':'many','ERzeroToMany':'zero_many','ERzeroToOne':'zero_one','none':'none'}
            e.update(text=plain(c.get('value','')),stroke=style.get('strokeColor','#344b55'),line_width=float(style.get('strokeWidth',2)),dashed=style.get('dashed')=='1',start=arrows.get(style.get('startArrow','none'),'none'),end=arrows.get(style.get('endArrow','classic'),'arrow'),route='curved' if style.get('curved')=='1' else ('orthogonal' if 'orthogonal' in style.get('edgeStyle','') else 'straight'))
            e['points']=[[float(pt.get('x',0)),float(pt.get('y',0))] for pt in c.findall('./mxGeometry/Array/mxPoint')];p['edges'].append(e)
        out['pages'].append(p)
    out['active_page']=out['pages'][0]['id'];return validate(out),list(dict.fromkeys(warnings))

def drawio_export(data,path):
    root=ET.Element('mxfile',host='ReDrawko',agent='Repaintko',version='1')
    shapes={'diamond':'rhombus','decision':'rhombus','relationship':'rhombus','database':'cylinder','actor':'umlActor','entity':'swimlane','data':'parallelogram','attribute':'ellipse','key_attribute':'ellipse','usecase':'ellipse','weak_entity':'rectangle'}
    arrows={'arrow':'classic','open':'open','diamond':'diamond','circle':'oval','one':'ERone','many':'ERmany','zero_one':'ERzeroToOne','zero_many':'ERzeroToMany','none':'none'}
    for p in data['pages']:
        diagram=ET.SubElement(root,'diagram',id=p['id'],name=p['name']);model=ET.SubElement(diagram,'mxGraphModel',pageWidth=str(p['width']),pageHeight=str(p['height']),grid='1');cells=ET.SubElement(model,'root');ET.SubElement(cells,'mxCell',id='0')
        for l in p['layers']:ET.SubElement(cells,'mxCell',id=l['id'],parent='0',value=l['name'],visible='1' if l['visible'] else '0')
        for n in p['nodes']:
            shape=shapes.get(n['shape'],n['shape']);text=n['text']
            if n['shape']=='entity':text+='\n'+'\n'.join(f"{r.get('key','')} {r['name']} : {r.get('type','')}".strip() for r in n['rows'])
            style=f"shape={shape};whiteSpace=wrap;html=0;fillColor={n['fill']};strokeColor={n['stroke']};fontColor={n['text_color']};fontSize={n['font_size']};strokeWidth={n['line_width']};rotation={n['rotation']};fontStyle={int(n['bold'])+2*int(n['italic'])};dashed={int(n['dashed'])};align={n['align']};"
            if n['shape'] in ('rounded','process','terminator'):style+='rounded=1;'
            cell=ET.SubElement(cells,'mxCell',id=n['id'],parent=n['layer'],vertex='1',value=text,style=style)
            ET.SubElement(cell,'mxGeometry',x=str(n['x']),y=str(n['y']),width=str(n['w']),height=str(n['h']),attrib={'as':'geometry'})
        for e in p['edges']:
            style=f"edgeStyle={'orthogonalEdgeStyle' if e['route']=='orthogonal' else 'none'};curved={int(e['route']=='curved')};startArrow={arrows[e['start']]};endArrow={arrows[e['end']]};strokeColor={e['stroke']};strokeWidth={e['line_width']};dashed={int(e['dashed'])};"
            cell=ET.SubElement(cells,'mxCell',id=e['id'],parent=e['layer'],edge='1',source=e['source'],target=e['target'],value=e['text'],style=style);g=ET.SubElement(cell,'mxGeometry',relative='1',attrib={'as':'geometry'})
            if e['points']:
                points=ET.SubElement(g,'Array',attrib={'as':'points'})
                for x,y in e['points']:ET.SubElement(points,'mxPoint',x=str(x),y=str(y))
    atomic_write(path,ET.tostring(root,encoding='utf-8',xml_declaration=True))

def sql_export(p):
    from sql_schema import export_schema
    return export_schema(p)

def sql_import(text):
    from sql_schema import parse_schema
    return parse_schema(text)

def export_scene(scene,path,scale=2,transparent=False):
    from PySide6.QtCore import QRectF,QSize,QSizeF,Qt
    from PySide6.QtGui import QPainter,QImage,QPdfWriter,QPageSize,QPageLayout
    selected=scene.selected_ids();scene.clearSelection();scene.exporting=True;scene.transparent_export=transparent
    p=scene.doc.page;rect=QRectF(0,0,p['width'],p['height']);suffix=Path(path).suffix.lower();painter=None
    try:
        if suffix=='.svg':
            from PySide6.QtSvg import QSvgGenerator
            target=QSvgGenerator();target.setFileName(str(path));target.setSize(QSize(round(rect.width()),round(rect.height())));target.setViewBox(rect);target.setTitle('ReDrawko · '+p['name']);painter=QPainter(target);scene.render(painter,rect,rect)
        elif suffix=='.pdf':
            target=QPdfWriter(str(path));target.setResolution(96);target.setPageSize(QPageSize(QSizeF(rect.width()*25.4/96,rect.height()*25.4/96),QPageSize.Unit.Millimeter));painter=QPainter(target);scene.render(painter,QRectF(0,0,target.width(),target.height()),rect)
        else:
            w,h=round(rect.width()*scale),round(rect.height()*scale)
            if w*h>64_000_000:raise ValueError('PNG-Export maximal 64 Millionen Pixel. Kleinere Seite oder Skalierung wählen.')
            image=QImage(w,h,QImage.Format.Format_ARGB32_Premultiplied);image.fill(Qt.GlobalColor.transparent if transparent else __import__('PySide6.QtGui',fromlist=['QColor']).QColor(p['background']));painter=QPainter(image);scene.render(painter,QRectF(0,0,w,h),rect);painter.end();painter=None
            if not image.save(str(path),'PNG'):raise OSError('PNG konnte nicht gespeichert werden.')
    finally:
        if painter is not None:painter.end()
        scene.exporting=False
        for key in selected:
            item=scene.nodes.get(key) or scene.edges.get(key)
            if item:item.setSelected(True)
        scene.update()
