// 探针：验证 劳务工补签率(laborPayload) 并入 8/9 月后结构正确 + 日块压缩生效 + 渲染无报错
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FILE = 'file:///' + encodeURI('C:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html');
const { spawn } = require('child_process');
const http = require('http');
function getJSON(u){return new Promise((res,rej)=>{http.get(u,r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>{try{res(JSON.parse(d));}catch(e){rej(e);}});}).on('error',rej);});}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
  const chrome=spawn(CHROME,['--headless=new','--remote-debugging-port=9225','--user-data-dir=C:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_profile_l89','--no-first-run','--disable-gpu','about:blank'],{stdio:'ignore'});
  try{
    let t=null;
    for(let i=0;i<30;i++){await sleep(500);try{t=await getJSON('http://127.0.0.1:9225/json/list');break;}catch(e){}}
    if(!t){console.log('FAIL no CDP');process.exit(1);}
    const page=t.find(x=>x.type==='page');const ws=new WebSocket(page.webSocketDebuggerUrl);
    let id=0;const pend={};const send=(m,p)=>new Promise(r=>{const i=++id;pend[i]=r;ws.send(JSON.stringify({id:i,method:m,params:p}));});
    ws.onmessage=ev=>{const m=JSON.parse(ev.data);if(m.id&&pend[m.id]){pend[m.id](m.result||m);delete pend[m.id];}};
    await new Promise(r=>ws.onopen=r);
    await send('Page.enable');
    // 注入错误钩子
    await send('Page.addScriptToEvaluateOnNewDocument',{source:'window.__errs=[];window.onerror=function(m,s,l,c){window.__errs.push(m+" @"+l+":"+c);return false;};window.addEventListener("unhandledrejection",function(e){window.__errs.push("REJ:"+(e.reason&&e.reason.message||e.reason));});'});
    await send('Page.navigate',{url:FILE});
    let ready=false;
    for(let i=0;i<180;i++){await sleep(1000);const r=await send('Runtime.evaluate',{expression:'typeof laborPayload==="object"',returnByValue:true});if(r.result&&r.result.value){ready=true;break;}}
    if(!ready){console.log('FAIL laborPayload not ready');process.exit(1);}
    const expr=`
    (function(){
      var P=laborPayload;
      var months=P.months||[];
      var days=(P.days||[]);
      var dayKeysWithWh=0, dayKeysWithGrp=0;
      days.forEach(function(d){var b=P.data[d];if(b&&b.warehouse&&b.warehouse.length)dayKeysWithWh++;if(b&&b.group&&b.group.length)dayKeysWithGrp++;});
      var m08=P.data['2026-08']; var m09=P.data['2026-09'];
      var d0801=P.data['2026-08-01'];
      return {
        months: months,
        dayCount: days.length,
        dayKeysWithWh: dayKeysWithWh,
        dayKeysWithGrp: dayKeysWithGrp,
        m08_wh: m08?m08.warehouse.length:-1, m08_grp: m08?m08.group.length:-1,
        m09_wh: m09?m09.warehouse.length:-1, m09_grp: m09?m09.group.length:-1,
        d0801_wh: d0801?d0801.warehouse.length:-1, d0801_grp: d0801?d0801.group.length:-1,
        d0801_total: d0801?d0801.total:null
      };
    })()`;
    const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true});
    const struct=r.result.value;
    // 切到劳务工补签率视图并统计渲染行
    const r2=await send('Runtime.evaluate',{expression:`
      (function(){
        showCell('labor','sign');
        var mode=window.mode; var sel=window.selected;
        return {
          mode: mode, selected: sel,
          tbodyTr: document.querySelectorAll('#viewFormal tbody tr').length,
          whBody: (document.getElementById('whBody')||{}).innerHTML? document.getElementById('whBody').children.length : -1,
          grpBody: (document.getElementById('grpBody')||{}).innerHTML? document.getElementById('grpBody').children.length : -1,
          cTotal: (document.getElementById('cTotal')||{}).textContent,
          errs: window.__errs.length
        };
      })()`,returnByValue:true});
    const view=r2.result.value;
    // 再切到某个 8月某天 验证日块空仓/组 优雅降级
    const r3=await send('Runtime.evaluate',{expression:`
      (function(){
        // 找 2026-08 中任一天
        var d=(laborPayload.days||[]).find(function(x){return x.indexOf('2026-08')===0;});
        daySel=d; mode='day'; selected=''; render();
        var wb=document.getElementById('whBody'); var gb=document.getElementById('grpBody');
        var emptyWh = wb && /无仓明细数据/.test(wb.textContent);
        var emptyGrp = gb && /无组明细数据/.test(gb.textContent);
        return {day:d, emptyWh:emptyWh, emptyGrp:emptyGrp, errs:window.__errs.length};
      })()`,returnByValue:true});
    const dayView=r3.result.value;
    console.log('STRUCT='+JSON.stringify(struct,null,1));
    console.log('VIEW='+JSON.stringify(view,null,1));
    console.log('DAYVIEW='+JSON.stringify(dayView,null,1));
    console.log('ERRS_TOTAL='+((struct&&view&&dayView)?(view.errs+dayView.errs):'n/a'));
    process.exit(0);
  }finally{chrome.kill();}
})().catch(e=>{console.log('ERR',e.message);process.exit(1);});
