// 探针：验证 劳务工及时率(attendPayload) 日块压缩(unconfirmed>0)后结构正确 + 渲染无报错 + KPI 不变
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FILE = 'file:///' + encodeURI('C:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html');
const { spawn } = require('child_process');
const http = require('http');
function getJSON(u){return new Promise((res,rej)=>{http.get(u,r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>{try{res(JSON.parse(d));}catch(e){rej(e);}});}).on('error',rej);});}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
  const chrome=spawn(CHROME,['--headless=new','--remote-debugging-port=9227','--user-data-dir=C:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_profile_attc','--no-first-run','--disable-gpu','about:blank'],{stdio:'ignore'});
  try{
    let t=null;
    for(let i=0;i<30;i++){await sleep(500);try{t=await getJSON('http://127.0.0.1:9227/json/list');break;}catch(e){}}
    if(!t){console.log('FAIL no CDP');process.exit(1);}
    const page=t.find(x=>x.type==='page');const ws=new WebSocket(page.webSocketDebuggerUrl);
    let id=0;const pend={};const send=(m,p)=>new Promise(r=>{const i=++id;pend[i]=r;ws.send(JSON.stringify({id:i,method:m,params:p}));});
    ws.onmessage=ev=>{const m=JSON.parse(ev.data);if(m.id&&pend[m.id]){pend[m.id](m.result||m);delete pend[m.id];}};
    await new Promise(r=>ws.onopen=r);
    await send('Page.enable');
    await send('Page.addScriptToEvaluateOnNewDocument',{source:'window.__errs=[];window.onerror=function(m,s,l,c){window.__errs.push(m+" @"+l+":"+c);return false;};window.addEventListener("unhandledrejection",function(e){window.__errs.push("REJ:"+(e.reason&&e.reason.message||e.reason));});'});
    await send('Page.navigate',{url:FILE});
    let ready=false;
    for(let i=0;i<180;i++){await sleep(1000);const r=await send('Runtime.evaluate',{expression:'typeof attendPayload==="object"',returnByValue:true});if(r.result&&r.result.value){ready=true;break;}}
    if(!ready){console.log('FAIL attendPayload not ready');process.exit(1);}
    const expr=`
    (function(){
      var P=attendPayload;
      var nDays=P.days.length, dayWh=0, dayGrp=0, badWh=0, badGrp=0;
      P.days.forEach(function(d){var b=P.data[d];if(!b)return;
        (b.warehouse||[]).forEach(function(w){dayWh++;if(!((w.yqr||0)-(w.sjqr||0)>0))badWh++;});
        (b.group||[]).forEach(function(g){dayGrp++;if(!((g.yqr||0)-(g.sjqr||0)>0))badGrp++;});});
      return {months:P.months, nDays:nDays, dayWh:dayWh, dayGrp:dayGrp, badWh:badWh, badGrp:badGrp,
              empIndexKeys:Object.keys(P.empIndex||{}).length};
    })()`;
    const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true});
    const struct=r.result.value;
    // 切到劳务工及时率视图（默认最新月 2026-10）
    const r2=await send('Runtime.evaluate',{expression:`
      (function(){
        showCell('labor','att');
        var cards=document.getElementById('attendCards');
        return {
          mode: window.attendMode, sel: window.attendSel,
          kpi: cards?cards.innerText.replace(/\\n/g,' | '):'(none)',
          whRows: document.querySelectorAll('#attWhBody tr.att-wh').length,
          grpRows: document.querySelectorAll('#attGrpBody tr.att-grp').length,
          badges: document.querySelectorAll('#attGrpBody .emp-count').length,
          majorRows: document.querySelectorAll('#attMajorBody tr').length,
          detailRows: document.querySelectorAll('#attDetailBody tr.att-region').length,
          errs: window.__errs.length
        };
      })()`,returnByValue:true});
    const view=r2.result.value;
    // 切到 2026-06 月（数据最多的月份之一）再验证
    const r3=await send('Runtime.evaluate',{expression:`
      (function(){
        attendSel='2026-06'; attendMode='month'; renderAttend();
        var cards=document.getElementById('attendCards');
        return {sel:'2026-06', kpi:cards?cards.innerText.replace(/\\n/g,' | '):'(none)',
          whRows: document.querySelectorAll('#attWhBody tr.att-wh').length,
          grpRows: document.querySelectorAll('#attGrpBody tr.att-grp').length,
          errs: window.__errs.length};
      })()`,returnByValue:true});
    const m6=r3.result.value;
    console.log('STRUCT='+JSON.stringify(struct,null,1));
    console.log('VIEW10='+JSON.stringify(view,null,1));
    console.log('VIEW06='+JSON.stringify(m6,null,1));
    console.log('ERRS='+((view?view.errs:9)+(m6?m6.errs:9)));
    process.exit(0);
  }finally{chrome.kill();}
})().catch(e=>{console.log('ERR',e.message);process.exit(1);});
