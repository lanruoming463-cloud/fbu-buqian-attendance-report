const { spawn } = require('child_process');
const http = require('http');
const WebSocket = require('ws');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FILE = 'file:///c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html';
const PORT = 9244;
const PROFILE = 'c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_profile_1014e';
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
  await sleep(6000);
  const ev=await send('Runtime.evaluate',{expression:`(function(){
    const dayRe=/^\\d{4}-\\d{2}-\\d{2}$/;
    let yqr=0,sjqr=0,ydk=0,sjk=0;
    for(const k of Object.keys(attendPayload.data)){ if(!dayRe.test(k)) continue; const t=attendPayload.data[k].total; if(t){ yqr+=(t.yqr||0); sjqr+=(t.sjqr||0); ydk+=(t.ydk||0); sjk+=(t.sjk||0); } }
    const rate = yqr? (sjqr/yqr*100):0;
    return JSON.stringify({ yqr, sjqr, ydk, sjk, untimely: yqr-sjqr, rate: rate.toFixed(1) });
  })()`,returnByValue:true});
  const o=JSON.parse(ev.result.result.value);
  console.log('labor 应确认(yqr):',o.yqr);
  console.log('labor 实际确认(sjqr):',o.sjqr);
  console.log('labor 未及时确认(yqr-sjqr):',o.untimely);
  console.log('labor 应打卡(ydk):',o.ydk,' 实打卡(sjk):',o.sjk);
  console.log('labor 及时确认率:',o.rate+'%');
  console.log('JS ERRORS:',errors.length);
  ws.close();chrome.kill('SIGKILL');process.exit(0);
}
main().catch(e=>{console.error('PROBE FAIL',e);chrome.kill('SIGKILL');process.exit(1);});
