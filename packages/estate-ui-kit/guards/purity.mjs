#!/usr/bin/env node
// Token-purity guard. Usage: node guards/purity.mjs <dir-or-file>...
// Refuses, in .css/.scss/.tsx/.jsx/.astro/.svelte/.vue files (skipping node_modules, dist, .next,
// and the kit's own tokens.json/tokens.css which are the only places a literal may live):
//   1. colour literals: #hex, rgb(), hsl(), oklch()
//   2. font-size with a px/rem literal instead of var(--type-*)
//   3. inline style="" attributes carrying a colour or font-size
// Prints every hit as file:line and exits 1 if any. This is the gate crew#694 CP4 asks for.
//
//   node guards/purity.mjs --budget guards/budget.json
//
// The budget mode is the ratchet that lets the founder's surfaces be guarded before they are
// clean: every entry names a path and the number of violations it may still have. The guard
// fails only when a path is *above* its budget, so today's numbers start green and every
// surface that reaches zero turns its entry into a refusal. Entries are a partition: a path's
// count excludes files under any nested entry, so each scope owns its own number.
//
// THE BASE (why the numbers are measured against main, not against a snapshot).
// A snapshot number is wrong the moment main moves, and the failure is silent and unfair: on
// 2026-10-24 the lane that reviews the founder's surfaces was red because main itself had
// added 13 violations to a surface the lane never touched. The lane was not the problem; the
// snapshot was. So the guard measures the base -- what origin/main holds for the same path,
// with the same rules -- and judges the branch against three things:
//
//   cap      the branch may not be above max(budget, main's own count). main's own violations
//            are never the branch's fault, so they can never make it red.
//   teeth    the branch may not add violations in the files it touches: for each file it
//            changed, the branch's count minus main's count for that file, summed. This is
//            what stops a lane from riding on main's mess, and it is measured per file, so
//            cleaning one file cannot pay for dirtying another.
//   fresh    the cap in budget.json may not be looser than main's own count; a looser cap is
//            a stale cap and is reported, so the ratchet follows main down as surfaces are
//            cleaned.
//
// The base is read from origin/main by default; ESTATE_PURITY_BASE overrides it (a merge base,
// a SHA, a branch). With no base in the checkout the guard falls back to the cap alone, which
// is what it did before, and says so.
import { readFileSync, readdirSync, statSync, existsSync, mkdtempSync, rmSync } from 'node:fs';
import { join, extname, basename, relative, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';

const here = dirname(fileURLToPath(import.meta.url));
const kitRoot = join(here, '..');
// The checkout the guard measures. It is the repo the kit lives in, unless a caller points it
// elsewhere (the test measures a scratch repo the same way the guard measures this one).
const repoRoot = process.env.ESTATE_PURITY_ROOT ? resolve(process.env.ESTATE_PURITY_ROOT) : join(here, '..', '..', '..');
const EXT = new Set(['.css', '.scss', '.tsx', '.jsx', '.astro', '.svelte', '.vue']);
const SKIP = new Set(['node_modules', 'dist', '.next', '.astro', 'storybook-static', 'build', 'target']);
const ALLOW_FILE = /^(tokens\.(json|css|ts)|tailwind\.theme\.css)$/;
const files = [];
const collectInto = (p, list) => {
  const st = statSync(p);
  if (st.isDirectory()) { if (!SKIP.has(basename(p))) for (const e of readdirSync(p)) collectInto(join(p, e), list); }
  else if (EXT.has(extname(p)) && !ALLOW_FILE.test(basename(p))) list.push(p);
};
const collect = (p) => collectInto(p, files);

const COLOR = /((?<![\w#])#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|oklch)\()/;
const FONTSIZE = /font-size\s*:\s*(\d*\.?\d+)(px|rem|em|pt)/;
const INLINE = /style\s*=\s*["'{][^"'}]*(color|font-size)\s*:/;
const scan = (list) => {
  const hits = [];
  for (const f of list) {
    const lines = readFileSync(f, 'utf8').split('\n');
    lines.forEach((line, i) => {
      if (/^\s*(\/\/|\/\*|\*|`|\{\/\*)/.test(line)) return; // comments and template text may mention hex
      line = line.replace(/\/\*.*?\*\//g, '').replace(/\/\/\s.*$/, '');
      if (COLOR.test(line) && !/url\(|#\w+\s*\{|href=|id=|key=/.test(line)) hits.push({ file: f, at: i + 1, kind: 'colour literal', text: line.trim().slice(0, 90) });
      if (FONTSIZE.test(line) && !/var\(--type-/.test(line)) hits.push({ file: f, at: i + 1, kind: 'off-scale size', text: line.trim().slice(0, 90) });
      if (INLINE.test(line)) hits.push({ file: f, at: i + 1, kind: 'inline style', text: line.trim().slice(0, 90) });
    });
  }
  return hits;
};
const fmt = (h) => `${h.file}:${h.at}  ${h.kind}   ${h.text}`;
const counts = (hits) => hits.reduce((m, h) => { m[h.kind] = (m[h.kind] || 0) + 1; return m; }, {});
const perFile = (hits) => { const m = new Map(); for (const h of hits) m.set(h.file, (m.get(h.file) ?? 0) + 1); return m; };

// ---- the base: what main holds, measured with the same rules ---------------------------------
const BASE_REF = process.env.ESTATE_PURITY_BASE || 'origin/main';
const git = (args, cwd = repoRoot) => execFileSync('git', args, { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });

// Does this checkout carry the base? Each entry may name another checkout (the prospector
// surfaces live in their own repo), and each is measured against its own main.
const baseAvailable = (root) => {
  try { git(['rev-parse', '--verify', '--quiet', `${BASE_REF}^{commit}`], root); return true; } catch { return false; }
};

// The base's files for one repo-relative path, materialised in a temp dir. Null when the path
// does not exist on the base -- a new path, whose base count is zero by definition.
const baseTree = (rel, root) => {
  const dir = mkdtempSync(join(tmpdir(), 'estate-purity-base-'));
  try {
    const tar = join(dir, 'base.tar');
    git(['archive', '--format=tar', `--output=${tar}`, BASE_REF, '--', rel], root);
    execFileSync('tar', ['-xf', tar, '-C', dir], { stdio: 'ignore' });
    rmSync(tar);
    return dir;
  } catch {
    rmSync(dir, { recursive: true, force: true });
    return null;
  }
};

// The base's violation counts for one entry, per file, keyed by repo-relative path, with the
// nested entries' files excluded exactly as the branch's count excludes them.
const baseCounts = (e, nested) => {
  const dir = baseTree(e.path, e.root);
  if (!dir) return new Map();
  try {
    const list = [];
    collectInto(join(dir, e.path), list);
    const nestedAbs = nested.map((n) => join(dir, n.path));
    const mine = list.filter((f) => !nestedAbs.some((n) => f.startsWith(n + '/')));
    const per = new Map();
    for (const h of scan(mine)) {
      const rel = relative(dir, h.file);
      per.set(rel, (per.get(rel) ?? 0) + 1);
    }
    return per;
  } finally { rmSync(dir, { recursive: true, force: true }); }
};

// The files this branch changed, repo-relative. `A...HEAD` is the branch's own work since the
// merge base, which is what the teeth are measured over. Untracked files count too: a file that
// has never been committed is still a file the branch added, and a local run must not be
// greener than the CI run of the same tree.
const touchedFiles = () => {
  const set = new Set();
  try {
    for (const line of git(['diff', '--name-only', `${BASE_REF}...HEAD`]).split('\n')) if (line) set.add(line);
  } catch { /* no base: no teeth */ }
  try {
    for (const line of git(['ls-files', '--others', '--exclude-standard']).split('\n')) if (line) set.add(line);
  } catch { /* not a git checkout: no untracked files */ }
  return set;
};

// ---- budget mode (the ratchet) ---------------------------------------------------------------
const budgetArg = process.argv.indexOf('--budget');
if (budgetArg !== -1) {
  const budgetPath = budgetArg + 1 < process.argv.length ? process.argv[budgetArg + 1] : join(kitRoot, 'guards', 'budget.json');
  if (!existsSync(budgetPath)) { console.error(`purity: no budget file at ${budgetPath}`); process.exit(1); }
  const budget = JSON.parse(readFileSync(budgetPath, 'utf8'));
  const roots = new Map(); // repo name -> checkout root
  const entries = Object.entries(budget).filter(([path]) => !path.startsWith('$')).map(([path, spec]) => {
    const s = typeof spec === 'number' ? { max: spec } : spec;
    const root = s.root ? s.root.replace(/^~/, process.env.HOME ?? '') : repoRoot;
    return { path, max: s.max, root, repo: s.repo ?? 'idp' };
  });
  const hasBase = baseAvailable(repoRoot);
  const touched = hasBase ? touchedFiles() : new Set();
  if (!hasBase) console.log(`note   no base (${BASE_REF}) in this checkout: judging the cap alone`);
  let fail = 0;
  for (const e of entries) {
    const abs = resolve(e.root, e.path);
    if (!existsSync(abs)) { console.log(`skip   ${e.path}: not in this checkout (${e.repo})`); continue; }
    // A nested entry owns its own files: exclude them from the parent's count.
    const nested = entries.filter((o) => o !== e && o.root === e.root && o.path.startsWith(e.path + '/'));
    files.length = 0;
    collect(abs);
    const mine = files.filter((f) => !nested.some((n) => f.startsWith(resolve(n.root, n.path) + '/')));
    const hits = scan(mine);
    const n = hits.length;
    const per = new Map();
    for (const h of hits) {
      const rel = relative(e.root, h.file);
      per.set(rel, (per.get(rel) ?? 0) + 1);
    }
    // The base: main's own count for this path, measured the same way. An entry in another
    // checkout is measured against that checkout's main.
    const basePer = baseAvailable(e.root) ? baseCounts(e, nested) : null;
    const baseN = basePer ? [...basePer.values()].reduce((a, b) => a + b, 0) : null;
    const limit = baseN === null ? e.max : Math.max(e.max, baseN);
    // The teeth: what the branch added in the files it touched, file by file.
    let added = 0;
    const addedFiles = [];
    if (basePer) {
      for (const [f, c] of per) {
        if (!touched.has(f)) continue;
        const d = c - (basePer.get(f) ?? 0);
        if (d > 0) { added += d; addedFiles.push(`${f} (+${d})`); }
      }
    }
    const overCap = n > limit;
    const regressed = added > 0;
    const staleCap = baseN !== null && e.max > baseN;
    const c = counts(hits);
    const detail = n ? ` (${Object.entries(c).map(([k, v]) => `${k}: ${v}`).join(', ')})` : '';
    const baseNote = baseN === null ? '' : `, main ${baseN}`;
    if (overCap) {
      console.error(`REFUSE ${e.path}: ${n} violations, cap ${limit} (budget ${e.max}${baseNote})`);
      console.error(hits.slice(0, 10).map((h) => '  ' + fmt(h)).join('\n'));
      fail = 1;
    } else if (regressed) {
      console.error(`REFUSE ${e.path}: the branch added ${added} violation(s) in the files it touched`);
      console.error(addedFiles.slice(0, 10).map((f) => '  ' + f).join('\n'));
      fail = 1;
    } else if (staleCap) {
      console.log(`stale  ${e.path}: ${n}/${limit} violations${baseNote} -- the cap ${e.max} is looser than main's own ${baseN}; re-tighten it`);
    } else {
      console.log(`ok     ${e.path}: ${n}/${limit} violations${baseNote}${detail}`);
    }
  }
  process.exit(fail);
}

// ---- strict mode ------------------------------------------------------------------------------
for (const a of process.argv.slice(2)) collect(a);
const hits = scan(files);
if (hits.length) {
  const c = counts(hits);
  console.error(`purity: ${hits.length} violations in ${files.length} files — ` + Object.entries(c).map(([k, v]) => `${k}: ${v}`).join(', '));
  console.error(hits.slice(0, 40).map((h) => '  ' + fmt(h)).join('\n') + (hits.length > 40 ? `\n  … ${hits.length - 40} more` : ''));
  process.exit(1);
}
console.log(`purity: ${files.length} files, 0 violations`);
