#!/usr/bin/env node
// voice-lint — measures the prose in this repo against VOICE.md.
//
// It does not guess at quality. It extracts prose, counts four things that separate
// human editorial writing from machine marketing copy, and exits non-zero when a
// rule in VOICE.md breaks. Every threshold below is the number written in VOICE.md.
//
//   node scripts/voice-lint.mjs           # fail on a broken rule
//   node scripts/voice-lint.mjs --report  # print numbers, always exit 0

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const ROOT = new URL("..", import.meta.url).pathname;
const REPORT_ONLY = process.argv.includes("--report");
const SELF_TEST = process.argv.includes("--self-test");

// ---------------------------------------------------------------- collection

const SCAN = ["content", "app", "components"];
const SKIP_DIR = new Set(["node_modules", ".next", ".git"]);

function walk(dir, out = []) {
  for (const entry of readdirSync(dir)) {
    if (SKIP_DIR.has(entry)) continue;
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) walk(full, out);
    else if (/\.(tsx?|mjs)$/.test(entry)) out.push(full);
  }
  return out;
}

// Prose is any double-quoted literal with enough words to be a sentence.
// Everything else in these files is class names, CSS values and import paths.
const CODE_SHAPED =
  /var\(--|\d+px|rgba?\(|next\/|@\/|\/api|=>|[{}\[\]]|;\s*$|\b(const|return|import|export|function|let|var|await|async|className|useState|useEffect|createElement)\b|^\s*(flex|grid|none|auto|block|center|column|row|wrap)\s*$|^[a-z-]+:( |$)/;

const ENTITIES = { "&#x27;": "'", "&#39;": "'", "&amp;": "&", "&quot;": '"', "&gt;": ">", "&lt;": "<" };

function decode(text) {
  return text.replace(/&#x27;|&#39;|&amp;|&quot;|&gt;|&lt;/g, (e) => ENTITIES[e]);
}

// Two places prose lives in this repo: double-quoted literals in the content
// files, and JSX text nodes between tags in the pages. Both are needed; reading
// only literals would miss most of the page copy and quietly flatter the score.
function proseFrom(source) {
  const found = [];

  const push = (raw) => {
    const text = decode(raw).replace(/\\n/g, " ").replace(/\s+/g, " ").trim();
    const words = text.split(" ").filter((w) => /[a-zA-Z]/.test(w));
    if (words.length < 8) return;
    if (CODE_SHAPED.test(text)) return;
    found.push(text);
  };

  // 1. String literals.
  const literal = /"((?:[^"\\]|\\.){20,})"/g;
  let m;
  while ((m = literal.exec(source))) push(m[1].replace(/\\"/g, '"'));

  // 2. Template literals — the post bodies live here, and they are the longest
  // prose on the site. Skipping them would mean the linter never reads the pages
  // a reader actually spends time on.
  const template = /`([^`]{40,})`/g;
  while ((m = template.exec(source))) push(m[1].replace(/\$\{[^}]*\}/g, " "));

  // 3. JSX text nodes: whatever sits between > and <.
  const node = />([^<>{}]{20,})</g;
  while ((m = node.exec(source))) push(m[1]);

  return found;
}

// ---------------------------------------------------------------- measures

const BANNED = [
  "delve", "leverage", "robust", "seamless", "cutting-edge", "cutting edge",
  "ever-evolving", "ever evolving", "landscape", "tapestry", "testament to",
  "unlock", "empower", "elevate", "unparalleled", "game-changer", "game changer",
  "supercharge", "harness the power", "dive into", "best-in-class", "best in class",
  "world-class", "world class", "next-generation", "state-of-the-art",
  "state of the art", "holistic", "synergy", "streamline", "revolutionize",
  "in today's", "gone are the days", "whether you're", "more than just",
  "it's not just", "at the end of the day", "the future of",
];

const HEDGES = ["very", "quite", "really", "simply", "actually", "arguably", "somewhat"];

// A run of words with no sentence punctuation is a list fragment, not a sentence.
// Including those corrupts the deviation measure with one enormous outlier, so
// they are dropped — and counted, so the drop is visible rather than silent.
const MAX_SENTENCE_WORDS = 60;

function sentencesOf(text) {
  return text
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter((s) => {
      const n = s.split(/\s+/).filter(Boolean).length;
      return n > 1 && n <= MAX_SENTENCE_WORDS;
    });
}

function wordsOf(text) {
  return text.split(/\s+/).filter((w) => /[a-zA-Z0-9]/.test(w));
}

function countMatches(text, terms) {
  const lower = text.toLowerCase();
  const hits = [];
  for (const term of terms) {
    // Word-ish boundary: avoids "leverage" matching inside "leverages" only if wanted;
    // we do want inflections, so this stays a plain includes with a leading boundary.
    const re = new RegExp(`\\b${term.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\\\$&")}`, "g");
    const n = (lower.match(re) || []).length;
    if (n) hits.push({ term, n });
  }
  return hits;
}

