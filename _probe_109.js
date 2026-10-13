const { spawn } = require('child_process');
const http = require('http');
const WebSocket = require('ws');

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FILE = 'file:///c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html';
const PORT = 9224;
const PROFILE = 'c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_profile_109';

function getJSON(url) {
  return new Promise((res, rej) => {
    http.get(url, (r) => { let d=''; r.on('data',c=>d+=c); r.on('end',()=>{try{res(JSON.parse(d));}catch(e){rej(e);}}); }).on('error',rej);
  });
}
const chrome = spawn(CHROME, ['--headless=new','--disable-gpu','--no-sandbox','--remote-debugging-port='+PORT,'--user-data-dir='+PROFILE,'about:blank'], { stdio:'ignore' });
function sleep(ms){return new Promise(r=>setTimeout(r,ms));}
async function main(){
  await sleep(2500);
  let targets;
  for(let i=0;i<20;i++){ try{targets=await getJSON(`http://127.0.0.1:${PORT}/json/list`); if(targets&&targets.length)break;}catch(e){} await sleep(500);}
  const page=targets.find(t=>t.type==='page')||targets[0];
  const ws=new WebSocket(page.webSocketDebuggerUrl,{perMessageDeflate:false});
  let id=0; const pending=new Map(); const errors=[];
  function send(method,params){return new Promise(res=>{const mid=++id;pending.set(mid,res);ws.send(JSON.stringify({id:mid,method,params:params||{}}));});}
  ws.on('message',raw=>{const m=JSON.parse(raw); if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);} if(m.method==='Runtime.exceptionThrown'||m.method==='Runtime.consoleAPICalled'){errors.push(m.method==='Runtime.exceptionThrown'?JSON.stringify(m.params.exceptionDetails):JSON.stringify(m.params.args));}});
  await new Promise(r=>ws.on('open',r));
  await send('Page.enable'); await send('Runtime.enable');
  await send('Page.navigate',{url:FILE});
  await sleep(4000);
  const ev=await send('Runtime.evaluate',{expression:`(function(){
    function blkInfo(p,key){ const d=p.data&&p.data[key]; if(!d) return null; const t=d.total, u=d.untimely, ti=d.timely; const wh=(d.warehouse||[]).length, g=(d.group||[]).length; return {total:t,untimely:u,timely:ti,wh,group:g}; }
    const fa=formalAttPayload, at=attendPayload;
    const faDay=blkInfo(fa,'2026-10-09'); const atDay=blkInfo(at,'2026-10-09');
    return JSON.stringify({
      faMonths:fa.months, faDaysLast:fa.days.slice(-5), faDay109:faDay,
      atMonths:at.months, atDaysLast:at.days.slice(-5), atDay109:atDay
    });
  })()`,returnByValue:true});
  const o=JSON.parse(ev.result.result.value);
  console.log('formalAtt months:',o.faMonths.join(','));
  console.log('formalAtt last days:',o.faDaysLast.join(','));
  console.log('formalAtt 2026-10-09 block:',JSON.stringify(o.faDay109));
  console.log('attend months:',o.atMonths.join(','));
  console.log('attend last days:',o.atDaysLast.join(','));
  console.log('attend 2026-10-09 block:',JSON.stringify(o.atDay109));
  const ok = o.faDaysLast.includes('2026-10-09') && o.atDaysLast.includes('2026-10-09') && o.faDay109 && o.faDay109.total>0 && o.atDay109 && o.atDay109.total>0;
  console.log('=== 10.9 PRESENT IN BOTH & HAS DATA:', ok, '===');
  console.log('=== JS ERRORS ('+errors.length+') ==='); errors.slice(0,20).forEach(e=>console.log(e));
  ws.close(); chrome.kill('SIGKILL'); process.exit(0);
}
main().catch(e=>{console.error('PROBE FAIL',e);chrome.kill('SIGKILL');process.exit(1);});
