const { spawn } = require('child_process');
const http = require('http');
const WebSocket = require('ws');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FILE = 'file:///c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html';
const PORT = 9283;
const PROFILE = 'c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_profile_buqian2';
function getJSON(url){return new Promise((res,rej)=>{http.get(url,r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>{try{res(JSON.parse(d));}catch(e){rej(e);}});}).on('error',rej);});}
const chrome=spawn(CHROME,['--headless=new','--disable-gpu','--no-sandbox','--remote-debugging-port='+PORT,'--user-data-dir='+PROFILE,'--window-size=1400,2400','about:blank'],{stdio:'ignore'});
function sleep(ms){return new Promise(r=>setTimeout(r,ms));}
async function main(){
  await sleep(2500);
  let targets;
  for(let i=0;i<30;i++){try{targets=await getJSON(`http://127.0.0.1:${PORT}/json/list`);if(targets&&targets.length)break;}catch(e){}await sleep(500);}
  const page=targets.find(t=>t.type==='page')||targets[0];
  const ws=new WebSocket(page.webSocketDebuggerUrl,{perMessageDeflate:false});
  let id=0;const pending=new Map();const errors=[];const consoleErrs=[];
  function send(m,p){return new Promise(r=>{const mid=++id;pending.set(mid,r);ws.send(JSON.stringify({id:mid,method:m,params:p||{}}));});}
  ws.on('message',raw=>{const m=JSON.parse(raw);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);}if(m.method==='Runtime.exceptionThrown'){errors.push(((m.params.exceptionDetails||{}).exception||{}).description||'exc');}if(m.method==='Runtime.consoleAPICalled'&&m.params.type==='error'){consoleErrs.push((m.params.args||[]).map(a=>a.value||a.description||'').join(' ').slice(0,400));}});
  await new Promise(r=>ws.on('open',r));
  await send('Page.enable');await send('Runtime.enable');
  await send('Page.navigate',{url:FILE});
  let ready=false;
  for(let i=0;i<40;i++){await sleep(1000);const e=await send('Runtime.evaluate',{expression:`typeof showCell!=='undefined'`,returnByValue:true});if(e.result&&e.result.result&&e.result.result.value===true){ready=true;break;}}
  console.log('READY:',ready);
  async function ev(expr){const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true});const v=r.result&&r.result.result;return JSON.stringify(v&&v.value!==undefined?v.value:(r.result&&r.result.exceptionDetails&&r.result.exceptionDetails.text));}

  await send('Runtime.evaluate',{expression:`showCell('formal','sign')`,returnByValue:true});
  await sleep(800);
  // per-month KPI by simulating month switch: set selected then render
  const months = await ev(`(function(){
    const out={};
    try{
      for(const ym of ['2026-06','2026-07','2026-08','2026-09']){
        selected = ym; render();
        out[ym] = {t:document.getElementById('cTotal').textContent, d:document.getElementById('cDone').textContent, r:document.getElementById('cIng').textContent};
      }
      // group expand test on 2026-09
      selected='2026-09'; render();
      const grpRow=[...document.querySelectorAll('#grpBody tr.group-row')].find(r=>parseInt((r.children[1].textContent||'').replace(/,/g,''),10)>50);
      if(grpRow){ grpRow.click();
        const sub=document.querySelector('#grpBody tr.emp-subrow');
        out.expand={found:true, headCells:sub?[...sub.querySelectorAll('thead th')].map(t=>t.textContent.trim()):null, bodyFirst:sub&&sub.querySelector('tbody tr')?[...sub.querySelector('tbody tr').children].map(c=>c.textContent.trim()):null};
      } else out.expand={found:false};
      // top10 employee row sample
      const trs=[...document.querySelectorAll('#topBody tr.top-emp-row')].slice(0,3);
      out.topRows=trs.map(r=>[...r.children].map(c=>c.textContent.trim()));
      // note body visible text
      out.note=(document.getElementById('note-body')||document.body).textContent.includes('考勤为基');
      out.majorTopRow=document.querySelector('#majorBody tr')?[...document.querySelector('#majorBody tr').children].map(c=>c.textContent.trim()):null;
      out.ok=true;
    }catch(e){out.err=String(e&&e.stack||e);out.ok=false;}
    return JSON.stringify(out);
  })()`);
  console.log('MONTHS:', months);
  console.log('JS ERRORS:', errors.length, errors.slice(0,3));
  console.log('CONSOLE ERRORS:', consoleErrs.length, consoleErrs.slice(0,3));
  ws.close();chrome.kill('SIGKILL');process.exit(0);
}
main().catch(e=>{console.error('PROBE FAIL',e);chrome.kill('SIGKILL');process.exit(1);});
