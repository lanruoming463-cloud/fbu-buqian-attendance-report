// 探针：验证压缩后的 formalAtt 日/周数据（仅保留 untimely>0 的仓/组）
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FILE = 'file:///' + encodeURI('C:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html');
const { spawn } = require('child_process');
const http = require('http');

function getJSON(url) {
  return new Promise((res, rej) => {
    http.get(url, r => { let d = ''; r.on('data', c => d += c); r.on('end', () => { try { res(JSON.parse(d)); } catch (e) { rej(e); } }); }).on('error', rej);
  });
}
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const chrome = spawn(CHROME, ['--headless=new', '--remote-debugging-port=9223',
    '--user-data-dir=C:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_profile',
    '--no-first-run', '--disable-gpu', 'about:blank'], { stdio: 'ignore' });
  try {
    let targets = null;
    for (let i = 0; i < 30; i++) {
      await sleep(500);
      try { targets = await getJSON('http://127.0.0.1:9223/json/list'); break; } catch (e) { }
    }
    if (!targets) { console.log('FAIL: no CDP'); process.exit(1); }
    const page = targets.find(t => t.type === 'page');
    const ws = new WebSocket(page.webSocketDebuggerUrl);
    let id = 0; const pend = {};
    const send = (method, params) => new Promise(res => { const i = ++id; pend[i] = res; ws.send(JSON.stringify({ id: i, method, params })); });
    ws.onmessage = ev => { const m = JSON.parse(ev.data); if (m.id && pend[m.id]) { pend[m.id](m.result || m); delete pend[m.id]; } };
    await new Promise(r => ws.onopen = r);
    await send('Page.enable');
    await send('Page.navigate', { url: FILE });
    // 等待页面加载完成（formalAttPayload 可用）
    let ready = false;
    for (let i = 0; i < 120; i++) {
      await sleep(1000);
      const r = await send('Runtime.evaluate', { expression: 'typeof formalAttPayload==="object" && !!formalAttPayload.data', returnByValue: true });
      if (r.result && r.result.value) { ready = true; break; }
    }
    if (!ready) { console.log('FAIL: page not ready'); process.exit(1); }

    const expr = `
    (function(){
      var P = formalAttPayload, D = P.data;
      var dayKeys = P.days || [];
      var months = P.months || [];
      var out = { months: months, dayCount: dayKeys.length };
      // 日键汇总：保留的仓/组行数
      var keptWh = 0, keptGrp = 0, badFilter = 0, missingWhRef = 0, badTimely = 0;
      dayKeys.forEach(function(k){
        var b = D[k]; if (!b) { out.missingBlock = (out.missingBlock||0)+1; return; }
        b.group.forEach(function(g){
          if (!(g.untimely > 0)) badFilter++;
          if (g.timely !== g.total - g.untimely) badTimely++;
        });
        b.warehouse.forEach(function(w){
          if (!(w.untimely > 0)) badFilter++;
          if (w.timely !== w.total - w.untimely) badTimely++;
        });
        keptWh += b.warehouse.length; keptGrp += b.group.length;
        // 每个保留组的 仓对象 必须存在于同块 warehouse 列表
        var wset = {}; b.warehouse.forEach(function(w){ wset[w.major+'|'+w.region+'|'+w.wh]=1; });
        b.group.forEach(function(g){ if(!wset[g.major+'|'+g.region+'|'+g.wh]) missingWhRef++; });
        // 大区/区域必须全量
        if (!b.major.length || !b.detail.length) out.emptyMajorDet = (out.emptyMajorDet||0)+1;
      });
      out.keptWhRows = keptWh; out.keptGrpRows = keptGrp;
      out.badFilter = badFilter; out.missingWhRef = missingWhRef; out.badTimely = badTimely;
      // 月块对照（最后一个月）
      var lm = months[months.length-1], mb = D[lm];
      out.lastMonth = lm; out.monthWh = mb ? mb.warehouse.length : null; out.monthGrp = mb ? mb.group.length : null;
      // 月块仓合计 vs 日块同仓 total 一致性抽检：取最后一个日键里 untimely 最大的组
      var lk = dayKeys[dayKeys.length-1], lb = D[lk];
      if (lb && lb.group.length) {
        var g0 = lb.group.slice().sort(function(a,b){return b.untimely-a.untimely;})[0];
        var w0 = lb.warehouse.find(function(w){return w.major===g0.major&&w.region===g0.region&&w.wh===g0.wh;});
        out.sample = { day: lk, group: g0.group, gUntimely: g0.untimely, gTotal: g0.total, whFound: !!w0, whTotal: w0 ? w0.total : null };
        // empIndex 角标可用性
        var ek = g0.major+'|'+g0.region+'|'+g0.wh+'|'+g0.group;
        out.empBadge = (P.empIndex && P.empIndex[ek]) ? P.empIndex[ek].length : 0;
        out.empCountMatch = (P.empCount && P.empCount[ek]) || 0;
      }
      // 总量校验：月块 total 与日块聚合 total
      var mTot = {}; months.forEach(function(m){ var b=D[m]; ['total','untimely'].forEach(function(k){ mTot[k]=(mTot[k]||0)+b.total[k]; }); });
      var dTot = {total:0,untimely:0}; dayKeys.forEach(function(k){ dTot.total+=D[k].total.total; dTot.untimely+=D[k].total.untimely; });
      out.monthTot = mTot; out.dayTot = dTot;
      return out;
    })()`;
    const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true });
    console.log('PROBE=' + JSON.stringify(r.result.value, null, 1));
    process.exit(0);
  } finally { chrome.kill(); }
})().catch(e => { console.log('ERR', e.message); process.exit(1); });
