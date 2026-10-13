const { spawn } = require('child_process');
const http = require('http');
const WebSocket = require('ws');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FILE = 'file:///c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html';
const PORT = 9230;
const PROFILE = 'c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_profile_one';
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
    const k=Object.keys(fa.data)[0];
    const d=fa.data[k];
    const wh=d.warehouse||[];
    const w0=wh[0]||null;
    const w0keys=w0?Object.keys(w0):[];
    const g0=(w0&&w0.group&&w0.group[0])||null;
    const g0keys=g0?Object.keys(g0):[];
    const grpArr=d.group||[];
    const g0b=grpArr[0]||null;
    // sum untimely at warehouse level and group level separately for this date
    let wSum=0, gSumW=0, gSumD=0;
    for(const w of wh){ if(typeof w.untimely==='number') wSum+=w.untimely; if(Array.isArray(w.group)) for(const g of w.group){ if(typeof g.untimely==='number') gSumW+=g.untimely; } }
    for(const g of grpArr){ if(typeof g.untimely==='number') gSumD+=g.untimely; }
    return JSON.stringify({ k, hasTotal: d.total, whCount: wh.length, w0keys, w0untimely: w0?w0.untimely:null, g0keys, g0untimely: g0?g0.untimely:null, wSum, gSumW, gSumD });
  })()`,returnByValue:true});
  const o=JSON.parse(ev.result.result.value);
  console.log('sample date key:',o.k,' d.total=',o.hasTotal);
  console.log('whCount:',o.whCount,' w0keys:',JSON.stringify(o.w0keys));
  console.log('w0.untimely=',o.w0untimely,' g0keys:',JSON.stringify(o.g0keys),' g0.untimely=',o.g0untimely);
  console.log('this date -> warehouse.untimely sum:',o.wSum,' group-inside-warehouse sum:',o.gSumW,' top-level group sum:',o.gSumD);
  console.log('JS ERRORS:',errors.length);
  ws.close();chrome.kill('SIGKILL');process.exit(0);
}
main().catch(e=>{console.error('PROBE FAIL',e);chrome.kill('SIGKILL');process.exit(1);});
