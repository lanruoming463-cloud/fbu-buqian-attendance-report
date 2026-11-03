const { spawn } = require('child_process');
const http = require('http');
const WebSocket = require('ws');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FILE = 'file:///c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html';
const PORT = 9291;
const PROFILE = 'c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_profile_oct';
function getJSON(url){return new Promise((res,rej)=>{http.get(url,r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>{try{res(JSON.parse(d));}catch(e){rej(e);}});}).on('error',rej);});}
const chrome=spawn(CHROME,['--headless=new','--disable-gpu','--no-sandbox','--remote-debugging-port='+PORT,'--user-data-dir='+PROFILE,'--window-size=1400,2400','about:blank'],{stdio:'ignore'});
function sleep(ms){return new Promise(r=>setTimeout(r,ms));}
let id=0;const pending=new Map();const errors=[];const consoleErrs=[];
async function main(){
  await sleep(2500);
  let targets;
  for(let i=0;i<30;i++){try{targets=await getJSON(`http://127.0.0.1:${PORT}/json/list`);if(targets&&targets.length)break;}catch(e){}await sleep(500);}
  const page=targets.find(t=>t.type==='page')||targets[0];
  const ws=new WebSocket(page.webSocketDebuggerUrl,{perMessageDeflate:false});
  function send(m,p){return new Promise(r=>{const mid=++id;pending.set(mid,r);ws.send(JSON.stringify({id:mid,method:m,params:p||{}}));});}
  ws.on('message',raw=>{const m=JSON.parse(raw);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);}if(m.method==='Runtime.exceptionThrown'){errors.push(((m.params.exceptionDetails||{}).exception||{}).description||'exc');}if(m.method==='Runtime.consoleAPICalled'&&m.params.type==='error'){consoleErrs.push((m.params.args||[]).map(a=>a.value||a.description||'').join(' ').slice(0,400));}});
  await new Promise(r=>ws.on('open',r));
  await send('Page.enable');await send('Runtime.enable');
  await send('Page.navigate',{url:FILE});
  let ready=false;
  for(let i=0;i<50;i++){await sleep(1000);const e=await send('Runtime.evaluate',{expression:`typeof showCell!=='undefined'`,returnByValue:true});if(e.result&&e.result.result&&e.result.result.value===true){ready=true;break;}}
  async function ev(expr){const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true});const v=r.result&&r.result.result;return v&&v.value!==undefined?v.value:(r.result&&r.result.exceptionDetails&&r.result.exceptionDetails.text);}
  console.log('READY:',ready);
  console.log('formalPayload.months=', await ev('JSON.stringify(formalPayload.months)'));
  console.log('laborPayload.months=', await ev('JSON.stringify(laborPayload.months)'));
  // 正式工 选 2026-10
  await ev("wt='formal';sec='sign';selected='2026-10';setMode('month');render();");
  await sleep(600);
  console.log('FORMAL 2026-10 KPI total/done/rate=',
    await ev("document.getElementById('cTotal').textContent+' / '+document.getElementById('cDone').textContent+' / '+document.getElementById('cIng').textContent"));
  const fOctRows = await ev("(function(){var n=0;document.querySelectorAll('#grpBody tr.major-row2').forEach(()=>n++);return n;})()");
  console.log('FORMAL 2026-10 major rows=', fOctRows);
  // 劳务工 选 2026-10（先切到 labor + sign）
  await ev("wt='labor';sec='sign';selected='2026-10';setMode('month');render();");
  await sleep(600);
  console.log('LABOR 2026-10 KPI total/done/rate=',
    await ev("document.getElementById('cTotal').textContent+' / '+document.getElementById('cDone').textContent+' / '+document.getElementById('cIng').textContent"));
  const lOctRows = await ev("(function(){var n=0;document.querySelectorAll('#grpBody tr.major-row2').forEach(()=>n++);return n;})()");
  console.log('LABOR 2026-10 major rows=', lOctRows);
  // 劳务工 2026-10 Top10 区域数
  const lTop = await ev("Object.keys(laborPayload.topEmpIndexM['2026-10']||{}).length");
  console.log('LABOR topEmpIndexM 2026-10 区域数=', lTop);
  console.log('JS exceptions:', errors.length, JSON.stringify(errors.slice(0,5)));
  console.log('CONSOLE errors:', consoleErrs.length, JSON.stringify(consoleErrs.slice(0,5)));
  ws.close();chrome.kill();process.exit(0);
}
main().catch(e=>{console.error('PROBE FAIL',e);process.exit(1);});
setTimeout(()=>{console.error('TIMEOUT');process.exit(2);}, 120000);
