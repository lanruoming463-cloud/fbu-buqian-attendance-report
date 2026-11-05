// V20 验证探针: 载入注入后 HTML, 检查页面 JS 异常 + 渲染 KPI + 确认 4 条已剔除
const { spawn } = require('child_process');
const http = require('http');
const WebSocket = require('ws');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const URL = 'file:///C:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html';
const PORT = 9228;
const getJSON = p => new Promise((res,rej)=>http.get({host:'127.0.0.1',port:PORT,path:p},r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>{try{res(JSON.parse(d))}catch(e){rej(e)}})}).on('error',rej));
const sleep = ms => new Promise(r=>setTimeout(r,ms));
(async()=>{
  const chrome = spawn(CHROME,['--headless=new','--remote-debugging-port='+PORT,'--remote-allow-origins=*','--disable-gpu','--no-sandbox','--disable-dev-shm-usage','--user-data-dir=C:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_1105','about:blank'],{stdio:'ignore'});
  let up=false;
  for(let i=0;i<40;i++){ await sleep(500); try{ await getJSON('/json'); up=true; break; }catch(e){} }
  if(!up){ console.error('PORT FAIL'); chrome.kill('SIGKILL'); process.exit(1); }
  const targets = await getJSON('/json');
  const page = targets.find(t=>t.type==='page') || targets[0];
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id=0; const pending={}; const errs=[];
  ws.on('message',m=>{const o=JSON.parse(m); if(o.id&&pending[o.id]){pending[o.id](o);delete pending[o.id];} if(o.method==='Runtime.exceptionThrown') errs.push(o.params.exceptionDetails.text);});
  const send=(method,params={})=>new Promise(res=>{const i=++id;pending[i]=res;ws.send(JSON.stringify({id:i,method,params}));});
  await new Promise(r=>ws.on('open',r));
  await send('Runtime.enable'); await send('Page.enable');
  await send('Page.navigate',{url:URL}); await sleep(5000);
  const ev = async e => {const r=await send('Runtime.evaluate',{expression:e,returnByValue:true}); return r.result&&r.result.result?r.result.result.value:null;};
  console.log('JS异常:', errs.length, errs.slice(0,3));
  console.log('正式工 KPI:', await ev("Array.from(document.querySelectorAll('#genCards .card')).map(c=>(c.querySelector('.v')?c.querySelector('.v').textContent:'?')+' | '+(c.querySelector('.l')?c.querySelector('.l').textContent:'?')).join(' /// ')"));
  console.log('劳务工 KPI:', await ev("Array.from(document.querySelectorAll('#attendCards .card')).map(c=>(c.querySelector('.v')?c.querySelector('.v').textContent:'?')+' | '+(c.querySelector('.l')?c.querySelector('.l').textContent:'?')).join(' /// ')"));
  // 顶部整体指标条是否已移除
  console.log('ovAttV 是否存在(应 null):', await ev("typeof document.getElementById('ovAttV')"));
  // 法国区 及时率(月视图) 抽样
  console.log('法国区 10月及时率(从 payload):', await ev("(function(){var fp=formalAttPayload;var e=fp.data['2026-10'].detail.find(x=>x.region==='法国区');return e? (e.timely/e.total*100).toFixed(2)+'%':'';})()"));
  // 4 条是否仍出现在 empIndex
  console.log('4条仍在 empIndex(应空数组):', await ev("(function(){var fp=formalAttPayload;var T=[['zt0022449','2026-10-18'],['zt0022048','2026-10-27'],['zt0022048','2026-10-28'],['zt0022580','2026-10-30']];var hit=[];for(var gk in fp.empIndex){fp.empIndex[gk].forEach(function(r){T.forEach(function(t){if(String(r[1]).trim()===t[0]&&String(r[5]).trim().slice(0,10)===t[1])hit.push(gk+'|'+t[0]);});});}return JSON.stringify(hit);})()"));
  ws.close(); chrome.kill('SIGKILL'); process.exit(0);
})().catch(e=>{console.error('FAIL',e);process.exit(1);});
