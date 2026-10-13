const { spawn } = require('child_process');
const http = require('http');
const WebSocket = require('ws');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FILE = 'file:///c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html';
const PORT = 9229;
const PROFILE = 'c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_profile_dateblk';
function getJSON(url){return new Promise((res,rej)=>{http.get(url,r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>{try{res(JSON.parse(d));}catch(e){rej(e);}});}).on('error',rej);});}
const chrome=spawn(CHROME,['--headless=new','--disable-gpu','--no-sandbox','--remote-debugging-port='+PORT,'--user-data-dir='+PROFILE,'about:blank'],{stdio:'ignore'});
function sleep(ms){return new Promise(r=>setTimeout(r,ms));}
async function main(){
  await sleep(2500);
  let targets;
  for(let i=0;i<20;i++){try{targets=await getJSON(`http://127.0.0.1:${PORT}/json/list`);if(targets&&targets.length)break;}catch(e){}await sleep(500);}
  const page=targets.find(t=>t.type==='page')||targets[0];
  const ws=new WebSocket(page.webSocketDebuggerUrl,{perMessageDeflate:false});
  let id=0;const pending=new Map();const errors=[];
  function send(m,p){return new Promise(r=>{const mid=++id;pending.set(mid,r);ws.send(JSON.stringify({id:mid,method:m,params:p||{}}));});}
  ws.on('message',raw=>{const m=JSON.parse(raw);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);}if(m.method==='Runtime.exceptionThrown'){errors.push(JSON.stringify(m.params.exceptionDetails));}});
  await new Promise(r=>ws.on('open',r));
  await send('Page.enable');await send('Runtime.enable');
  await send('Page.navigate',{url:FILE});
  await sleep(5000);
  const ev=await send('Runtime.evaluate',{expression:`(function(){
    const fa=formalAttPayload;
    let dayTotal=0, dayCount=0;
    for(const k of Object.keys(fa.data)){ const d=fa.data[k]; if(d&&typeof d.total==='number'){ dayTotal+=d.total; dayCount++; } }
    // warehouse-level untimely (one level, no group double count)
    let whU=0;
    for(const k of Object.keys(fa.data)){ const d=fa.data[k]; if(d&&Array.isArray(d.warehouse)){ for(const w of d.warehouse){ if(typeof w.untimely==='number') whU+=w.untimely; } } }
    return JSON.stringify({ dayTotal, dayCount, whU, expectedTotal:115244, expectedUntimely:2271 });
  })()`,returnByValue:true});
  const o=JSON.parse(ev.result.result.value);
  console.log('date-block grand total:',o.dayTotal,'(expected 115244) match:',o.dayTotal===115244);
  console.log('date-block count:',o.dayCount);
  console.log('warehouse-level untimely:',o.whU,'(expected 2271) match:',o.whU===2271);
  console.log('JS ERRORS:',errors.length);
  ws.close();chrome.kill('SIGKILL');process.exit(0);
}
main().catch(e=>{console.error('PROBE FAIL',e);chrome.kill('SIGKILL');process.exit(1);});
