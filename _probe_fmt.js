// 检查当前看板 10 月 KPI 卡片的小数位
const { spawn } = require('child_process');
const http = require('http');
const WebSocket = require('ws');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const URL = 'file:///C:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html';
const PORT = 9227;
const getJSON = p => new Promise((res,rej)=>http.get({host:'127.0.0.1',port:PORT,path:p},r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>{try{res(JSON.parse(d))}catch(e){rej(e)}})}).on('error',rej));
const sleep = ms => new Promise(r=>setTimeout(r,ms));
(async()=>{
  const chrome = spawn(CHROME,['--headless=new','--remote-debugging-port='+PORT,'--remote-allow-origins=*','--disable-gpu','--no-sandbox','--disable-dev-shm-usage','--user-data-dir=C:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_fmt','about:blank'],{stdio:'ignore'});
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
  await send('Page.navigate',{url:URL}); await sleep(4500);
  const ev = async e => {const r=await send('Runtime.evaluate',{expression:e,returnByValue:true}); return r.result&&r.result.result?r.result.result.value:null;};
  console.log('genSel(正式工月份):', await ev("typeof genSel!=='undefined'?genSel:'N/A'"));
  console.log('attendMode:', await ev("typeof attendMode!=='undefined'?attendMode:'N/A'"));
  console.log('attendSel:', await ev("typeof attendSel!=='undefined'?attendSel:'N/A'"));
  console.log('正式工 KPI:', await ev("Array.from(document.querySelectorAll('#genCards .card')).map(c=>c.querySelector('.v').textContent+' | '+c.querySelector('.l').textContent).join(' /// ')"));
  console.log('劳务工 KPI:', await ev("Array.from(document.querySelectorAll('#attendCards .card')).map(c=>c.querySelector('.v').textContent+' | '+c.querySelector('.l').textContent).join(' /// ')"));
  console.log('JS异常:', errs.length);
  ws.close(); chrome.kill('SIGKILL'); process.exit(0);
})().catch(e=>{console.error('FAIL',e);process.exit(1);});
