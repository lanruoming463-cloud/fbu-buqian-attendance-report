const { spawn } = require('child_process');
const http = require('http');
const WebSocket = require('ws');
const fs = require('fs');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FILE = 'file:///c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html';
const PORT = 9251;
const PROFILE = 'c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_profile_signint';
const SHOT = 'c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_dbg_signint.png';
function getJSON(url){return new Promise((res,rej)=>{http.get(url,r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>{try{res(JSON.parse(d));}catch(e){rej(e);}});}).on('error',rej);});}
const chrome=spawn(CHROME,['--headless=new','--disable-gpu','--no-sandbox','--remote-debugging-port='+PORT,'--user-data-dir='+PROFILE,'--window-size=1400,2400','about:blank'],{stdio:'ignore'});
function sleep(ms){return new Promise(r=>setTimeout(r,ms));}
async function main(){
  await sleep(2500);
  let targets;
  for(let i=0;i<20;i++){try{targets=await getJSON(`http://127.0.0.1:${PORT}/json/list`);if(targets&&targets.length)break;}catch(e){}await sleep(500);}
  const page=targets.find(t=>t.type==='page')||targets[0];
  const ws=new WebSocket(page.webSocketDebuggerUrl,{perMessageDeflate:false});
  let id=0;const pending=new Map();const errors=[];
  function send(m,p){return new Promise(r=>{const mid=++id;pending.set(mid,r);ws.send(JSON.stringify({id:mid,method:m,params:p||{}}));});}
  ws.on('message',raw=>{const m=JSON.parse(raw);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);}if(m.method==='Runtime.exceptionThrown'){errors.push(JSON.stringify(m.params.exceptionDetails).slice(0,400));}});
  await new Promise(r=>ws.on('open',r));
  await send('Page.enable');await send('Runtime.enable');
  await send('Page.navigate',{url:FILE});
  await sleep(6000);
  // 模拟：切到补签率视图 + 正式工 + 按月 2026-07
  const ev=await send('Runtime.evaluate',{expression:`(function(){
    const out={};
    try{
      // 尝试直接操作全局（sign 视图变量）
      if (typeof selected !== 'undefined') {
        selected = '2026-07'; mode = 'month'; render();
        const d = currentData();
        out.afterSelect = { selected, total: d.total, done: d.done, ing: d.ing, majorN: (d.major||[]).length };
      } else { out.noSelected = true; }
      // 读取 KPI DOM
      const kpiEls = document.querySelectorAll('.kpi, .kpi-card, [class*=kpi]');
      out.kpiTexts = Array.from(kpiEls).slice(0,8).map(e=>e.textContent.trim().slice(0,40));
      out.bodyErr = window.__lastErr || null;
    }catch(e){ out.err = String(e); }
    return JSON.stringify(out);
  })()`,returnByValue:true});
  console.log(ev.result.result.value);
  await sleep(1000);
  const shot=await send('Page.captureScreenshot',{format:'png'});
  fs.writeFileSync(SHOT, Buffer.from(shot.result.data,'base64'));
  console.log('screenshot saved:',SHOT);
  console.log('JS ERRORS:',errors.length, errors.slice(0,3));
  ws.close();chrome.kill('SIGKILL');process.exit(0);
}
main().catch(e=>{console.error('PROBE FAIL',e);chrome.kill('SIGKILL');process.exit(1);});
