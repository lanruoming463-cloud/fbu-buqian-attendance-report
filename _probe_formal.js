const { spawn } = require('child_process');
const http = require('http');
const WebSocket = require('ws');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FILE = 'file:///c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_injected_formal.html';
const PORT = 9273;
const PROFILE = 'c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_profile_formal';
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
  ws.on('message',raw=>{const m=JSON.parse(raw);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);}if(m.method==='Runtime.exceptionThrown'){errors.push(JSON.stringify(m.params.exceptionDetails).slice(0,300));}if(m.method==='Runtime.consoleAPICalled'&&m.params.type==='error'){consoleErrs.push((m.params.args||[]).map(a=>a.value||a.description||'').join(' ').slice(0,300));}});
  await new Promise(r=>ws.on('open',r));
  await send('Page.enable');await send('Runtime.enable');
  await send('Page.navigate',{url:FILE});
  let ready=false;
  for(let i=0;i<40;i++){await sleep(1000);const e=await send('Runtime.evaluate',{expression:`typeof formalPayload!=='undefined'`,returnByValue:true});if(e.result&&e.result.result&&e.result.result.value===true){ready=true;break;}}
  console.log('READY:',ready);
  const ev=await send('Runtime.evaluate',{expression:`(function(){
    const out={};
    try{
      // 1) 直接校验数据聚合
      let aggSpain=0, aggGrand=0; const perMonth={};
      formalPayload.months.forEach(m=>{ const v=formalPayload.data[m]; aggGrand+=v.total; v.detail.forEach(r=>{if(r.region==='西班牙区'){aggSpain+=r.total; perMonth[m]=r.total;}}); });
      out.aggSpain=aggSpain; out.aggGrand=aggGrand; out.perMonthSpain=perMonth;
      out.allEmp=formalPayload.allEmp.length;
      out.spainOtherInAllEmp = formalPayload.allEmp.filter(e=>e.region==='西班牙区'&&String(e.补签事由).trim()==='其他').length;
      // 2) 渲染正式工补签率 按月 2026-09
      curWt='formal'; curSec='sign'; payload=formalPayload; mode='month'; selected='2026-09'; render();
      const spRow=document.querySelector('#detailBody tr.region-row2[data-region="西班牙区"]');
      out.spain2026_09 = spRow ? spRow.textContent.replace(/\\s+/g,' ').trim() : 'NOT FOUND';
      const euMaj=document.querySelector('#majorBody tr[data-major="欧洲区"]');
      out.europe2026_09 = euMaj ? euMaj.textContent.replace(/\\s+/g,' ').trim() : 'NOT FOUND';
      out.cTotal2026_09 = document.getElementById('cTotal') ? document.getElementById('cTotal').textContent : 'NA';
      // 3) 渲染 2026-07（其他最多的月）
      selected='2026-07'; render();
      const spRow7=document.querySelector('#detailBody tr.region-row2[data-region="西班牙区"]');
      out.spain2026_07 = spRow7 ? spRow7.textContent.replace(/\\s+/g,' ').trim() : 'NOT FOUND';
      // 4) Top10 西班牙区（组下明细/排名不含被剔除者）
      const topRows=[...document.querySelectorAll('#topBody tr')].map(r=>r.textContent.replace(/\\s+/g,' ').trim()).slice(0,12);
      out.topSample=topRows;
    }catch(e){ out.err=String(e&&e.stack||e); }
    return JSON.stringify(out);
  })()`,returnByValue:true});
  console.log('EVAL:', ev.result.result.value);
  console.log('JS ERRORS:', errors.length, errors.slice(0,5));
  console.log('CONSOLE ERRORS:', consoleErrs.length, consoleErrs.slice(0,5));
  ws.close();chrome.kill('SIGKILL');process.exit(0);
}
main().catch(e=>{console.error('PROBE FAIL',e);chrome.kill('SIGKILL');process.exit(1);});
