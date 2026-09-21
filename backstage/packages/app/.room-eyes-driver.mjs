
import { chromium } from 'playwright-core';
import net from 'node:net';

const CDP = process.env.ROOM_EYE_PORT || '9222';
const SOCK = process.env.ROOM_EYES_SOCK || '/tmp/room-eyes.sock';

const b = await chromium.connectOverCDP(`http://127.0.0.1:${CDP}`);
/** The last canvas fraction that opened a menu, so the sweep is paid once rather than always. */
let lastHit = null;
const findPage = () => {
  const pages = b.contexts().flatMap((c) => c.pages());
  return pages.find((x) => x.url().includes('/fleet')) ?? pages[0];
};

async function look(p) {
  await p.waitForSelector('canvas', { timeout: 6000 }).catch(() => {});
  return p.evaluate(() => {
    const agents = Array.from(document.querySelectorAll('[data-testid^="agent-"]'));
    const states = {};
    for (const a of agents) {
      const m = (a.textContent || '').match(/thinking|waiting|stuck|finished/i);
      if (m) states[m[0].toLowerCase()] = (states[m[0].toLowerCase()] || 0) + 1;
    }
    const c = document.querySelector('canvas');
    const r = c?.getBoundingClientRect();
    const menu = document.querySelector('[data-testid="radial-menu"]');
    return {
      agents: agents.length,
      states,
      first: (agents[0]?.textContent || '').trim().slice(0, 96),
      canvas: r ? { w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.x), y: Math.round(r.y) } : null,
      menu: menu ? Array.from(menu.querySelectorAll('button')).map((x) => ({ verb: x.textContent.trim(), on: !x.disabled })) : null,
      mind: !!document.querySelector('[data-testid="mind-panel"]'),
      voice: !!document.querySelector('[data-testid="voice-ptt"]'),
      url: location.href,
    };
  });
}

async function handle(p, line) {
  const [cmd, ...args] = line.trim().split(/\s+/);
  switch (cmd) {
    case 'look':
      return look(p);
    case 'click': {
      // Click a fraction of the canvas, which is how a person clicks a node: the layout is
      // seeded and only the canvas knows where an agent is.
      const r = await p.evaluate(() => {
        const c = document.querySelector('canvas');
        const b = c.getBoundingClientRect();
        return { x: b.x, y: b.y, w: b.width, h: b.height };
      });
      await p.mouse.click(r.x + r.w * Number(args[0]), r.y + r.h * Number(args[1]));
      await p.waitForTimeout(120);
      return look(p);
    }
    case 'menu': {
      // SWEEP, BUT REMEMBER. Measured: a full sweep is 6.2s and the browser work per look is
      // 0.7s, so almost all of it is the grid. Agents drift about 10% a minute, which means a
      // point that opened a menu a few seconds ago still opens one -- so the last hit is tried
      // FIRST and the sweep is usually skipped entirely.
      const r = await p.evaluate(() => {
        const c = document.querySelector('canvas');
        const b = c.getBoundingClientRect();
        return { x: b.x, y: b.y, w: b.width, h: b.height };
      });
      const opens = async (gx, gy) => {
        await p.mouse.click(r.x + r.w * gx, r.y + r.h * gy);
        await p.waitForTimeout(90);
        return p.evaluate(() => !!document.querySelector('[data-testid="radial-menu"]'));
      };
      if (lastHit && (await opens(lastHit[0], lastHit[1]))) return look(p);
      const step = lastHit ? 0.035 : 0.05;
      for (let gy = 0.14; gy <= 0.90; gy += 0.07) {
        for (let gx = 0.06; gx <= 0.95; gx += step) {
          if (await opens(gx, gy)) { lastHit = [gx, gy]; return look(p); }
        }
      }
      return { ...(await look(p)), menu: null, note: 'no node opened a menu' };
    }
    case 'eval': {
      const expr = line.trim().slice(5);
      return await p.evaluate(expr);
    }
    case 'shot': {
      const c = await p.$('canvas');
      await c.screenshot({ path: args[0] });
      return { wrote: args[0] };
    }
    case 'quit':
      return { bye: true };
    default:
      throw new Error(`unknown command: ${cmd}`);
  }
}

// One JSON line out per request. Separated by a NEWLINE rather than EOF, so the process can stay
// up and answer again -- the whole point.
const server = net.createServer((conn) => {
  let buf = '';
  conn.on('data', async (chunk) => {
    buf += chunk.toString();
    const lines = buf.split('\n');
    buf = lines.pop() ?? '';
    for (const line of lines) {
      if (!line.trim()) continue;
      let reply;
      try {
        reply = { ok: true, result: await handle(findPage(), line) };
      } catch (e) {
        reply = { ok: false, error: String(e).slice(0, 300) };
      }
      conn.write(JSON.stringify(reply) + '\n');
      if (line.trim() === 'quit') { conn.end(); process.exit(0); }
    }
  });
});
// A stale socket file is removed rather than refused, so a killed driver does not wedge the path.
import fs from 'node:fs';
try { fs.unlinkSync(SOCK); } catch {}
server.listen(SOCK, () => console.error('room-eyes: driver listening'));
