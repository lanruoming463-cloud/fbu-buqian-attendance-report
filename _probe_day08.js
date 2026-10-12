// 探针：确认 正式工/劳务工 考勤确认及时率 payload 均含 2026-10-08 日块且总量正确
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FILE = 'file:///' + encodeURI('C:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html');
const { spawn } = require('child_process');
const http = require('http');
function getJSON(u){return new Promise((res,rej)=>{http.get(u,r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>{try{res(JSON.parse(d));}catch(e){rej(e);}});}).on('error',rej);});}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
  const chrome=spawn(CHROME,['--headless=new','--remote-debugging-port=9224','--user-data-dir=C:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_profile2','--no-first-run','--disable-gpu','about:blank'],{stdio:'ignore'});
  try{
    let t=null;
    for(let i=0;i<30;i++){await sleep(500);try{t=await getJSON('http://127.0.0.1:9224/json/list');break;}catch(e){}}
    if(!t){console.log('FAIL no CDP');process.exit(1);}
    const page=t.find(x=>x.type==='page');const ws=new WebSocket(page.webSocketDebuggerUrl);
    let id=0;const pend={};const send=(m,p)=>new Promise(r=>{const i=++id;pend[i]=r;ws.send(JSON.stringify({id:i,method:m,params:p}));});
    ws.onmessage=ev=>{const m=JSON.parse(ev.data);if(m.id&&pend[m.id]){pend[m.id](m.result||m);delete pend[m.id];}};
    await new Promise(r=>ws.onopen=r);
    await send('Page.enable');await send('Page.navigate',{url:FILE});
    let ready=false;
    for(let i=0;i<120;i++){await sleep(1000);const r=await send('Runtime.evaluate',{expression:'typeof formalAttPayload==="object"&&typeof attendPayload==="object"',returnByValue:true});if(r.result&&r.result.value){ready=true;break;}}
    if(!ready){console.log('FAIL not ready');process.exit(1);}
    const expr=`
    (function(){
      function dayInfo(P,name){
        var out={name:name, days:(P.days||[]).slice(-3), months:P.months||[]};
        var d=P.data['2026-10-08'];
        if(d){ out.d08={total:d.total.total, untimely:d.total.untimely, wh:d.warehouse.length, grp:d.group.length}; }
        else out.d08=null;
        // 月块 2026-10 总量
        var m=P.data['2026-10'];
        if(m) out.m10={total:m.total.total, untimely:m.total.untimely};
        return out;
      }
      return { formal: dayInfo(formalAttPayload,'formal'), labor: dayInfo(attendPayload,'labor') };
    })()`;
    const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true});
    console.log('PROBE='+JSON.stringify(r.result.value,null,1));
    process.exit(0);
  }finally{chrome.kill();}
})().catch(e=>{console.log('ERR',e.message);process.exit(1);});
