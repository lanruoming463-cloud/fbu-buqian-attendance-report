const { spawn } = require('child_process');
const http = require('http');
const WebSocket = require('ws');

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const FILE = 'file:///c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html';
const PORT = 9223;
const PROFILE = 'c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/_chrome_tmp_profile_fsign';

function getJSON(url) {
  return new Promise((res, rej) => {
    http.get(url, (r) => {
      let d = '';
      r.on('data', (c) => (d += c));
      r.on('end', () => { try { res(JSON.parse(d)); } catch (e) { rej(e); } });
    }).on('error', rej);
  });
}

const chrome = spawn(CHROME, [
  '--headless=new', '--disable-gpu', '--no-sandbox',
  '--remote-debugging-port=' + PORT, '--user-data-dir=' + PROFILE,
  'about:blank'
], { stdio: 'ignore' });

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function main() {
  await sleep(2500);
  let targets;
  for (let i = 0; i < 20; i++) {
    try { targets = await getJSON(`http://127.0.0.1:${PORT}/json/list`); if (targets && targets.length) break; } catch (e) {}
    await sleep(500);
  }
  const page = targets.find(t => t.type === 'page') || targets[0];
  const ws = new WebSocket(page.webSocketDebuggerUrl, { perMessageDeflate: false });
  let id = 0;
  const pending = new Map();
  const errors = [];
  function send(method, params) {
    return new Promise((res) => {
      const mid = ++id;
      pending.set(mid, res);
      ws.send(JSON.stringify({ id: mid, method, params: params || {} }));
    });
  }
  ws.on('message', (raw) => {
    const m = JSON.parse(raw);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
    if (m.method === 'Runtime.exceptionThrown' || m.method === 'Runtime.consoleAPICalled') {
      const txt = m.method === 'Runtime.exceptionThrown'
        ? JSON.stringify(m.params.exceptionDetails)
        : JSON.stringify(m.params.args);
      errors.push(txt);
    }
  });
  await new Promise(r => ws.on('open', r));
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Page.navigate', { url: FILE });
  await sleep(4000);

  const evalRes = await send('Runtime.evaluate', {
    expression: `(function(){
      function collect(blocks){
        const majors=new Set(), regions=new Set();
        if(!blocks) return {majors,regions};
        for(const [k,b] of Object.entries(blocks)){
          if(!b||typeof b!=='object') continue;
          if(Array.isArray(b.major)) for(const m of b.major) if(m&&m.name) majors.add(m.name);
          if(Array.isArray(b.detail)) for(const d of b.detail){ if(d.major) majors.add(d.major); if(d.region) regions.add(d.region);}
          if(Array.isArray(b.warehouse)) for(const w of b.warehouse){ if(w.major) majors.add(w.major); if(w.region) regions.add(w.region);}
          if(Array.isArray(b.group)) for(const g of b.group){ if(g.major) majors.add(g.major); if(g.region) regions.add(g.region);}
        }
        return {majors:[...majors], regions:[...regions]};
      }
      const f=collect(formalPayload.data);
      const l=collect(laborPayload.data);
      return JSON.stringify({
        formalMajors:f.majors.sort(), formalRegions:f.regions.sort(),
        laborMajors:l.majors.sort()
      });
    })()`,
    returnByValue: true
  });

  const out = JSON.parse(evalRes.result.result.value);
  const excludedMajors = ['海外销售部','FBU财务部','渠道管理部','LD 法务部','FBU技术部','平台业务部','品牌客户部'];
  const excludedRegions = ['国内HRBP组','美洲支持HRBP组','美洲支持bp组','欧亚支持bp组','欧亚支持HRBP组'];
  const badMajors = excludedMajors.filter(m => out.formalMajors.includes(m));
  const badRegions = excludedRegions.filter(r => out.formalRegions.includes(r));
  console.log('=== formalPayload distinct 三级部门 ===');
  console.log(out.formalMajors.join(' | '));
  console.log('=== formalPayload distinct 四级部门 ===');
  console.log(out.formalRegions.join(' | '));
  console.log('=== CHECK ===');
  console.log('excluded majors still present:', JSON.stringify(badMajors));
  console.log('excluded regions still present:', JSON.stringify(badRegions));
  console.log('FBU HRBP Dept. retained:', out.formalMajors.includes('FBU HRBP Dept.'));
  console.log('三大区 present:', ['美洲区','欧洲区','亚太区'].every(m => out.formalMajors.includes(m)));
  console.log('=== laborPayload distinct major ===');
  console.log(out.laborMajors.join(' | '));
  console.log('labor non-三大区 majors:', out.laborMajors.filter(m=>!['美洲区','欧洲区','亚太区'].includes(m)));
  console.log('=== JS ERRORS (' + errors.length + ') ===');
  errors.slice(0, 20).forEach(e => console.log(e));

  ws.close();
  chrome.kill('SIGKILL');
  process.exit(0);
}

main().catch(e => { console.error('PROBE FAIL', e); chrome.kill('SIGKILL'); process.exit(1); });
