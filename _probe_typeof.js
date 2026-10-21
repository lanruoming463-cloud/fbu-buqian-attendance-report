const { spawn } = require('child_process');
const http = require('http');
const WebSocket = require('ws');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FILE = 'file:///c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/%E8%A1%A5%E7%AD%BE%E6%B5%81%E7%A8%8B_%E8%A1%A5%E7%AD%BE%E7%BB%9F%E8%AE%A1.html';
const PORT = 9293;
const PROFILE = 'c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_profile_typeof';
function getJSON(url){return new Promise((res,rej)=>{http.get(url,r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>{try{res(JSON.parse(d));}catch(e){rej(e);}});}).on('error',rej);});}
const chrome=spawn(CHROME,['--headless=new','--disable-gpu','--no-sandbox','--remote-debugging-port='+PORT,'--user-data-dir='+PROFILE,'--window-size=1400,2400','about:blank'],{stdio:'ignore'});
function sleep(ms){return new Promise(r=>setTimeout(r,ms));}
async function main(){
  await sleep(2500);
  let targets;
  for(let i=0;i<30;i++){try{targets=await getJSON(`http://127.0.0.1:${PORT}/json/list`);if(targets&&targets.length)break;}catch(e){}await sleep(500);}
  const page=targets.find(t=>t.type==='page')||targets[0];
  const ws=new WebSocket(page.webSocketDebuggerUrl,{perMessageDeflate:false});
  let id=0;const pending=new Map();
  function send(m,p){return new Promise(r=>{const mid=++id;pending.set(mid,r);ws.send(JSON.stringify({id:mid,method:m,params:p||{}}));});}
  ws.on('message',raw=>{const m=JSON.parse(raw);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);}});
  await new Promise(r=>ws.on('open',r));
  await send('Page.enable');await send('Runtime.enable');
  await send('Page.navigate',{url:FILE});
  let ready=false;
  for(let i=0;i<40;i++){await sleep(1000);const e=await send('Runtime.evaluate',{expression:`typeof showCell!=='undefined'`,returnByValue:true});if(e.result&&e.result.result&&e.result.result.value===true){ready=true;break;}}
  console.log('READY:',ready);
  let attReady=false;
  for(let i=0;i<30;i++){await sleep(1000);const e2=await send('Runtime.evaluate',{expression:`typeof renderAttend!=='undefined'`,returnByValue:true});if(e2.result&&e2.result.result&&e2.result.result.value===true){attReady=true;console.log('ATT_READY after',i+1,'s');break;}}
  console.log('ATT_READY:',attReady);
  const r=await send('Runtime.evaluate',{expression:`(function(){var o={};o.typeofRenderAttend=typeof renderAttend;o.typeofShowCell=typeof showCell;o.typeofRenderGen=typeof renderGen;try{showCell('labor','att');o.afterCall=true;o.attHead=[...document.querySelectorAll('#tableAttMajor thead th')].map(t=>t.textContent.trim());o.attRows=document.querySelectorAll('#attMajorBody tr').length;}catch(e){o.err=e.message;}return JSON.stringify(o);})()`,returnByValue:true});
  console.log(r.result.result.value);
  chrome.kill();process.exit(0);
}
main().catch(e=>{console.error('FATAL',e);chrome.kill();process.exit(1);});
