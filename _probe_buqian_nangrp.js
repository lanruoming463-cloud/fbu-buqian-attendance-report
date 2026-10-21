const { spawn } = require('child_process');
const http = require('http');
const WebSocket = require('ws');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FILE = 'file:///c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html';
const PORT = 9301;
const PROFILE = 'c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_profile_buqian11';
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
  for(let i=0;i<40;i++){await sleep(1000);const e=await send('Runtime.evaluate',{expression:`typeof showCell!=='undefined'`,returnByValue:true});if(e.result&&e.result.result&&e.result.result.value===true)break;}
  await send('Runtime.evaluate',{expression:`showCell('formal','sign')`,returnByValue:true});
  await sleep(800);
  const r=await send('Runtime.evaluate',{expression:`(function(){
    var o={};
    selected='2026-06'; render(); buildEmpIndex();
    // 找 grp 表中显示 nan 的组行
    var nanRows=[...document.querySelectorAll('#grpBody tr.group-row')].filter(function(r){return r.dataset.group==='nan'||r.dataset.wh==='nan';});
    o.nanGrpRows=nanRows.length;
    if(nanRows.length){var r0=nanRows[0];o.nanKey=r0.dataset.major+'|'+r0.dataset.region+'|'+r0.dataset.wh+'|'+r0.dataset.group;
      o.nanInEmpIndex=!!empIndex[o.nanKey];
      r0.click();
      var sub=document.querySelector('#grpBody tr.emp-subrow');
      o.expandText=sub?sub.textContent.trim().slice(0,50):null;}
    // 部门直属键是否存在于 empIndex
    var dk=Object.keys(empIndex).filter(function(k){return k.indexOf('部门直属')>=0;});
    o.deptKeys=dk.length; o.deptSample=dk.slice(0,2);
    return JSON.stringify(o);
  })()`,returnByValue:true});
  console.log(r.result.result.value);
  console.log('JS ERRORS:', errors.length);
  ws.close();chrome.kill('SIGKILL');process.exit(0);
}
main().catch(e=>{console.error('PROBE FAIL',e);chrome.kill('SIGKILL');process.exit(1);});
