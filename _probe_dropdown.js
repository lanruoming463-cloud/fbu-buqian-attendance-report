const { spawn } = require('child_process');
const http = require('http');
const WebSocket = require('ws');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FILE = 'file:///c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html';
const PORT = 9234;
const PROFILE = 'c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_profile_dd';
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
  // Navigate to 正式工 考勤确认及时率 view and open the day dropdown
  const ev=await send('Runtime.evaluate',{expression:`(function(){
    // assume current view default; switch to gen formal att via showCell if available
    try { if (typeof showCell==='function') showCell('formal','att'); } catch(e){}
    // open dropdown in day mode
    try { if (typeof setModeGen==='function') setModeGen('day'); else if (typeof setMode==='function') setMode('day'); } catch(e){}
    // trigger the shared dropdown
    try { if (typeof toggleGenDropdownShared==='function') toggleGenDropdownShared(); } catch(e){}
    var dd=document.getElementById('dropdown');
    var items = dd ? Array.from(dd.querySelectorAll('.item')).slice(0,12).map(function(e){return e.textContent;}) : [];
    var groups = dd ? Array.from(dd.querySelectorAll('.group')).slice(0,6).map(function(e){return e.textContent;}) : [];
    return JSON.stringify({ items, groups, hasDd: !!dd, hidden: dd?dd.classList.contains('hidden'):null });
  })()`,returnByValue:true});
  const o=JSON.parse(ev.result.result.value);
  console.log('dropdown hidden:',o.hidden,' hasDd:',o.hasDd);
  console.log('first 12 day items:',JSON.stringify(o.items));
  console.log('first groups:',JSON.stringify(o.groups));
  // check descending: items should be 10月12日,10月11日,... (text like M月D日)
  const dayRe=/^(\d+)月(\d+)日/;
  const parsed=o.items.map(function(t){var mm=t.match(dayRe);return mm?[+mm[1],+mm[2]]:null;}).filter(Boolean);
  let desc=true;
  for(let i=1;i<parsed.length;i++){ var a=parsed[i-1],b=parsed[i]; var va=a[0]*100+a[1], vb=b[0]*100+b[1]; if(vb>va) desc=false; }
  console.log('day items strictly descending (newest first):',desc,' parsedCount:',parsed.length);
  console.log('JS ERRORS:',errors.length);
  ws.close();chrome.kill('SIGKILL');process.exit(0);
}
main().catch(e=>{console.error('PROBE FAIL',e);chrome.kill('SIGKILL');process.exit(1);});
