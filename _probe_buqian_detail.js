const { spawn } = require('child_process');
const http = require('http');
const WebSocket = require('ws');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FILE = 'file:///c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html';
const PORT = 9293;
const PROFILE = 'c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_profile_buqian7';
function getJSON(url){return new Promise((res,rej)=>{http.get(url,r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>{try{res(JSON.parse(d));}catch(e){rej(e);}});}).on('error',rej);});}
const chrome=spawn(CHROME,['--headless=new','--disable-gpu','--no-sandbox','--remote-debugging-port='+PORT,'--user-data-dir='+PROFILE,'--window-size=1400,2400','about:blank'],{stdio:'ignore'});
function sleep(ms){return new Promise(r=>setTimeout(r,ms));}
async function main(){
  await sleep(2500);
  let targets;
  for(let i=0;i<30;i++){try{targets=await getJSON(`http://127.0.0.1:${PORT}/json/list`);if(targets&&targets.length)break;}catch(e){}await sleep(500);}
  const page=targets.find(t=>t.type==='page')||targets[0];
  const ws=new WebSocket(page.webSocketDebuggerUrl,{perMessageDeflate:false});
  let id=0;const pending=new Map();const errors=[];
  function send(m,p){return new Promise(r=>{const mid=++id;pending.set(mid,r);ws.send(JSON.stringify({id:mid,method:m,params:p||{}}));});}
  ws.on('message',raw=>{const m=JSON.parse(raw);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);}if(m.method==='Runtime.exceptionThrown'){errors.push(((m.params.exceptionDetails||{}).exception||{}).description||'exc');}});
  await new Promise(r=>ws.on('open',r));
  await send('Page.enable');await send('Runtime.enable');
  await send('Page.navigate',{url:FILE});
  let ready=false;
  for(let i=0;i<40;i++){await sleep(1000);const e=await send('Runtime.evaluate',{expression:`typeof showCell!=='undefined'`,returnByValue:true});if(e.result&&e.result.result&&e.result.result.value===true){ready=true;break;}}
  console.log('READY:',ready);
  const r=await send('Runtime.evaluate',{expression:`(function(){
    const o={};
    showCell('formal','sign');
    // KPI regression (weight=1 must keep days sums identical)
    o.kpi={t:document.getElementById('cTotal').textContent,d:document.getElementById('cDone').textContent,r:document.getElementById('cIng').textContent};
    // expand a group with employees
    selected='2026-09'; render(); buildEmpIndex();
    const k0=Object.keys(empIndex).find(k=>empIndex[k].length>1);
    const parts=k0.split('|');
    const row=[...document.querySelectorAll('#grpBody tr.group-row')].find(r=>r.dataset.major===parts[0]&&r.dataset.region===parts[1]&&r.dataset.wh===parts[2]&&r.dataset.group===parts[3]);
    row.click();
    const sub=document.querySelector('#grpBody tr.emp-subrow');
    o.headCells=sub?[...sub.querySelectorAll('thead th')].map(t=>t.textContent.trim()):null;
    o.nRows=sub?sub.querySelectorAll('tbody tr').length:0;
    o.firstRows=sub?[...sub.querySelectorAll('tbody tr')].slice(0,3).map(tr=>[...tr.children].map(c=>c.textContent.trim())):null;
    // Top10 days aggregation check (weight=1)
    buildTopEmp();
    const rk=Object.keys(topEmpIndex).find(k=>topEmpIndex[k].length>0);
    o.topSample=topEmpIndex[rk].slice(0,2).map(e=>({n:e.name,c:e.count,d:e.done}));
    // labor regression
    showCell('labor','sign');
    const lrow=[...document.querySelectorAll('#grpBody tr.group-row')].find(r=>true);
    if(lrow){lrow.click();const lsub=document.querySelector('#grpBody tr.emp-subrow');
      o.laborHead=lsub?[...lsub.querySelectorAll('thead th')].map(t=>t.textContent.trim()):null;}
    return JSON.stringify(o);
  })()`,returnByValue:true});
  console.log(r.result.result.value);
  console.log('JS ERRORS:', errors.length, errors.slice(0,3));
  ws.close();chrome.kill('SIGKILL');process.exit(0);
}
main().catch(e=>{console.error('PROBE FAIL',e);chrome.kill('SIGKILL');process.exit(1);});
