// 探针：验证 正式工补签率(formalPayload) 并入 8/9 月后结构正确 + 日块压缩生效 + 渲染无报错
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FILE = 'file:///' + encodeURI('C:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html');
const { spawn } = require('child_process');
const http = require('http');
function getJSON(u){return new Promise((res,rej)=>{http.get(u,r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>{try{res(JSON.parse(d));}catch(e){rej(e);}});}).on('error',rej);});}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
  const chrome=spawn(CHROME,['--headless=new','--remote-debugging-port=9226','--user-data-dir=C:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_profile_f89','--no-first-run','--disable-gpu','about:blank'],{stdio:'ignore'});
  try{
    let t=null;
    for(let i=0;i<30;i++){await sleep(500);try{t=await getJSON('http://127.0.0.1:9226/json/list');break;}catch(e){}}
    if(!t){console.log('FAIL no CDP');process.exit(1);}
    const page=t.find(x=>x.type==='page');const ws=new WebSocket(page.webSocketDebuggerUrl);
    let id=0;const pend={};const send=(m,p)=>new Promise(r=>{const i=++id;pend[i]=r;ws.send(JSON.stringify({id:i,method:m,params:p}));});
    ws.onmessage=ev=>{const m=JSON.parse(ev.data);if(m.id&&pend[m.id]){pend[m.id](m.result||m);delete pend[m.id];}};
    await new Promise(r=>ws.onopen=r);
    await send('Page.enable');
    await send('Page.addScriptToEvaluateOnNewDocument',{source:'window.__errs=[];window.onerror=function(m,s,l,c){window.__errs.push(m+" @"+l+":"+c);return false;};window.addEventListener("unhandledrejection",function(e){window.__errs.push("REJ:"+(e.reason&&e.reason.message||e.reason));});'});
    await send('Page.navigate',{url:FILE});
    let ready=false;
    for(let i=0;i<180;i++){await sleep(1000);const r=await send('Runtime.evaluate',{expression:'typeof formalPayload==="object"',returnByValue:true});if(r.result&&r.result.value){ready=true;break;}}
    if(!ready){console.log('FAIL formalPayload not ready');process.exit(1);}
    const expr=`
    (function(){
      var P=formalPayload;
      var months=P.months||[];
      var days=(P.days||[]);
      var dayKeysWithWh=0, dayKeysWithGrp=0;
      days.forEach(function(d){var b=P.data[d];if(b&&b.warehouse&&b.warehouse.length)dayKeysWithWh++;if(b&&b.group&&b.group.length)dayKeysWithGrp++;});
      function blk(k){var b=P.data[k];return b?{wh:b.warehouse.length, grp:b.group.length, total:(b.total||{}).total}:null;}
      return {
        months: months, dayCount: days.length,
        dayKeysWithWh: dayKeysWithWh, dayKeysWithGrp: dayKeysWithGrp,
        has08: months.indexOf('2026-08')>=0, has09: months.indexOf('2026-09')>=0, has05: months.indexOf('2026-05')>=0,
        m08: blk('2026-08'), m09: blk('2026-09')
      };
    })()`;
    const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true});
    const struct=r.result.value;
    // 切到 正式工补签率(sign) 视图，默认选中最后月份
    const r2=await send('Runtime.evaluate',{expression:`
      (function(){
        showCell('formal','sign');
        return {
          mode: window.mode, selected: window.selected,
          tbodyTr: document.querySelectorAll('#viewFormal tbody tr').length,
          whBody: (document.getElementById('whBody')||{}).children? document.getElementById('whBody').children.length : -1,
          grpBody: (document.getElementById('grpBody')||{}).children? document.getElementById('grpBody').children.length : -1,
          cTotal: (document.getElementById('cTotal')||{}).textContent,
          errs: window.__errs.length
        };
      })()`,returnByValue:true});
    const view=r2.result.value;
    // 切到 2026-08 月份看仓/组是否全量
    const r3=await send('Runtime.evaluate',{expression:`
      (function(){
        selected='2026-08'; mode='month'; render();
        var wb=document.getElementById('whBody'); var gb=document.getElementById('grpBody');
        return {month:'2026-08', whChildren: wb?wb.children.length:-1, grpChildren: gb?gb.children.length:-1, errs:window.__errs.length};
      })()`,returnByValue:true});
    const mview=r3.result.value;
    // 切到 2026-08 某天 看优雅降级
    const r4=await send('Runtime.evaluate',{expression:`
      (function(){
        var d=(formalPayload.days||[]).find(function(x){return x.indexOf('2026-08')===0;});
        daySel=d; mode='day'; selected=''; render();
        var wb=document.getElementById('whBody'); var gb=document.getElementById('grpBody');
        return {day:d, emptyWh: wb&&/无仓明细数据/.test(wb.textContent), emptyGrp: gb&&/无组明细数据/.test(gb.textContent), errs:window.__errs.length};
      })()`,returnByValue:true});
    const dview=r4.result.value;
    console.log('STRUCT='+JSON.stringify(struct,null,1));
    console.log('VIEW='+JSON.stringify(view,null,1));
    console.log('MVIEW='+JSON.stringify(mview,null,1));
    console.log('DVIEW='+JSON.stringify(dview,null,1));
    console.log('ERRS_TOTAL='+((struct&&view&&mview&&dview)?(view.errs+mview.errs+dview.errs):'n/a'));
    process.exit(0);
  }finally{chrome.kill();}
})().catch(e=>{console.log('ERR',e.message);process.exit(1);});
