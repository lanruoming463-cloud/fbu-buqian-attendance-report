const { spawn } = require('child_process');
const http = require('http');
const WebSocket = require('ws');
const fs = require('fs');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FILE = 'file:///c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_injected_1016_18.html';
const PORT = 9268;
const PROFILE = 'c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_profile_101618';
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
  for(let i=0;i<40;i++){
    await sleep(1000);
    const e=await send('Runtime.evaluate',{expression:`typeof formalAttPayload!=='undefined' && typeof attendPayload!=='undefined'`,returnByValue:true});
    if(e.result&&e.result.result&&e.result.result.value===true){ready=true;break;}
  }
  console.log('READY:',ready);
  const ev=await send('Runtime.evaluate',{expression:`(function(){
    const out={};
    try{
      // 正式工 day blocks
      out.fpDays = formalAttPayload.days.slice(-5);
      ['2026-10-16','2026-10-17','2026-10-18'].forEach(d=>{
        const b=formalAttPayload.data[d];
        out['fp_'+d]=b?{total:b.total.total,normal:b.total.normal,abnormal:b.total.abnormal,untimely:b.total.untimely,timely:b.total.timely}:null;
      });
      out.fpOct=formalAttPayload.data['2026-10'].total;
      // 劳务工 day blocks
      out.apDays = attendPayload.days.slice(-5);
      ['2026-10-16','2026-10-17','2026-10-18'].forEach(d=>{
        const b=attendPayload.data[d];
        out['ap_'+d]=b?{total:b.total.total,yqr:b.total.yqr,sjqr:b.total.sjqr,unconfirmed:b.total.unconfirmed,ldk:b.total.ldk}:null;
      });
      // render 正式工 按月 2026-10
      genPayload=formalAttPayload; genSel='2026-10'; genMode='month'; renderGen(genPayload);
      out.genOct=(document.getElementById('genCards')?document.getElementById('genCards').textContent:'').replace(/\\s+/g,' ').slice(0,160);
      // render 正式工 按天 2026-10-18
      genSel='2026-10-18'; genMode='day'; renderGen(genPayload);
      out.genDay18=(document.getElementById('genCards')?document.getElementById('genCards').textContent:'').replace(/\\s+/g,' ').slice(0,160);
      // render 劳务工 按月 2026-10
      attendSel='2026-10'; attendMode='month'; renderAttend();
      out.attOct=(document.getElementById('attendCards')?document.getElementById('attendCards').textContent:'').replace(/\\s+/g,' ').slice(0,160);
      // render 劳务工 按天 2026-10-18
      attendSel='2026-10-18'; attendMode='day'; renderAttend();
      out.attDay18=(document.getElementById('attendCards')?document.getElementById('attendCards').textContent:'').replace(/\\s+/g,' ').slice(0,160);
      out.ok=true;
    }catch(e){ out.err=String(e&&e.stack||e); out.ok=false; }
    return JSON.stringify(out);
  })()`,returnByValue:true});
  console.log('EVAL:', ev.result.result.value);
  console.log('JS ERRORS:', errors.length, errors.slice(0,5));
  console.log('CONSOLE ERRORS:', consoleErrs.length, consoleErrs.slice(0,5));
  ws.close();chrome.kill('SIGKILL');process.exit(0);
}
main().catch(e=>{console.error('PROBE FAIL',e);chrome.kill('SIGKILL');process.exit(1);});
