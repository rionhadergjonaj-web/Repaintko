const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(require('node:path').join(__dirname, '../web/releases.js'), 'utf8');
function element() { return {textContent:'', href:'', children:[], append(...items){this.children.push(...items)}, replaceChildren(){this.children=[]}}; }
async function run(responses) {
  const nodes = new Map();
  const document = {getElementById(id){if(!nodes.has(id))nodes.set(id,element());return nodes.get(id)},createElement:element};
  let index=0;
  const context = vm.createContext({document, URL, AbortSignal, Date, fetch:async()=>{
    const data=responses[index++];if(data instanceof Error)throw data;
    return {ok:true,json:async()=>data};
  }});
  // Invoke once, then await the real asynchronous release handling.
  vm.runInContext(source.replace(/loadReleases\(\);\s*$/, ''),context);
  await vm.runInContext('loadReleases()',context);
  return nodes;
}
(async()=>{
  const release={tag_name:'v13.1.0',name:'<script>not executable</script>',published_at:'2026-10-20T10:00:00Z',body:'Changes',assets:[{name:'Repaintko-Setup-13.1.0.exe',browser_download_url:'https://github.com/rionhadergjonaj-web/Repaintko/releases/download/v13.1.0/Repaintko-Setup-13.1.0.exe',size:1024*1024}]};
  let nodes=await run([[release],release]);
  assert.match(nodes.get('download-button').href,/13.1.0.exe$/);
  assert.equal(nodes.get('release-list').children[0].children[0].textContent,release.name);
  nodes=await run([[]]);assert.match(nodes.get('release-status').textContent,/vorbereitet/);
  nodes=await run([new Error('offline')]);assert.match(nodes.get('download-button').href,/releases$/);
  const malicious={...release,assets:[{...release.assets[0],browser_download_url:'https://evil.invalid/setup.exe'}]};
  nodes=await run([[malicious],malicious]);assert.equal(nodes.get('download-button'),undefined);
  console.log('Website: latest release, safe text rendering, no release, offline fallback and untrusted asset rejection: OK');
})().catch(error=>{console.error(error);process.exitCode=1});
