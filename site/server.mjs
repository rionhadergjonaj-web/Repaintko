import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomBytes } from 'node:crypto';
import { openDatabase, username, passwordValid, hashPassword, checkPassword, digest } from './store.mjs';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const fail=(status,message)=>Object.assign(new Error(message),{status});
export async function createApp({database=process.env.DATABASE_PATH || resolve(root,'data/community.sqlite'),origin=process.env.PUBLIC_ORIGIN || 'http://127.0.0.1:3000',production=process.env.NODE_ENV==='production',rateLimit=30}={}) {
  if(new URL(origin).origin!==origin || (production && !origin.startsWith('https://'))) throw new Error('PUBLIC_ORIGIN muss die exakte Herkunft sein; Produktion benötigt HTTPS.');
  const db=openDatabase(database), rates=new Map();
  const dummy=await hashPassword(randomBytes(32).toString('hex'));
  const cookieName=production?'__Host-repaintko':'repaintko';
  const headers={'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self' https://api.github.com; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",'X-Content-Type-Options':'nosniff','Referrer-Policy':'same-origin','X-Frame-Options':'DENY'};
  if(production) headers['Strict-Transport-Security']='max-age=31536000';
  let hashes=0;
  async function boundedHash(fn){if(hashes>=4) throw fail(503,'Bitte kurz warten und erneut versuchen.'); hashes++;try{return await fn();}finally{hashes--;}}
  function rate(key,limit=rateLimit,period=600000){const now=Date.now();for(const [k,v] of rates) if(v.until<now) rates.delete(k); let v=rates.get(key);if(!v){if(rates.size>=10000) throw fail(429,'Bitte später erneut versuchen.');v={count:0,until:now+period};rates.set(key,v);}if(++v.count>limit) throw fail(429,'Zu viele Versuche. Bitte später erneut versuchen.');}
  function user(req){const match=(req.headers.cookie||'').split(';').map(x=>x.trim()).find(x=>x.startsWith(cookieName+'='));if(!match)return null;const token=match.slice(cookieName.length+1);return db.prepare('SELECT u.id,u.name,u.role FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>?').get(digest(token),Date.now()) || null;}
  function session(res,id){const token=randomBytes(32).toString('hex');db.prepare('DELETE FROM sessions WHERE expires<=?').run(Date.now());db.prepare('INSERT INTO sessions VALUES(?,?,?)').run(digest(token),id,Date.now()+604800000);res.setHeader('Set-Cookie',`${cookieName}=${token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=604800${production?'; Secure':''}`);}
  async function body(req){if(!req.headers['content-type']?.startsWith('application/json'))throw fail(415,'JSON erforderlich.');let size=0,chunks=[];for await(const chunk of req){size+=chunk.length;if(size>16384)throw fail(413,'Eingabe ist zu groß.');chunks.push(chunk);}try{const value=JSON.parse(Buffer.concat(chunks));if(!value||Array.isArray(value)||typeof value!=='object')throw Error();return value;}catch{throw fail(400,'Ungültige Eingabe.');}}
  const server=http.createServer(async(req,res)=>{
    for(const [key,value] of Object.entries(headers))res.setHeader(key,value);
    const send=(status,value)=>{res.writeHead(status,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'});res.end(JSON.stringify(value));};
    try{
      const path=new URL(req.url,'http://localhost').pathname;
      if(path.startsWith('/api/')){
        res.setHeader('Cache-Control','no-store');
        if(req.method!=='GET' && req.headers.origin!==origin)throw fail(403,'Anfrage stammt nicht von dieser Webseite.');
        const current=user(req);
        if(path==='/api/me' && req.method==='GET')return send(200,{user:current});
        if(['/api/register','/api/login'].includes(path) && req.method==='POST'){
          rate('auth:'+req.socket.remoteAddress);const input=await body(req);let name;
          try{name=username(input.name);}catch(e){throw fail(400,e.message);}
          if(!passwordValid(input.password))throw fail(400,'Passwort: 12–128 Zeichen.');
          rate('name:'+name.key);
          if(path==='/api/register'){
            if(name.key==='rezzko')throw fail(409,'Dieser Benutzername ist reserviert.');
            const hash=await boundedHash(()=>hashPassword(input.password));let result;
            try{result=db.prepare('INSERT INTO users(name,name_key,password) VALUES(?,?,?)').run(name.name,name.key,hash);}catch(e){if(e.code?.includes('SQLITE') && db.prepare('SELECT id FROM users WHERE name_key=?').get(name.key))throw fail(409,'Dieser Benutzername ist bereits vergeben.');throw e;}
            session(res,Number(result.lastInsertRowid));return send(201,{ok:true});
          }
          const found=db.prepare('SELECT * FROM users WHERE name_key=?').get(name.key);
          const valid=await boundedHash(()=>checkPassword(input.password,found?.password||dummy));
          if(!found||!valid)throw fail(401,'Benutzername oder Passwort ist falsch.');
          session(res,found.id);return send(200,{ok:true});
        }
        if(path==='/api/logout' && req.method==='POST'){
          const token=(req.headers.cookie||'').split(';').map(x=>x.trim()).find(x=>x.startsWith(cookieName+'='));if(token)db.prepare('DELETE FROM sessions WHERE token=?').run(digest(token.slice(cookieName.length+1)));
          res.setHeader('Set-Cookie',`${cookieName}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0${production?'; Secure':''}`);return send(200,{ok:true});
        }
        if(!current)throw fail(401,'Bitte zuerst anmelden.');
        if(path==='/api/suggestions' && req.method==='POST'){
          rate('suggest:'+current.id,10,3600000);const input=await body(req);
          if(typeof input.title!=='string'||typeof input.body!=='string'||input.title.trim().length<3||input.title.trim().length>120||input.body.trim().length<10||input.body.trim().length>5000)throw fail(400,'Titel: 3–120 Zeichen. Vorschlag: 10–5000 Zeichen.');
          const result=db.prepare('INSERT INTO suggestions(user_id,title,body,created) VALUES(?,?,?,?)').run(current.id,input.title.trim(),input.body.trim(),Date.now());return send(201,{id:Number(result.lastInsertRowid)});
        }
        if(path==='/api/suggestions' && req.method==='GET')return send(200,{suggestions:db.prepare('SELECT id,title,body,created,status FROM suggestions WHERE user_id=? ORDER BY id DESC LIMIT 100').all(current.id)});
        if(path==='/api/admin/suggestions' && req.method==='GET'){
          if(current.role!=='admin')throw fail(403,'Nur für Administratoren.');
          const before=Number(new URL(req.url,'http://localhost').searchParams.get('before')||Number.MAX_SAFE_INTEGER);
          if(!Number.isSafeInteger(before)||before<1)throw fail(400,'Ungültige Seite.');
          return send(200,{suggestions:db.prepare('SELECT s.*,u.name FROM suggestions s JOIN users u ON u.id=s.user_id WHERE s.id<? ORDER BY s.id DESC LIMIT 100').all(before)});
        }
        if(/^\/api\/admin\/suggestions\/\d+$/.test(path) && req.method==='PATCH'){
          if(current.role!=='admin')throw fail(403,'Nur für Administratoren.');const input=await body(req);if(!['new','reviewing','planned','done'].includes(input.status))throw fail(400,'Ungültiger Status.');
          const result=db.prepare('UPDATE suggestions SET status=? WHERE id=?').run(input.status,Number(path.split('/').pop()));if(!result.changes)throw fail(404,'Vorschlag nicht gefunden.');return send(200,{ok:true});
        }
        throw fail(404,'Nicht gefunden.');
      }
      if(!['GET','HEAD'].includes(req.method))throw fail(405,'Methode nicht erlaubt.');
      // Explicit public-file allowlist: database, source and signing keys are never served.
      const files={'/':['index.html','text/html'],'/index.html':['index.html','text/html'],'/community':['web/community.html','text/html'],'/healthz':[null,'text/plain'],'/version.json':['version.json','application/json'],'/web/style.css':['web/style.css','text/css'],'/web/releases.js':['web/releases.js','text/javascript'],'/web/favicon.svg':['web/favicon.svg','image/svg+xml'],'/web/community.css':['web/community.css','text/css'],'/web/community.js':['web/community.js','text/javascript']};
      const file=files[path];if(!file)throw fail(404,'Nicht gefunden.');
      const content=file[0]?await readFile(resolve(root,file[0])):Buffer.from('ok');res.writeHead(200,{'Content-Type':file[1]+'; charset=utf-8','Cache-Control':'no-cache'});res.end(req.method==='HEAD'?undefined:content);
    }catch(e){if(!res.headersSent)send(e.status||500,{error:e.status?e.message:'Interner Fehler. Bitte erneut versuchen.'});else res.end();}
  });
  server.requestTimeout=15000;server.headersTimeout=10000;
  return {server,db,close:async()=>{await new Promise(r=>server.close(r));db.close();}};
}
if(process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const app=await createApp();app.server.listen(Number(process.env.PORT||3000),process.env.HOST||'127.0.0.1',()=>console.log('Repaintko-Webserver bereit.'));
  for(const signal of ['SIGINT','SIGTERM'])process.on(signal,async()=>{await app.close();process.exit(0);});
}
