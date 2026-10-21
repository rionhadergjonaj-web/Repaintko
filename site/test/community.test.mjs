import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp,rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createApp } from '../server.mjs';
import { provisionAdmin } from '../store.mjs';
const password='Test-only-strong-password-123';
test('Konten, Rechte, Vorschläge, Sitzungen und persistente Daten',async()=>{
 const dir=await mkdtemp(join(tmpdir(),'community-'));const database=join(dir,'test.sqlite');let app=await createApp({database});
 await provisionAdmin(app.db,password);await new Promise(r=>app.server.listen(0,'127.0.0.1',r));let base='http://127.0.0.1:'+app.server.address().port;
 async function call(path,method='GET',data,cookie='',origin='http://127.0.0.1:3000'){const response=await fetch(base+path,{method,headers:{Origin:origin,Cookie:cookie,'Content-Type':'application/json'},body:data?JSON.stringify(data):undefined});return {status:response.status,body:await response.json(),cookie:response.headers.get('set-cookie')?.split(';')[0],headers:response.headers};}
 try{
 assert.equal((await call('/api/register','POST',{name:'four',password})).status,400);
 assert.equal((await call('/api/register','POST',{name:'REZZKO',password})).status,409);
 assert.equal((await call('/api/register','POST',{name:'Alice01',password:'short'})).status,400);
 assert.equal((await call('/api/register','POST',{name:'Alice01',password},'','https://evil.test')).status,403);
 const alice=await call('/api/register','POST',{name:'Alice01',password,role:'admin'});assert.equal(alice.status,201);
 assert.equal((await call('/api/me','GET',null,alice.cookie)).body.user.role,'user');
 assert.equal((await call('/api/register','POST',{name:'ALICE01',password})).status,409);
 const racers=await Promise.all([call('/api/register','POST',{name:'Racer01',password}),call('/api/register','POST',{name:'racer01',password})]);assert.deepEqual(racers.map(x=>x.status).sort(),[201,409]);
 assert.equal((await call('/api/login','POST',{name:'Alice01',password:'incorrect-password'})).status,401);
 assert.equal((await call('/api/admin/suggestions','GET',null,alice.cookie)).status,403);
 assert.equal((await call('/api/suggestions','POST',{title:'Neue Idee',body:'Eine längere Beschreibung.'})).status,401);
 const suggestion=await call('/api/suggestions','POST',{title:'<script>test</script>',body:'Eine neue Funktion für Repaintko.'},alice.cookie);assert.equal(suggestion.status,201);
 const bob=await call('/api/register','POST',{name:'Bobby01',password});assert.equal((await call('/api/suggestions','GET',null,bob.cookie)).body.suggestions.length,0);
 const admin=await call('/api/login','POST',{name:'rezzko',password});assert.equal(admin.status,200);
 assert.equal((await call('/api/admin/suggestions','GET',null,admin.cookie)).body.suggestions[0].name,'Alice01');
 assert.equal((await call('/api/admin/suggestions/'+suggestion.body.id,'PATCH',{status:'done'},alice.cookie)).status,403);
 assert.equal((await call('/api/admin/suggestions/'+suggestion.body.id,'PATCH',{status:'done'},admin.cookie)).status,200);
 assert.equal((await call('/api/suggestions','GET',null,alice.cookie)).body.suggestions[0].status,'done');
 assert.equal((await call('/api/suggestions','POST',{title:'Title',body:'x'.repeat(20000)},alice.cookie)).status,413);
 for(const path of ['/data/community.sqlite','/.secrets/update-signing.dpapi','/site/server.mjs']) assert.equal((await fetch(base+path)).status,404);
 assert.match((await fetch(base+'/community')).headers.get('content-security-policy'),/frame-ancestors 'none'/);
 const stored=app.db.prepare('SELECT password FROM users WHERE name_key=?').get('alice01').password;assert.ok(!stored.includes(password));
 await app.close();app=await createApp({database});await new Promise(r=>app.server.listen(0,'127.0.0.1',r));base='http://127.0.0.1:'+app.server.address().port;
 assert.equal((await call('/api/suggestions','GET',null,alice.cookie)).body.suggestions.length,1);
 await call('/api/logout','POST',{},alice.cookie);assert.equal((await call('/api/me','GET',null,alice.cookie)).body.user,null);
 await assert.rejects(()=>provisionAdmin(app.db,password),/existiert bereits/);
 }finally{await app.close();await rm(dir,{recursive:true,force:true});}
});
test('Produktionscookies und Begrenzung von Anmeldeversuchen',async()=>{
 const app=await createApp({database:':memory:',origin:'https://repaintko.com',production:true,rateLimit:2});await new Promise(r=>app.server.listen(0,'127.0.0.1',r));const base='http://127.0.0.1:'+app.server.address().port;
 try{const send=()=>fetch(base+'/api/register',{method:'POST',headers:{Origin:'https://repaintko.com','Content-Type':'application/json'},body:JSON.stringify({name:'User123',password})});const one=await send();assert.equal(one.status,201);assert.match(one.headers.get('set-cookie'),/__Host-repaintko=.*HttpOnly.*SameSite=Strict.*Secure/);await send();assert.equal((await send()).status,429);}finally{await app.close();}
});
