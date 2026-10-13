const { spawn } = require('child_process');
const http = require('http');
const WebSocket = require('ws');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FILE = 'file:///c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html';
const PORT = 9227;
const PROFILE = 'c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_profile_struct';
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
    const p=formalAttPayload;
    const topKeys=Object.keys(p);
    const dataKeys=Object.keys(p.data||{});
    const sampleKey=dataKeys[0];
    const sample=p.data[sampleKey];
    let sumU=0, sumT=0;
    for(const k of dataKeys){ const d=p.data[k]; if(d&&typeof d==='object'){ if(typeof d.untimely==='number') sumU+=d.untimely; if(typeof d.total==='number') sumT+=d.total; } }
    return JSON.stringify({ topKeys, sampleKey, sampleKeys: sample?Object.keys(sample):null, sampleUntimely: sample?sample.untimely:null, dataKeyCount: dataKeys.length, sumU, sumT });
  })()`,returnByValue:true});
  const o=JSON.parse(ev.result.result.value);
  console.log('topKeys:',JSON.stringify(o.topKeys));
  console.log('dataKeyCount:',o.dataKeyCount,'sampleKey:',o.sampleKey);
  console.log('sampleKeys:',JSON.stringify(o.sampleKeys));
  console.log('sampleUntimely:',o.sampleUntimely);
  console.log('SUM untimely (date-block level):',o.sumU,' total:',o.sumT);
  console.log('JS ERRORS:',errors.length);
  ws.close();chrome.kill('SIGKILL');process.exit(0);
}
main().catch(e=>{console.error('PROBE FAIL',e);chrome.kill('SIGKILL');process.exit(1);});
