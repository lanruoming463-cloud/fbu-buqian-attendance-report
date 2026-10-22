const { spawn } = require('child_process');
const http = require('http');
const WebSocket = require('ws');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FILE = 'file:///c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/%E8%A1%A5%E7%AD%BE%E6%B5%81%E7%A8%8B_%E8%A1%A5%E7%AD%BE%E7%BB%9F%E8%AE%A1.html';
const PORT = 9296;
const PROFILE = 'c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_profile_1020';
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
  for(let i=0;i<40;i++){await sleep(1000);const e=await send('Runtime.evaluate',{expression:`typeof showCell!=='undefined'&&typeof renderAttend!=='undefined'&&typeof renderGen!=='undefined'`,returnByValue:true});if(e.result&&e.result.result&&e.result.result.value===true){ready=true;break;}}
  console.log('READY:',ready);
  const r=await send('Runtime.evaluate',{expression:`(function(){ try{
    const o={};
    o.fDays=formalAttPayload.days.slice(-5);
    o.lDays=attendPayload.days.slice(-5);
    o.fMonth=formalAttPayload.data['2026-10'].total;
    o.lMonthTot=(function(){var AD=attendPayload.days.filter(function(d){return d.indexOf('2026-10')===0;});var t={yqr:0,sjqr:0};AD.forEach(function(d){var b=attendPayload.data[d];if(!b)return;t.yqr+=b.total.yqr;t.sjqr+=b.total.sjqr;});return t;})();
    // 正式工考勤 day 视图取 10-20
    showCell('formal','att');
    setModeGen('day');
    o.fDayPicker=document.getElementById('genDateLabel')?document.getElementById('genDateLabel').textContent:'';
    // 劳务工考勤 day 视图取 10-20
    showCell('labor','att');
    attendDayStart=attendDayEnd='2026-10-20';
    setModeAttend('day');
    o.lDayPicker=document.getElementById('btnPicker')?document.getElementById('btnPicker').textContent:'';
    o.lDayCards=document.getElementById('attendCards')?document.getElementById('attendCards').textContent:'';
    return JSON.stringify(o);
  }catch(e){ return JSON.stringify({FATAL:e.message}); } })()`,returnByValue:true});
  const v=r.result&&r.result.result?r.result.result.value:null;
  console.log(v);
  console.log('JS_ERRORS:',errors.length, errors.slice(0,3));
  chrome.kill();process.exit(0);
}
main().catch(e=>{console.error('FATAL',e);chrome.kill();process.exit(1);});
