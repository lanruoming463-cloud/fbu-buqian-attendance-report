// CDP 探针: 加载注入后 HTML, 捕获 JS 异常/console 错误, 校验关键 KPI
const { spawn, execSync } = require('child_process');
const http = require('http');
const WebSocket = require('ws');
const fs = require('fs');

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const URL = 'file:///C:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_injected_1104.html';
const PORT = 9223;

function getJSON(path){
  return new Promise((res,rej)=>{
    http.get({host:'127.0.0.1',port:PORT,path},r=>{
      let d='';r.on('data',c=>d+=c);r.on('end',()=>{try{res(JSON.parse(d));}catch(e){rej(e);}});
    }).on('error',rej);
  });
}
const sleep = ms=>new Promise(r=>setTimeout(r,ms));

(async()=>{
  const UDIR = 'C:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_1104';
  const chrome = spawn(CHROME,['--headless=new','--remote-debugging-port='+PORT,'--remote-debugging-address=127.0.0.1','--remote-allow-origins=*','--disable-gpu','--no-sandbox','--disable-dev-shm-usage','--user-data-dir='+UDIR,'about:blank'],{stdio:'ignore'});
  // 轮询端口
  let up=false;
  for(let i=0;i<40;i++){ await sleep(500); try{ await getJSON('/json'); up=true; break; }catch(e){} }
  if(!up){ console.error("CHROME 端口未启动"); chrome.kill('SIGKILL'); process.exit(1); }
  let targets = await getJSON('/json');
  let page = targets.find(t=>t.type==='page') || targets[0];
  const wsUrl = page.webSocketDebuggerUrl;
  const ws = new WebSocket(wsUrl);
  let id=0; const pending={};
  const errors=[], consoleErrs=[];
  ws.on('message',m=>{
    const o=JSON.parse(m);
    if(o.id && pending[o.id]){ pending[o.id](o); delete pending[o.id]; }
    if(o.method==='Runtime.exceptionThrown'){ errors.push(o.params.exceptionDetails.exception?o.params.exceptionDetails.exception.description:o.params.exceptionDetails.text); }
    if(o.method==='Runtime.consoleAPICalled' && o.params.type==='error'){ consoleErrs.push(o.params.args.map(a=>a.value||a.description).join(' ')); }
    if(o.method==='Log.entryAdded' && o.params.entry.level==='error'){ consoleErrs.push('[Log] '+o.params.entry.text); }
  });
  const send=(method,params={})=>new Promise(res=>{ const i=++id; pending[i]=res; ws.send(JSON.stringify({id:i,method,params})); });
  await new Promise(r=>ws.on('open',r));
  await send('Runtime.enable'); await send('Console.enable'); await send('Log.enable'); await send('Page.enable');
  await send('Page.navigate',{url:URL});
  await sleep(4500);
  // 校验 KPI
  const ev = async (expr)=>{ const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true}); return r.result&&r.result.result?r.result.result.value:null; };
  const kpis = {};
  kpis.labor_1030_yqr = await ev("attendPayload.data['2026-10-30'].total.yqr");
  kpis.labor_1031_yqr = await ev("attendPayload.data['2026-10-31'].total.yqr");
  kpis.labor_1030_unconf = await ev("attendPayload.data['2026-10-30'].total.unconfirmed");
  kpis.labor_days = await ev("attendPayload.days.length");
  kpis.formal_1010_untimely = await ev("formalAttPayload.data['2026-10'].total.untimely");
  kpis.formal_1010_timely = await ev("formalAttPayload.data['2026-10'].total.timely");
  kpis.formal_empindex_rows = await ev("Object.values(formalAttPayload.empIndex).reduce((a,b)=>a+b.length,0)");
  kpis.formal_days = await ev("formalAttPayload.days.length");
  console.log("KPI:", JSON.stringify(kpis));
  console.log("JS异常数:", errors.length);
  errors.slice(0,10).forEach(e=>console.log("  ERR:", e));
  console.log("Console错误数:", consoleErrs.length);
  consoleErrs.slice(0,10).forEach(e=>console.log("  CERR:", e));
  ws.close(); chrome.kill('SIGKILL');
  process.exit(0);
})().catch(e=>{console.error("PROBE_FAIL",e);process.exit(1);});
