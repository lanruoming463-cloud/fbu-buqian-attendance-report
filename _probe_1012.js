const { spawn } = require('child_process');
const http = require('http');
const WebSocket = require('ws');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FILE = 'file:///c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html';
const PORT = 9233;
const PROFILE = 'c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_profile_1012';
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
    const dayRe=/^\\d{4}-\\d{2}-\\d{2}$/;
    function agg(p){ let u=0,t=0; for(const k of Object.keys(p.data)){ if(!dayRe.test(k)) continue; const d=p.data[k]; if(d&&d.total&&typeof d.total==='object'){ if(typeof d.total.untimely==='number') u+=d.total.untimely; if(typeof d.total.total==='number') t+=d.total.total; } } return {u,t}; }
    const fa=agg(formalAttPayload); const at=agg(attendPayload);
    return JSON.stringify({
      faU:fa.u, faT:fa.t, atU:at.u, atT:at.t, faDays: formalAttPayload.days, atDays: attendPayload.days
    });
  })()`,returnByValue:true});
  const o=JSON.parse(ev.result.result.value);
  console.log('formalAtt DAY untimely:',o.faU,' (expect 2477) match:',o.faU===2477);
  console.log('formalAtt DAY total:',o.faT,' (expect 121078) match:',o.faT===121078);
  console.log('attend DAY untimely:',o.atU,' attend DAY total:',o.atT);
  const hasFa = o.faDays.includes('2026-10-10')&&o.faDays.includes('2026-10-11')&&o.faDays.includes('2026-10-12');
  const hasAt = o.atDays.includes('2026-10-10')&&o.atDays.includes('2026-10-11')&&o.atDays.includes('2026-10-12');
  console.log('formalAtt has 10.10-10.12 days:',hasFa);
  console.log('attend has 10.10-10.12 days:',hasAt);
  console.log('JS ERRORS:',errors.length);
  ws.close();chrome.kill('SIGKILL');process.exit(0);
}
main().catch(e=>{console.error('PROBE FAIL',e);chrome.kill('SIGKILL');process.exit(1);});
