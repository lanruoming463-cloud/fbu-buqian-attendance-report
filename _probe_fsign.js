const fs = require('fs');

const htmlPath = 'c:/Users/zt25337/WorkBuddy/2026-08-20-09-25-58/补签流程_补签统计.html';
const html = fs.readFileSync(htmlPath, 'utf8');

// Robust JSON object extractor that skips braces inside strings (handles escapes).
function braceExtract(src, startMarker) {
  const i = src.indexOf(startMarker);
  if (i < 0) throw new Error('marker not found: ' + startMarker);
  let j = src.indexOf('{', i);
  if (j < 0) throw new Error('no brace after marker');
  let depth = 0;
  let k = j;
  while (k < src.length) {
    const c = src[k];
    if (c === '"' || c === "'") {
      const q = c;
      k++;
      while (k < src.length) {
        if (src[k] === '\\') { k += 2; continue; }
        if (src[k] === q) { k++; break; }
        k++;
      }
      continue;
    }
    if (c === '{') depth++;
    else if (c === '}') {
      depth--;
      if (depth === 0) {
        return src.slice(j, k + 1);
      }
    }
    k++;
  }
  throw new Error('unbalanced');
}

const fpStr = braceExtract(html, 'const formalPayload =');
const formalPayload = JSON.parse(fpStr);
const lpStr = braceExtract(html, 'const laborPayload =');
const laborPayload = JSON.parse(lpStr);

function collect(blocks) {
  const majors = new Set();
  const regions = new Set();
  if (!blocks) return { majors, regions };
  for (const [key, blk] of Object.entries(blocks)) {
    if (!blk || typeof blk !== 'object') continue;
    if (Array.isArray(blk.major)) for (const m of blk.major) if (m && m.name) majors.add(m.name);
    if (Array.isArray(blk.detail)) for (const d of blk.detail) { if (d.major) majors.add(d.major); if (d.region) regions.add(d.region); }
    if (Array.isArray(blk.warehouse)) for (const w of blk.warehouse) { if (w.major) majors.add(w.major); if (w.region) regions.add(w.region); }
    if (Array.isArray(blk.group)) for (const g of blk.group) { if (g.major) majors.add(g.major); if (g.region) regions.add(g.region); }
  }
  return { majors, regions };
}

const f = collect(formalPayload.data);
console.log('=== formalPayload distinct 三级部门 (major) ===');
console.log([...f.majors].sort().join(' | '));
console.log('=== formalPayload distinct 四级部门 (region) ===');
console.log([...f.regions].sort().join(' | '));

const excludedMajors = ['海外销售部','FBU财务部','渠道管理部','LD 法务部','FBU技术部','平台业务部','品牌客户部'];
const excludedRegions = ['国内HRBP组','美洲支持HRBP组','美洲支持bp组','欧亚支持bp组','欧亚支持HRBP组'];
const badMajors = excludedMajors.filter(m => f.majors.has(m));
const badRegions = excludedRegions.filter(r => f.regions.has(r));
console.log('=== CHECK ===');
console.log('excluded majors still present:', JSON.stringify(badMajors));
console.log('excluded regions still present:', JSON.stringify(badRegions));
console.log('FBU HRBP Dept. retained:', f.majors.has('FBU HRBP Dept.'));
console.log('三大区 present:', ['美洲区','欧洲区','亚太区'].every(m => f.majors.has(m)));

const l = collect(laborPayload.data);
console.log('=== laborPayload distinct major ===');
console.log([...l.majors].sort().join(' | '));
console.log('labor non-三大区 majors:', [...l.majors].filter(m=>!['美洲区','欧洲区','亚太区'].includes(m)));
