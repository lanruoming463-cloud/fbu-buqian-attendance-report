const { spawn } = require('child_process');
const http = require('http');
const WebSocket = require('ws');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FILE = 'file:///c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html';
const PORT = 9292;
const PROFILE = 'c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_profile_buqian_legend';
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
  for(let i=0;i<40;i++){await sleep(1000);const e=await send('Runtime.evaluate',{expression:`typeof showCell!=='undefined'`,returnByValue:true});if(e.result&&e.result.result&&e.result.result.value===true){ready=true;break;}}
  console.log('READY:',ready);
  const r=await send('Runtime.evaluate',{expression:`(function(){ try{
    const o={};
    // 正式工补签率
    showCell('formal','sign');
    o.formalMajHead=[...document.querySelectorAll('#tableMajor thead th')].map(t=>t.textContent.trim());
    const fmBar=document.querySelector('#majorBody tr .bar>span');
    o.formalMajBarWidth=fmBar?fmBar.style.width:null;
    const fmRate=document.querySelector('#majorBody tr td.rate');
    o.formalMajRate=fmRate?fmRate.textContent.trim():null;
    // 劳务工补签率（默认月=最新）
    showCell('labor','sign');
    o.laborMajHead=[...document.querySelectorAll('#tableMajor thead th')].map(t=>t.textContent.trim());
    const rows=[...document.querySelectorAll('#majorBody tr')].filter(tr=>tr.querySelector('.bar>span'));
    const lrow=rows.find(tr=>tr.textContent.includes('欧洲区'))||rows[0];
    if(lrow){
      const tds=[...lrow.querySelectorAll('td')];
      o.laborEuropeRow=tds.slice(0,7).map(t=>t.textContent.trim());
      const bar=lrow.querySelector('.bar>span');
      o.laborEuropeBarWidth=bar?bar.style.width:null;
    }
    // 劳务工及时率表头
    showCell('labor','att');
    o.laborAttHead=[...document.querySelectorAll('#tableAttMajor thead th')].map(t=>t.textContent.trim());
    return JSON.stringify(o);
  }catch(e){ return JSON.stringify({FATAL:e.message}); } })()`,returnByValue:true});
  const v=r.result&&r.result.result?r.result.result.value:null;
  console.log('EXC_DETAILS:', JSON.stringify(r.result&&r.result.exceptionDetails||null).slice(0,300));
  console.log(v);
  console.log('JS_ERRORS:',errors.length, errors.slice(0,3));
  chrome.kill();process.exit(0);
}
main().catch(e=>{console.error('FATAL',e);chrome.kill();process.exit(1);});
