// Turso SQL-over-HTTPS adapter. No credentials or database paths are exposed to browsers.
export function remoteDatabase(rawUrl, token, transport=fetch) {
  const url=new URL(rawUrl.replace(/^(libsql|turso):/, 'https:'));
  if(url.protocol!=='https:'||!url.hostname.endsWith('.turso.io')||url.username||url.password||url.search||url.hash||url.pathname!=='/'||url.port)throw Error('Ungültige Turso-Datenbankadresse.');
  if(!token)throw Error('TURSO_AUTH_TOKEN fehlt.');
  const endpoint=new URL('/v2/pipeline',url);
  const encode=value=>value===null?{type:'null'}:typeof value==='number'?{type:'integer',value:String(value)}:{type:'text',value:String(value)};
  async function execute(sql,args=[]){
    const response=await transport(endpoint,{method:'POST',redirect:'error',signal:AbortSignal.timeout(10000),headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},body:JSON.stringify({requests:[{type:'execute',stmt:{sql,args:args.map(encode)}},{type:'close'}]})});
    if(!response.ok)throw Object.assign(Error('Datenbank vorübergehend nicht erreichbar.'),{status:503});
    const payload=await response.json(),entry=payload.results?.[0];
    if(entry?.type==='error')throw Object.assign(Error('Datenbankanfrage fehlgeschlagen.'),{code:entry.error?.code});
    const result=entry?.response?.result;if(!result)throw Error('Ungültige Datenbankantwort.');
    const decode=value=>value.type==='null'?null:value.type==='integer'||value.type==='float'?Number(value.value):value.value;
    return {rows:result.rows.map(row=>Object.fromEntries(result.cols.map((col,i)=>[col.name,decode(row[i])]))),changes:result.affected_row_count,lastInsertRowid:result.last_insert_rowid};
  }
  return {prepare(sql){return {async get(...args){return (await execute(sql,args)).rows[0];},async all(...args){return (await execute(sql,args)).rows;},async run(...args){return execute(sql,args);}};},async exec(sql){for(const statement of sql.split(';').map(s=>s.trim()).filter(Boolean))await execute(statement);},close(){}};
}
