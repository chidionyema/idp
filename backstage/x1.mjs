import { chromium } from 'playwright-core';
const b = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
const errs=[]; p.on('pageerror', e=>errs.push('PE:'+e.message.slice(0,140)));
p.on('console', m=>{ if(m.type()==='error') errs.push('C:'+m.text().slice(0,120)); });
await p.goto('http://127.0.0.1:18910/', { waitUntil:'commit', timeout:12000 });
await p.waitForTimeout(7000);
const R = r => p.evaluate(r);
const out=[]; const chk=(n,ok,d='')=>out.push([n,!!ok,d]);

// C1 HOVER: move the mouse over the grid; a node must highlight (scale up + tooltip visible).
const box = await R(() => { const c=document.querySelector('canvas'); const r=c.getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height}; });
const baseScales = await R(()=>window.__reactor.nodes.map(n=>n.groupScale));
let hovered=null;
for (let gy=0.15; gy<=0.85 && !hovered; gy+=0.03) for (let gx=0.15; gx<=0.85 && !hovered; gx+=0.03) {
  await p.mouse.move(box.x+box.w*gx, box.y+box.h*gy);
  await p.waitForTimeout(60);
  const h = await R(()=>({ id: window.__reactor.hovered, tip: document.querySelector('#tt-id')?.innerText,
                           op: getComputedStyle(document.querySelector('#tt-id')?.closest('div').parentElement).opacity }));
  if (h.id) hovered = h;
}
chk('C1 hover highlights a node', !!hovered, hovered? `hovered=${hovered.id} tooltip=${hovered.tip}` : 'no hover found');
if (hovered) {
  const s2 = await R(()=>window.__reactor.nodes.map(n=>n.groupScale));
  const grew = s2.filter((v,i)=>v>baseScales[i]+1e-6).length;
  chk('C2 hovered node scales up 1.3x', grew===1, `${grew} node(s) enlarged`);
}

// C3 CLICK-TO-SELECT via real mouse, not the test hook.
await p.mouse.click(box.x+box.w*0.5, box.y+box.h*0.5).catch(()=>{});
const afterEmpty = await R(()=>({ sel: window.__reactor.selected }));
chk('C3 click empty space deselects', afterEmpty.sel === null, `selected=${afterEmpty.sel}`);

for (const [n,ok,d] of out) console.log(`  ${ok?'PASS':'FAIL'}  ${n.padEnd(42)} ${d}`);
console.log(`${out.filter(x=>x[1]).length}/${out.length}`);
console.log('errors:', errs.slice(0,3));
await b.close();