// ---------------------------------------------------------------- thresholds
// The numbers here are the numbers in VOICE.md. Change one, change both.

const LIMITS = {
  emDashPer100: 1.0,
  shortSentenceRatio: 0.15,
  sentenceSigma: 5.0,
  adverbPer100: 4.0,
  hedgePer100: 2.0,
  triadPer100: 1.2,
  ticPer1000: 8,
};

// A word that recurs past the tic limit is a habit, not emphasis. "production"
// and "actually" are the two this site reaches for when it has nothing to say.
const STOPWORDS = new Set(
  ("a an the and or but if then than that this these those it its is are was were be been " +
    "being to of in on at for with from by as into over under we you your our they them their " +
    "he she his her my me not no so up out about more most other some such only own same too " +
    "can will do does did done have has had having what which who whom when where why how all " +
    "any both each few many much neither nor now once per via also very").split(/\s+/)
);

// "not just X" / "not only X but Y" — the construction used to imply depth.
const NOT_JUST = /\bnot\s+(just|only|merely|simply)\b/gi;
// Two or three items joined as a list. Generated copy resolves almost every
// sentence into one of these; human copy does it occasionally.
const TRIAD = /\b\w+,\s+\w+,\s+(?:and|or)\s+\w+/g;

// ---------------------------------------------------------------- run

const files = SCAN.flatMap((d) => {
  try { return walk(join(ROOT, d)); } catch { return []; }
});

let allText = "";
const perFile = [];
const bannedHits = [];

for (const file of files) {
  const source = readFileSync(file, "utf8");
  const chunks = proseFrom(source);
  if (!chunks.length) continue;
  const text = chunks.join(" ");
  allText += " " + text;
  perFile.push({ file: relative(ROOT, file), text });

  for (const hit of countMatches(text, BANNED)) {
    bannedHits.push({ file: relative(ROOT, file), ...hit });
  }
}

// Nouns that are the subject of this site, not a verbal habit. They repeat
// because the work repeats. Everything outside this list is held to the limit.
const DOMAIN = new Set([
  "model", "models", "latency", "routing", "route", "routed", "inference", "eval",
  "evals", "evaluation", "token", "tokens", "cost", "costs", "spend", "deployment",
  "deployments", "production", "pipeline", "pipelines", "trace", "traces", "identity",
  "workload", "workloads", "fallback", "circuit", "breaker", "team", "teams",
]);

