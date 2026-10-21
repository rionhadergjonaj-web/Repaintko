"""SQL AST interchange shared by ReDrawko and ReDataKo; never executes SQL."""
import math
import sqlglot
from sqlglot import exp
from redraw_model import page,node,edge

def table_name(t):return '.'.join(part.name for part in t.parts)
def quoted(name,dialect='sqlite'):
    q='`' if dialect=='mysql' else '"'
    return q+name.replace(q,q+q)+q
def names(expressions):return [e.name for e in expressions]

def layout(p,order=None):
    nodes=p['nodes'];lookup={n['id']:n for n in nodes};parents={n['id']:set() for n in nodes}
    for e in p['edges']:
        if e['source']!=e['target']:parents[e['source']].add(e['target'])
    levels={};remaining=set(lookup)
    while remaining:
        ready=sorted(k for k in remaining if not (parents[k]&remaining))
        if not ready:ready=[min(remaining,key=lambda k:(len(parents[k]&remaining),lookup[k]['text']))]
        for k in ready:levels[k]=min(12,max([levels.get(v,-1)+1 for v in parents[k]]+[0]));remaining.remove(k)
    ranks={name:i for i,name in enumerate(order or [])};columns={}
    for k,l in levels.items():columns.setdefault(l,[]).append(lookup[k])
    x=80
    for level,items in sorted(columns.items()):
        items.sort(key=lambda n:(ranks.get(n['text'],9999),sum(lookup[k].get('y',0) for k in parents[n['id']]),n['text']))
        y=80
        for n in items:n['x']=x;n['y']=y;n['w']=max(300,min(600,max([len(n['text'])]+[len(r['name'])+len(r.get('type',''))+8 for r in n.get('rows',[])])*8));n['h']=max(100,42+26*len(n.get('rows',[])));y+=n['h']+100
        x+=max(n['w'] for n in items)+180
    p['width']=max(1000,x+80);p['height']=max(700,max((n['y']+n['h']+80 for n in nodes),default=700))
    for e in p['edges']:
        a,b=lookup[e['source']],lookup[e['target']]
        if abs(a['x']-b['x'])<30:e['source_port']='bottom' if a['y']<b['y'] else 'top';e['target_port']='top' if a['y']<b['y'] else 'bottom'
        else:e['source_port']='left' if a['x']>b['x'] else 'right';e['target_port']='right' if a['x']>b['x'] else 'left'
        e['points']=[]

