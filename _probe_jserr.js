const { spawn } = require('child_process');
const http = require('http');
const WebSocket = require('ws');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FILE = 'file:///c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/%E8%A1%A5%E7%AD%BE%E6%B5%81%E7%A8%8B_%E8%A1%A5%E7%AD%BE%E7%BB%9F%E8%AE%A1.html';
const PORT = 9294;
const PROFILE = 'c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_profile_jserr';
function getJSON(url){return new Promise((res,rej)=>{http.get(url,r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>{try{res(JSON.parse(d));}catch(e){rej(e);}});}).on('error',rej);});}
const chrome=spawn(CHROME,['--headless=new','--disable-gpu','--no-sandbox','--remote-debugging-port='+PORT,'--user-data-dir='+PROFILE,'--window-size=1400,2400','about:blank'],{stdio:'ignore'});
function sleep(ms){return new Promise(r=>setTimeout(r,ms));}
async function main(){
  await sleep(2500);
  let targets;
  for(let i=0;i<30;i++){try{targets=await getJSON(`http://127.0.0.1:${PORT}/json/list`);if(targets&&targets.length)break;}catch(e){}await sleep(500);}
  const page=targets.find(t=>t.type==='page')||targets[0];
  const ws=new WebSocket(page.webSocketDebuggerUrl,{perMessageDeflate:false});
  let id=0;const pending=new Map();const errs=[];
  function send(m,p){return new Promise(r=>{const mid=++id;pending.set(mid,r);ws.send(JSON.stringify({id:mid,method:m,params:p||{}}));});}
  ws.on('message',raw=>{const m=JSON.parse(raw);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);}
    if(m.method==='Runtime.exceptionThrown'){const d=m.params.exceptionDetails||{};errs.push({text:d.text,desc:(d.exception||{}).description||'',line:d.lineNumber,col:d.columnNumber});}
    if(m.method==='Log.entryAdded'){const e=m.params.entry||{};if(e.level==='error')errs.push({text:e.text,desc:(e.stackTrace&&e.stackTrace.description)||''});}});
  await new Promise(r=>ws.on('open',r));
  await send('Page.enable');await send('Runtime.enable');await send('Log.enable');
  await send('Page.navigate',{url:FILE});
  await sleep(9000);
  console.log(JSON.stringify(errs.slice(0,6),null,1).slice(0,3000));
  chrome.kill();process.exit(0);
}
main().catch(e=>{console.error('FATAL',e);chrome.kill();process.exit(1);});