// Score one block of prose. Shared by the real corpus and by --self-test, so the
// self-test cannot drift from the rules it is meant to prove still bite.
function score(allText, bannedHits) {
const rawSentenceCount = allText.split(/(?<=[.!?])\s+/).filter((s) => s.trim()).length;

const sentences = sentencesOf(allText);
const words = wordsOf(allText);
const wordCount = words.length;

const lengths = sentences.map((s) => s.split(/\s+/).length);
const mean = lengths.reduce((a, b) => a + b, 0) / lengths.length;
const sigma = Math.sqrt(lengths.reduce((a, b) => a + (b - mean) ** 2, 0) / lengths.length);
const shortRatio = lengths.filter((l) => l < 10).length / lengths.length;
const emDashes = (allText.match(/—/g) || []).length;
const adverbs = words.filter((w) => /ly[.,;:]?$/i.test(w) && w.length > 4).length;
const hedgeHits = countMatches(allText, HEDGES).reduce((a, h) => a + h.n, 0);
const notJust = (allText.match(NOT_JUST) || []).length;
const triads = (allText.match(TRIAD) || []).length;

const freq = new Map();
for (const raw of words) {
  const w = raw.toLowerCase().replace(/[^a-z']/g, "");
  if (w.length < 4 || STOPWORDS.has(w) || DOMAIN.has(w)) continue;
  freq.set(w, (freq.get(w) || 0) + 1);
}
const tics = [...freq.entries()]
  .map(([word, n]) => ({ word, n, per1000: (n / wordCount) * 1000 }))
  .filter((t) => t.per1000 > LIMITS.ticPer1000)
  .sort((a, b) => b.per1000 - a.per1000);

const per100 = (n) => (wordCount ? (n / wordCount) * 100 : 0);

const results = [
  {
    rule: "no AI tells",
    ok: bannedHits.length === 0,
    detail: bannedHits.length
      ? bannedHits.map((h) => `"${h.term}"×${h.n} in ${h.file}`).join("; ")
      : "clean",
    limit: "0 hits",
  },
  {
    rule: "em dashes",
    ok: per100(emDashes) <= LIMITS.emDashPer100,
    detail: `${per100(emDashes).toFixed(2)} per 100 words (${emDashes} total)`,
    limit: `≤ ${LIMITS.emDashPer100}`,
  },
  {
    rule: "short sentences",
    ok: shortRatio >= LIMITS.shortSentenceRatio,
    detail: `${(shortRatio * 100).toFixed(0)}% of sentences under 10 words`,
    limit: `≥ ${LIMITS.shortSentenceRatio * 100}%`,
  },
  {
    rule: "sentence deviation",
    ok: sigma >= LIMITS.sentenceSigma,
    detail: `σ = ${sigma.toFixed(1)} words (mean ${mean.toFixed(1)})`,
    limit: `≥ ${LIMITS.sentenceSigma}`,
  },
  {
    rule: "adverbs",
    ok: per100(adverbs) <= LIMITS.adverbPer100,
    detail: `${per100(adverbs).toFixed(2)} per 100 words (${adverbs} total)`,
    limit: `≤ ${LIMITS.adverbPer100}`,
  },
  {
    rule: "hedges",
    ok: per100(hedgeHits) <= LIMITS.hedgePer100,
    detail: `${per100(hedgeHits).toFixed(2)} per 100 words (${hedgeHits} total)`,
    limit: `≤ ${LIMITS.hedgePer100}`,
  },
  {
    rule: "list constructions",
    ok: per100(triads) <= LIMITS.triadPer100,
    detail: `${per100(triads).toFixed(2)} per 100 words (${triads} total)`,
    limit: `≤ ${LIMITS.triadPer100}`,
  },
  {
    rule: "not just / not only",
    ok: notJust === 0,
    detail: `${notJust} occurrences`,
    limit: "0",
  },
  {
    rule: "word tics",
    ok: tics.length === 0,
    detail: tics.length ? tics.map((t) => `"${t.word}"×${t.n}`).join(", ") : "none",
    limit: `≤ ${LIMITS.ticPer1000}/1000 each`,
  },
];

return { rawSentenceCount, sentenceCount: sentences.length, wordCount, results };
}

const pad = (s, n) => s + " ".repeat(Math.max(0, n - s.length));

// ---------------------------------------------------------------- self-test
// A gate that cannot fail is not a gate. This sample is written the way a model
// writes when it is not being watched, and the linter must reject it.
if (SELF_TEST) {
  const SLOP = `
    In today's ever-evolving landscape, we leverage cutting-edge, robust and seamless
    solutions to unlock your team's potential — and it's not just about tooling — it's
    about transformation — at the end of the day, really just simply quite genuinely
    a testament to what is possible when you empower, elevate and revolutionize.
    Truly, deeply, significantly, dramatically robust. Really quite simply just actually
    very much a game-changer. We streamline, we supercharge, we dive into the future.
  `;
  const bad = score(SLOP, countMatches(SLOP, BANNED).map((h) => ({ file: "<self-test>", ...h })));
  const failed = bad.results.filter((r) => !r.ok).map((r) => r.rule);
  const mustFail = ["no AI tells", "em dashes", "not just / not only"];
  const missing = mustFail.filter((r) => !failed.includes(r));

  console.log(`\nvoice-lint --self-test`);
  console.log(`  slop sample fails ${failed.length}/${bad.results.length} rules: ${failed.join(", ")}`);
  if (missing.length) {
    console.log(`  BROKEN: the linter no longer rejects: ${missing.join(", ")}`);
    console.log(`  A rule that cannot fire is not a rule.\n`);
    process.exit(1);
  }
  console.log(`  gate bites: yes\n`);
  process.exit(0);
}

const scored = score(allText, bannedHits);
const { results } = scored;
const passed = results.filter((r) => r.ok).length;

console.log(
  `\nvoice-lint — ${files.length} source files, ${perFile.length} with prose, ` +
    `${scored.wordCount} words, ${scored.sentenceCount} sentences ` +
    `(${scored.rawSentenceCount - scored.sentenceCount} unpunctuated runs dropped)\n`
);
for (const r of results) {
  console.log(`  ${r.ok ? "ok  " : "FAIL"}  ${pad(r.rule, 20)} ${pad(r.detail, 46)} ${r.limit}`);
}
console.log(`\n  ${passed}/${results.length} rules pass\n`);

if (REPORT_ONLY) process.exit(0);
process.exit(passed === results.length ? 0 : 1);