def parse_schema(text,dialect='sqlite'):
    if len(text)>5_000_000:raise ValueError('SQL-Import maximal 5 MB.')
    trees=sqlglot.parse(text,read=dialect);p=page('SQL-Schema');p['sql_dialect']=dialect;p['sql_indexes']=[];p['sql_warnings']=[]
    tables={};foreign=[]
    def fk(table,cols,ref,name=''):
        schema=ref.this
        if not isinstance(schema,exp.Schema):raise ValueError('REFERENCES ohne explizite Zielspalten bitte ergänzen.')
        foreign.append(dict(table=table,columns=cols,target=table_name(schema.this),target_columns=names(schema.expressions),name=name,options=ref.args.get('options') or []))
    for tree in trees:
        if tree is None:continue
        if isinstance(tree,exp.Create) and tree.kind=='TABLE' and isinstance(tree.this,exp.Schema):
            schema=tree.this;name=table_name(schema.this)
            if name.casefold() in tables:raise ValueError('Doppelter Tabellenname: '+name)
            n=node('entity',0,0,p['active_layer']);n.update(text=name,rows=[],sql_constraints=[],sql_original_name=name);pk=set()
            for col in schema.expressions:
                if isinstance(col,exp.ColumnDef):
                    row=dict(name=col.name,type=col.args['kind'].sql(dialect=dialect),key='',nullable=True,sql_extra=[])
                    for c in col.constraints:
                        kind=c.kind
                        if isinstance(kind,exp.PrimaryKeyColumnConstraint):pk.add(col.name)
                        elif isinstance(kind,exp.NotNullColumnConstraint):row['nullable']=False
                        elif isinstance(kind,exp.UniqueColumnConstraint):row['key']='UQ'
                        elif isinstance(kind,exp.Reference):fk(name,[col.name],kind)
                        else:row['sql_extra'].append(c.sql(dialect=dialect))
                    n['rows'].append(row)
                else:
                    fks=list(col.find_all(exp.ForeignKey))
                    if isinstance(col,exp.ForeignKey):fks=[col]
                    if fks:
                        for f in fks:fk(name,names(f.expressions),f.args['reference'],col.name if isinstance(col,exp.Constraint) else '')
                    else:
                        keys=list(col.find_all(exp.PrimaryKey))
                        if isinstance(col,exp.PrimaryKey):keys=[col]
                        if keys:
                            for key in keys:pk.update(names(key.expressions))
                        else:n['sql_constraints'].append(col.sql(dialect=dialect))
            for r in n['rows']:
                if r['name'] in pk:r['key']=('PK '+r['key']).strip();r['nullable']=False
            tables[name.casefold()]=n;p['nodes'].append(n)
        elif isinstance(tree,exp.Alter):
            for f in tree.find_all(exp.ForeignKey):fk(table_name(tree.this),names(f.expressions),f.args['reference'])
            if not list(tree.find_all(exp.ForeignKey)):p['sql_warnings'].append('ALTER ohne Fremdschlüssel nicht als Diagramm übernommen.')
        elif isinstance(tree,exp.Create) and tree.kind=='INDEX':p['sql_indexes'].append(tree.sql(dialect=dialect))
        else:p['sql_warnings'].append('Nur Schema übernommen: '+tree.key.upper())
    if not tables:raise ValueError('Keine unterstützte CREATE TABLE-Definition gefunden.')
    for f in foreign:
        a=tables.get(f['table'].casefold());b=tables.get(f['target'].casefold())
        if a is None or b is None:raise ValueError('Fremdschlüssel verweist auf fehlende Tabelle: '+f['target'])
        if len(f['columns'])!=len(f['target_columns']) or not f['columns']:raise ValueError('Ungültiger zusammengesetzter Fremdschlüssel.')
        for col in f['columns']:
            r=next((r for r in a['rows'] if r['name']==col),None)
            if r is None:raise ValueError('Fremdschlüsselspalte fehlt: '+col)
            r['key']=(r['key']+' FK').strip()
        if not set(f['target_columns'])<={r['name'] for r in b['rows']}:raise ValueError('Zielspalte fehlt: '+f['target'])
        e=edge(a['id'],b['id'],p['active_layer']);e.update(start='many',end='one',text=', '.join(f['columns'])+' → '+', '.join(f['target_columns']),sql_fk=f);p['edges'].append(e)
    layout(p);return p

def export_schema(p,dialect=None):
    dialect=dialect or p.get('sql_dialect','sqlite');lookup={n['id']:n for n in p['nodes']};statements=[]
    for n in p['nodes']:
        if n['shape']!='entity':continue
        lines=[];pk=[]
        for r in n['rows']:
            text=quoted(r['name'],dialect)+' '+(r.get('type') or 'TEXT')
            if not r.get('nullable'):text+=' NOT NULL'
            if 'UQ' in r.get('key',''):text+=' UNIQUE'
            auto=dialect=='sqlite' and any('AUTOINCREMENT' in c.upper() for c in r.get('sql_extra',[]))
            if auto:
                text=quoted(r['name'],dialect)+' INTEGER PRIMARY KEY'
            elif 'PK' in r.get('key',''):pk.append(r['name'])
            text+=' '+' '.join(r.get('sql_extra',[]));lines.append(text.strip())
        if pk:lines.append('PRIMARY KEY ('+', '.join(quoted(k,dialect) for k in pk)+')')
        lines.extend(n.get('sql_constraints',[]))
        for e in p['edges']:
            if e['source']!=n['id'] or not e.get('sql_fk'):continue
            f=e['sql_fk'];target=lookup[e['target']]
            if not set(f['columns'])<={r['name'] for r in n['rows']} or not set(f['target_columns'])<={r['name'] for r in target['rows']}:raise ValueError('FK-Spalten wurden umbenannt/gelöscht. Verbindung zuerst korrigieren.')
            prefix='CONSTRAINT '+quoted(f['name'],dialect)+' ' if f.get('name') else ''
            lines.append(prefix+'FOREIGN KEY ('+', '.join(quoted(k,dialect) for k in f['columns'])+') REFERENCES '+'.'.join(quoted(k,dialect) for k in target['text'].split('.'))+' ('+', '.join(quoted(k,dialect) for k in f['target_columns'])+') '+' '.join(f.get('options',[])))
        statement='CREATE TABLE '+'.'.join(quoted(k,dialect) for k in n['text'].split('.'))+' (\n  '+',\n  '.join(lines)+'\n)'
        sqlglot.parse_one(statement,read=dialect);statements.append(statement+';')
    statements += [s.rstrip(';')+';' for s in p.get('sql_indexes',[])]
    return '\n\n'.join(statements)+'\n'
