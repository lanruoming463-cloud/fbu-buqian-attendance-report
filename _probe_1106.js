// V21 验证探针: 载入注入后 HTML, 检查页面 JS 异常 + 渲染 11月 KPI + 确认 11月数据可访问
const { spawn } = require('child_process');
const http = require('http');
const WebSocket = require('ws');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const URL = 'file:///C:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html';
const PORT = 9229;
const getJSON = p => new Promise((res,rej)=>http.get({host:'127.0.0.1',port:PORT,path:p},r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>{try{res(JSON.parse(d))}catch(e){rej(e)}})}).on('error',rej));
const sleep = ms => new Promise(r=>setTimeout(r,ms));
(async()=>{
  const chrome = spawn(CHROME,['--headless=new','--remote-debugging-port='+PORT,'--remote-allow-origins=*','--disable-gpu','--no-sandbox','--disable-dev-shm-usage','--user-data-dir=C:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_1106','about:blank'],{stdio:'ignore'});
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
  console.log('默认 genSel(应为2026-11):', await ev("typeof genSel!=='undefined'?genSel:'N/A'"));
  console.log('默认 attendSel(应为2026-11):', await ev("typeof attendSel!=='undefined'?attendSel:'N/A'"));
  console.log('正式工 KPI(默认11月):', await ev("Array.from(document.querySelectorAll('#genCards .card')).map(c=>(c.querySelector('.v')?c.querySelector('.v').textContent:'?')+' | '+(c.querySelector('.l')?c.querySelector('.l').textContent:'?')).join(' /// ')"));
  console.log('劳务工 KPI(默认11月):', await ev("Array.from(document.querySelectorAll('#attendCards .card')).map(c=>(c.querySelector('.v')?c.querySelector('.v').textContent:'?')+' | '+(c.querySelector('.l')?c.querySelector('.l').textContent:'?')).join(' /// ')"));
  // 直接读 payload 校验 11月
  console.log('正式工 months:', await ev("formalAttPayload.months.join(',')"));
  console.log('正式工 11月月块:', await ev("(function(){var t=formalAttPayload.data['2026-11'].total;return 'total='+t.total+' untimely='+t.untimely+' timely='+t.timely+' rate='+(t.timely/t.total*100).toFixed(2)+'%';})()"));
  console.log('劳务工 months:', await ev("attendPayload.months.join(',')"));
  console.log('劳务工 11月(聚合日块):', await ev("(function(){var ap=attendPayload;var t={yqr:0,sjqr:0};['2026-11-01','2026-11-02','2026-11-03'].forEach(function(d){var b=ap.data[d];if(b){t.yqr+=b.total.yqr;t.sjqr+=b.total.sjqr;}});return 'yqr='+t.yqr+' sjqr='+t.sjqr+' unconfirmed='+(t.yqr-t.sjqr)+' rate='+(t.sjqr/t.yqr*100).toFixed(2)+'%';})()"));
  // 切换到 11月日视图(11-02) 验证 day 渲染
  console.log('切到 11-02 day 后 劳务工 KPI:', await ev("(function(){ if(typeof setModeAttend==='function'){ attendMode='day'; attendDayStart='2026-11-02'; attendDayEnd='2026-11-02'; renderAttend(); } return Array.from(document.querySelectorAll('#attendCards .card')).map(c=>(c.querySelector('.v')?c.querySelector('.v').textContent:'?')+'|'+(c.querySelector('.l')?c.querySelector('.l').textContent:'?')).join(' /// '); })()"));
  ws.close(); chrome.kill('SIGKILL'); process.exit(0);
})().catch(e=>{console.error('FAIL',e);process.exit(1);});
