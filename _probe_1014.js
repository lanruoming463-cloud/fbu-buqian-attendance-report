const { spawn } = require('child_process');
const http = require('http');
const WebSocket = require('ws');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FILE = 'file:///c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html';
const PORT = 9240;
const PROFILE = 'c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_profile_1014';
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
    function agg(p){ let u=0,t=0; for(const k of Object.keys(p.data)){ if(!dayRe.test(k)) continue; const d=p.data[k]; if(d&&d.total&&typeof d.total==='object'){ if(typeof d.total.untimely==='number') u+=d.total.untimely; if(typeof d.total.total==='number') t+=d.total.total; } } return {u,t}; }
    const fa=agg(formalAttPayload);
    const at=agg(attendPayload);
    return JSON.stringify({
      faU:fa.u, faT:fa.t,
      atU:at.u, atT:at.t,
      faHas1014: !!formalAttPayload.data['2026-10-14'],
      atHas1014: !!attendPayload.data['2026-10-14'],
      faMonths: formalAttPayload.months,
      attMonths: attendPayload.months
    });
  })()`,returnByValue:true});
  const o=JSON.parse(ev.result.result.value);
  console.log('formalAtt DAY untimely:',o.faU,' (expect 2679) match:',o.faU===2679);
  console.log('formalAtt DAY total:',o.faT,' (expect 124996) match:',o.faT===124996);
  console.log('attend DAY untimely:',o.atU);
  console.log('attend DAY total:',o.atT);
  console.log('formalAtt has 2026-10-14 key:',o.faHas1014);
  console.log('attend has 2026-10-14 key:',o.atHas1014);
  console.log('formalAtt months:',JSON.stringify(o.faMonths));
  console.log('attend months:',JSON.stringify(o.attMonths));
  console.log('JS ERRORS:',errors.length);
  ws.close();chrome.kill('SIGKILL');process.exit(0);
}
main().catch(e=>{console.error('PROBE FAIL',e);chrome.kill('SIGKILL');process.exit(1);});
