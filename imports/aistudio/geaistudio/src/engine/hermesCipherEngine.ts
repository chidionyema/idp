/**
 * Certified Deterministic Isopsephy, Gematria & Legacy Compatibility Core.
 * Zero Node-only imports so both browser and server execute identical math.
 *
 * Recovered from chidionyema/hermes-v2 commit 1220c4ad:
 *   - patches/hermes-agent/0001-feat-summary-port-the-isopsephy-card-from-the-old-es.patch
 *   - gateway/qabalah.py (27-letter Greek isopsephy, Hebrew Mispar Hechrechi & Mispar Gadol,
 *     English Extended 26-letter non-colliding table, 37-word live-summed canon)
 *   - gateway/summary_card.py (Pythagorean, Chaldean, Legacy Hebrew A-V/W-Z wraparound)
 */

export type ScriptKind = 'greek' | 'hebrew' | 'latin';

export type CipherId =
  | 'greek_isopsephy'
  | 'hebrew_hechrechi'
  | 'hebrew_gadol'
  | 'english_extended'
  | 'legacy_pythagorean'
  | 'legacy_hebrew_wraparound'
  | 'legacy_chaldean';

export interface LetterBreakdownItem {
  originalChar: string;
  normalizedChar: string;
  letterName: string;
  value: number;
  index: number;
}

export interface SkippedCharacterItem {
  char: string;
  codePoint: string;
  reason: 'whitespace' | 'digit' | 'punctuation' | 'unsupported_script';
}

export interface ReadingResult {
  cipherId: CipherId;
  cipherVersion: string;
  system: string;
  script: ScriptKind;
  total: number;
  treeRoot: number; // 1..10 (stops at 10 for Malkuth; 0 when total === 0)
  legacyMasterRoot: number; // 1..9 or master 11, 22, 33
  reductionLadder: number[];
  breakdown: LetterBreakdownItem[];
  scored: number;
  skipped: number;
  skippedChars: SkippedCharacterItem[];
  reproducibilityHash: string;
  legacyWarning?: string;
}

export interface CanonEntry {
  canonicalId: string;
  word: string;
  transliteration: string;
  gloss: string;
  script: 'hebrew' | 'greek';
  sourceCitation: string;
  theme: 'divine_names' | 'sephirot' | 'classical_isopsephy' | 'wisdom';
}

export interface CanonComputedEntry extends CanonEntry {
  reading: ReadingResult;
}

export interface DualModeDiffReport {
  input: string;
  legacyWraparound: ReadingResult;
  englishExtended: ReadingResult;
  collidingWrapChars: string[];
  hasWraparoundDefect: boolean;
  explanation: string;
}

// ---------------------------------------------------------------------------
// 1. GREEK ISOPSEPHY — 24 Classical Letters + 3 Archaic Numerals (1..900)
// ---------------------------------------------------------------------------
export const GREEK_ROWS: ReadonlyArray<readonly [string, string, number]> = [
  ['α', 'alpha', 1],
  ['β', 'beta', 2],
  ['γ', 'gamma', 3],
  ['δ', 'delta', 4],
  ['ε', 'epsilon', 5],
  ['ϝ', 'digamma', 6],
  ['ζ', 'zeta', 7],
  ['η', 'eta', 8],
  ['θ', 'theta', 9],
  ['ι', 'iota', 10],
  ['κ', 'kappa', 20],
  ['λ', 'lambda', 30],
  ['μ', 'mu', 40],
  ['ν', 'nu', 50],
  ['ξ', 'xi', 60],
  ['ο', 'omicron', 70],
  ['π', 'pi', 80],
  ['ϙ', 'koppa', 90],
  ['ρ', 'rho', 100],
  ['σ', 'sigma', 200],
  ['τ', 'tau', 300],
  ['υ', 'upsilon', 400],
  ['φ', 'phi', 500],
  ['χ', 'chi', 600],
  ['ψ', 'psi', 700],
  ['ω', 'omega', 800],
  ['ϡ', 'sampi', 900],
];

export const GREEK_TABLE: Record<string, { value: number; name: string }> = {};
for (const [ch, name, val] of GREEK_ROWS) {
  GREEK_TABLE[ch] = { value: val, name };
  GREEK_TABLE[ch.toUpperCase()] = { value: val, name };
}
// Classical positional/numeral variants matching gateway/qabalah.py
const GREEK_ALIASES: ReadonlyArray<readonly [string, string, string]> = [
  ['ς', 'σ', 'sigma (final)'],
  ['ϲ', 'σ', 'sigma (lunate)'],
  ['Ϲ', 'σ', 'sigma (lunate)'],
  ['ϛ', 'ϝ', 'stigma (digamma numeral)'],
  ['Ϛ', 'ϝ', 'stigma (digamma numeral)'],
  ['ϟ', 'ϙ', 'koppa (modern numeral)'],
  ['Ϟ', 'ϙ', 'koppa (modern numeral)'],
  ['Ϝ', 'ϝ', 'digamma'],
  ['Ϙ', 'ϙ', 'koppa'],
  ['Ϡ', 'ϡ', 'sampi'],
];
for (const [alias, base, label] of GREEK_ALIASES) {
  GREEK_TABLE[alias] = { value: GREEK_TABLE[base].value, name: label };
}

// ---------------------------------------------------------------------------
// 2. HEBREW GEMATRIA — Mispar Hechrechi & Mispar Gadol (finals 500..900)
// ---------------------------------------------------------------------------
export const HEBREW_ROWS: ReadonlyArray<readonly [string, string, number]> = [
  ['א', 'aleph', 1],
  ['ב', 'beth', 2],
  ['ג', 'gimel', 3],
  ['ד', 'daleth', 4],
  ['ה', 'he', 5],
  ['ו', 'vav', 6],
  ['ז', 'zayin', 7],
  ['ח', 'cheth', 8],
  ['ט', 'teth', 9],
  ['י', 'yod', 10],
  ['כ', 'kaph', 20],
  ['ל', 'lamed', 30],
  ['מ', 'mem', 40],
  ['נ', 'nun', 50],
  ['ס', 'samekh', 60],
  ['ע', 'ayin', 70],
  ['פ', 'pe', 80],
  ['צ', 'tzaddi', 90],
  ['ק', 'qoph', 100],
  ['ר', 'resh', 200],
  ['ש', 'shin', 300],
  ['ת', 'tav', 400],
];

export const HEBREW_SOFIT_ROWS: ReadonlyArray<readonly [string, string, number, number]> = [
  ['ך', 'כ', 20, 500],
  ['ם', 'מ', 40, 600],
  ['ן', 'נ', 50, 700],
  ['ף', 'פ', 80, 800],
  ['ץ', 'צ', 90, 900],
];

export const HEBREW_TABLE: Record<string, { value: number; name: string }> = {};
export const HEBREW_GADOL_TABLE: Record<string, { value: number; name: string }> = {};
for (const [ch, name, val] of HEBREW_ROWS) {
  HEBREW_TABLE[ch] = { value: val, name };
  HEBREW_GADOL_TABLE[ch] = { value: val, name };
}
for (const [sofit, base, stdVal, gadolVal] of HEBREW_SOFIT_ROWS) {
  const baseName = HEBREW_TABLE[base].name;
  HEBREW_TABLE[sofit] = { value: stdVal, name: `${baseName} sofit` };
  HEBREW_GADOL_TABLE[sofit] = { value: gadolVal, name: `${baseName} sofit (gadol)` };
}

// ---------------------------------------------------------------------------
// 3. ENGLISH EXTENDED vs LEGACY WRAPAROUND (preserving recovered W=A bug)
// ---------------------------------------------------------------------------
export const ENGLISH_EXT_TABLE: Record<string, { value: number; name: string }> = {};
'ABCDEFGHI'.split('').forEach((ch, idx) => {
  ENGLISH_EXT_TABLE[ch] = { value: idx + 1, name: ch };
});
'JKLMNOPQR'.split('').forEach((ch, idx) => {
  ENGLISH_EXT_TABLE[ch] = { value: (idx + 1) * 10, name: ch };
});
'STUVWXYZ'.split('').forEach((ch, idx) => {
  ENGLISH_EXT_TABLE[ch] = { value: (idx + 1) * 100, name: ch };
});

// Exact `_GEMATRIA` from gateway/summary_card.py: A–V map 1..400, W–Z wrap to 1,2,3,4
const HEBREW_22_SEQ = [
  1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 200, 300, 400,
];
export const LEGACY_HEBREW_WRAP_TABLE: Record<string, { value: number; name: string }> = {};
'ABCDEFGHIJKLMNOPQRSTUV'.split('').forEach((ch, idx) => {
  LEGACY_HEBREW_WRAP_TABLE[ch] = { value: HEBREW_22_SEQ[idx], name: ch };
});
'WXYZ'.split('').forEach((ch, idx) => {
  LEGACY_HEBREW_WRAP_TABLE[ch] = { value: HEBREW_22_SEQ[idx], name: `${ch} (legacy wrap)` };
});

export const PYTHAGOREAN_TABLE: Record<string, { value: number; name: string }> = {};
'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('').forEach((ch, idx) => {
  PYTHAGOREAN_TABLE[ch] = { value: (idx % 9) + 1, name: ch };
});

const CHALDEAN_VALUES: Record<string, number> = {
  A: 1, B: 2, C: 3, D: 4, E: 5, F: 8, G: 3, H: 5, I: 1,
  J: 1, K: 2, L: 3, M: 4, N: 5, O: 7, P: 8, Q: 1, R: 2,
  S: 3, T: 4, U: 6, V: 6, W: 6, X: 5, Y: 1, Z: 7,
};
export const CHALDEAN_TABLE: Record<string, { value: number; name: string }> = {};
for (const [k, v] of Object.entries(CHALDEAN_VALUES)) {
  CHALDEAN_TABLE[k] = { value: v, name: k };
}

// ---------------------------------------------------------------------------
// 4. NORMALIZATION, REDUCTIONS & REPRODUCIBILITY FINGERPRINT
// ---------------------------------------------------------------------------

export interface SanitizedHermesInput {
  cleaned: string;
  strippedControlOrBidi: number;
  maxCharsExceeded: boolean;
  wasTruncated: boolean;
}

export const HERMES_MAX_INPUT_CHARS = 2400;

/**
 * Strips C0/C1 control characters (except standard whitespace) and Unicode bidirectional
 * override characters (Trojan Source U+202A..U+202E, U+2066..U+2069) before cipher scoring.
 */
export function sanitizeHermesInput(
  raw: string,
  maxChars = HERMES_MAX_INPUT_CHARS
): SanitizedHermesInput {
  let stripped = 0;
  let buf = '';
  for (const ch of raw) {
    const cp = ch.codePointAt(0) ?? 0;
    const isUnsafeControl =
      (cp < 0x20 && cp !== 0x09 && cp !== 0x0a && cp !== 0x0d) ||
      cp === 0x7f ||
      (cp >= 0x80 && cp <= 0x9f);
    const isBidiOverride =
      (cp >= 0x202a && cp <= 0x202e) || (cp >= 0x2066 && cp <= 0x2069);
    if (isUnsafeControl || isBidiOverride) {
      stripped++;
    } else {
      buf += ch;
    }
  }
  const maxCharsExceeded = buf.length > maxChars;
  const cleaned = maxCharsExceeded ? buf.slice(0, maxChars) : buf;
  return {
    cleaned,
    strippedControlOrBidi: stripped,
    maxCharsExceeded,
    wasTruncated: maxCharsExceeded,
  };
}

/** Strip non-spacing marks (Greek accents/breathings, Hebrew niqqud/cantillation) under NFD */
export function stripDiacriticsNfd(text: string): string {
  return sanitizeHermesInput(text).cleaned.normalize('NFD').replace(/\p{Mn}/gu, '');
}

/**
 * Tree reduction from qabalah.py (`_digital_root`):
 * Reduces positive integers to 1..10, stopping at 10 (Malkuth) rather than folding to 1 (Kether).
 * Example: מלכות = 496 -> 19 -> 10 (Malkuth), NOT 1 (Kether).
 */
export function treeDigitalRoot(n: number): number {
  if (n <= 0) return 0;
  let cur = Math.floor(n);
  while (cur > 10) {
    let next = 0;
    for (const d of String(cur)) next += Number(d);
    cur = next;
  }
  return cur;
}

/**
 * Legacy reduction from summary_card.py (`_reduce`):
 * Preserves Master Numbers 11, 22, 33; reduces all other sums down to 1..9.
 */
export function legacyReduceWithMasters(n: number): { root: number; ladder: number[] } {
  if (n <= 0) return { root: 0, ladder: [0] };
  let cur = Math.floor(n);
  const ladder = [cur];
  while (cur > 9) {
    if (cur === 11 || cur === 22 || cur === 33) break;
    let next = 0;
    for (const d of String(cur)) next += Number(d);
    cur = next;
    ladder.push(cur);
  }
  return { root: cur, ladder };
}

/** Deterministic FNV-1a 32-bit hex digest for pure browser+server reproducibility hashing */
export function computeReproducibilityHash(payload: string): string {
  let h = 0x811c9dc5;
  for (let i = 0; i < payload.length; i++) {
    h ^= payload.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return `hermes-${(h >>> 0).toString(16).padStart(8, '0')}`;
}

function classifySkipped(ch: string): SkippedCharacterItem['reason'] {
  if (/\s/.test(ch)) return 'whitespace';
  if (/[0-9]/.test(ch)) return 'digit';
  if (/[\p{P}\p{S}]/u.test(ch)) return 'punctuation';
  return 'unsupported_script';
}

function scoreWithTable(
  text: string,
  table: Record<string, { value: number; name: string }>,
  options: {
    cipherId: CipherId;
    cipherVersion: string;
    system: string;
    script: ScriptKind;
    uppercaseInput?: boolean;
    legacyWarning?: string;
  }
): ReadingResult {
  const source = options.uppercaseInput ? stripDiacriticsNfd(text).toUpperCase() : stripDiacriticsNfd(text);
  const breakdown: LetterBreakdownItem[] = [];
  const skippedChars: SkippedCharacterItem[] = [];

  let idx = 0;
  for (const ch of source) {
    const entry = table[ch];
    if (entry) {
      breakdown.push({
        originalChar: ch,
        normalizedChar: ch,
        letterName: entry.name,
        value: entry.value,
        index: idx,
      });
    } else if (!/\s/.test(ch)) {
      const cp = ch.codePointAt(0);
      skippedChars.push({
        char: ch,
        codePoint: cp !== undefined ? `U+${cp.toString(16).toUpperCase().padStart(4, '0')}` : 'U+0000',
        reason: classifySkipped(ch),
      });
    }
    idx++;
  }

  const total = breakdown.reduce((acc, b) => acc + b.value, 0);
  const treeRoot = treeDigitalRoot(total);
  const { root: legacyMasterRoot, ladder } = legacyReduceWithMasters(total);
  const hash = computeReproducibilityHash(
    `${options.cipherId}|${options.cipherVersion}|${source}|${total}`
  );

  return {
    cipherId: options.cipherId,
    cipherVersion: options.cipherVersion,
    system: options.system,
    script: options.script,
    total,
    treeRoot,
    legacyMasterRoot,
    reductionLadder: ladder,
    breakdown,
    scored: breakdown.length,
    skipped: skippedChars.length,
    skippedChars,
    reproducibilityHash: hash,
    legacyWarning: options.legacyWarning,
  };
}

export function scoreGreekIsopsephy(text: string): ReadingResult {
  return scoreWithTable(text, GREEK_TABLE, {
    cipherId: 'greek_isopsephy',
    cipherVersion: 'qabalah-1.0.0',
    system: 'Greek isopsephy',
    script: 'greek',
  });
}

export function scoreHebrewGematria(text: string, gadol = false): ReadingResult {
  return scoreWithTable(text, gadol ? HEBREW_GADOL_TABLE : HEBREW_TABLE, {
    cipherId: gadol ? 'hebrew_gadol' : 'hebrew_hechrechi',
    cipherVersion: 'qabalah-1.0.0',
    system: gadol ? 'Hebrew gematria (mispar gadol)' : 'Hebrew gematria',
    script: 'hebrew',
  });
}

export function scoreEnglishExtended(text: string): ReadingResult {
  return scoreWithTable(text, ENGLISH_EXT_TABLE, {
    cipherId: 'english_extended',
    cipherVersion: 'qabalah-1.0.0',
    system: 'English extended',
    script: 'latin',
    uppercaseInput: true,
  });
}

export function scoreLegacyPythagorean(text: string): ReadingResult {
  return scoreWithTable(text, PYTHAGOREAN_TABLE, {
    cipherId: 'legacy_pythagorean',
    cipherVersion: 'summary-card-1.0.0',
    system: 'Pythagorean (Legacy)',
    script: 'latin',
    uppercaseInput: true,
  });
}

export function scoreLegacyHebrewWraparound(text: string): ReadingResult {
  return scoreWithTable(text, LEGACY_HEBREW_WRAP_TABLE, {
    cipherId: 'legacy_hebrew_wraparound',
    cipherVersion: 'summary-card-1.0.0-wraparound',
    system: 'Legacy "Hebrew" Cipher (W=A Wraparound)',
    script: 'latin',
    uppercaseInput: true,
    legacyWarning:
      'Preserved legacy summary_card._GEMATRIA cipher: wraps after V so W=A(1), X=B(2), Y=C(3), Z=D(4). Switch to English Extended for collision-free 26-letter values.',
  });
}

export function scoreLegacyChaldean(text: string): ReadingResult {
  return scoreWithTable(text, CHALDEAN_TABLE, {
    cipherId: 'legacy_chaldean',
    cipherVersion: 'summary-card-1.0.0',
    system: 'Chaldean (Legacy)',
    script: 'latin',
    uppercaseInput: true,
  });
}

export function detectScriptsPresent(text: string): Set<ScriptKind> {
  const cleaned = stripDiacriticsNfd(text);
  const found = new Set<ScriptKind>();
  for (const ch of cleaned) {
    if (GREEK_TABLE[ch]) found.add('greek');
    else if (HEBREW_TABLE[ch]) found.add('hebrew');
    else if (/[A-Za-z]/.test(ch)) found.add('latin');
  }
  return found;
}

export function readingsForText(
  text: string,
  options: { includeLegacyLatin?: boolean } = {}
): ReadingResult[] {
  const present = detectScriptsPresent(text);
  const out: ReadingResult[] = [];
  if (present.has('greek')) {
    out.push(scoreGreekIsopsephy(text));
  }
  if (present.has('hebrew')) {
    const std = scoreHebrewGematria(text, false);
    out.push(std);
    const gadol = scoreHebrewGematria(text, true);
    if (gadol.total !== std.total) {
      out.push(gadol);
    }
  }
  if (present.has('latin')) {
    out.push(scoreEnglishExtended(text));
    if (options.includeLegacyLatin) {
      out.push(scoreLegacyPythagorean(text));
      out.push(scoreLegacyHebrewWraparound(text));
      out.push(scoreLegacyChaldean(text));
    }
  }
  return out;
}

export function inspectDualModeEnglishDiff(text: string): DualModeDiffReport {
  const legacyWraparound = scoreLegacyHebrewWraparound(text);
  const englishExtended = scoreEnglishExtended(text);
  const collidingWrapChars = Array.from(
    new Set(
      stripDiacriticsNfd(text)
        .toUpperCase()
        .split('')
        .filter((c) => c === 'W' || c === 'X' || c === 'Y' || c === 'Z')
    )
  );
  const hasWraparoundDefect = collidingWrapChars.length > 0;
  return {
    input: text,
    legacyWraparound,
    englishExtended,
    collidingWrapChars,
    hasWraparoundDefect,
    explanation: hasWraparoundDefect
      ? `Legacy summary_card wraps ${collidingWrapChars.join(', ')} back to A–D (${legacyWraparound.total}), whereas English Extended preserves unique hundreds values (${englishExtended.total}).`
      : 'No W/X/Y/Z letters present; English Extended separates J–V tens/hundreds cleanly beyond A–I.',
  };
}

// ---------------------------------------------------------------------------
// 5. THE 37-WORD HISTORICAL REFERENCE CANON (zero stored totals!)
// ---------------------------------------------------------------------------
export const CANON_WORDS: ReadonlyArray<CanonEntry> = [
  // Hebrew (22 entries)
  { canonicalId: 'heb-yhwh', word: 'יהוה', transliteration: 'YHWH', gloss: 'the Tetragrammaton', script: 'hebrew', sourceCitation: 'Classical Kabbalah / Tanakh', theme: 'divine_names' },
  { canonicalId: 'heb-elohim', word: 'אלהים', transliteration: 'Elohim', gloss: 'Elohim', script: 'hebrew', sourceCitation: 'Genesis 1:1 / Sefer Yetzirah', theme: 'divine_names' },
  { canonicalId: 'heb-adonai', word: 'אדני', transliteration: 'Adonai', gloss: 'Adonai', script: 'hebrew', sourceCitation: 'Classical Kabbalah', theme: 'divine_names' },
  { canonicalId: 'heb-ehyeh', word: 'אהיה', transliteration: 'Ehyeh', gloss: 'Ehyeh — I Am', script: 'hebrew', sourceCitation: 'Exodus 3:14 / Kether attribution', theme: 'divine_names' },
  { canonicalId: 'heb-echad', word: 'אחד', transliteration: 'echad', gloss: 'echad — one (unity)', script: 'hebrew', sourceCitation: 'Deuteronomy 6:4 · equates with ahavah (13)', theme: 'wisdom' },
  { canonicalId: 'heb-ahavah', word: 'אהבה', transliteration: 'ahavah', gloss: 'ahavah — love', script: 'hebrew', sourceCitation: 'Classical Gematria · equates with echad (13)', theme: 'wisdom' },
  { canonicalId: 'heb-chai', word: 'חי', transliteration: 'chai', gloss: 'chai — life', script: 'hebrew', sourceCitation: 'Classical Hebrew (18)', theme: 'wisdom' },
  { canonicalId: 'heb-emet', word: 'אמת', transliteration: 'emet', gloss: 'emet — truth (aleph-mem-tav)', script: 'hebrew', sourceCitation: 'Talmud Shabbat 55a · first, middle, final letter', theme: 'wisdom' },
  { canonicalId: 'heb-shalom', word: 'שלום', transliteration: 'shalom', gloss: 'shalom — peace', script: 'hebrew', sourceCitation: 'Classical Hebrew', theme: 'wisdom' },
  { canonicalId: 'heb-torah', word: 'תורה', transliteration: 'Torah', gloss: 'Torah', script: 'hebrew', sourceCitation: 'Classical Kabbalah (611)', theme: 'wisdom' },
  { canonicalId: 'heb-mashiach', word: 'משיח', transliteration: 'Mashiach', gloss: 'Mashiach — anointed', script: 'hebrew', sourceCitation: 'Equates with nachash (358)', theme: 'classical_isopsephy' },
  { canonicalId: 'heb-nachash', word: 'נחש', transliteration: 'nachash', gloss: 'nachash — serpent', script: 'hebrew', sourceCitation: 'Zohar / Genesis 3 · equates with Mashiach (358)', theme: 'classical_isopsephy' },
  { canonicalId: 'heb-kether', word: 'כתר', transliteration: 'Kether', gloss: 'Kether — Crown', script: 'hebrew', sourceCitation: 'Sefer Bahir / Zohar (Sephirah 1)', theme: 'sephirot' },
  { canonicalId: 'heb-chokmah', word: 'חכמה', transliteration: 'Chokmah', gloss: 'Chokmah — Wisdom', script: 'hebrew', sourceCitation: 'Sefer Yetzirah (Sephirah 2)', theme: 'sephirot' },
  { canonicalId: 'heb-binah', word: 'בינה', transliteration: 'Binah', gloss: 'Binah — Understanding', script: 'hebrew', sourceCitation: 'Sefer Yetzirah (Sephirah 3)', theme: 'sephirot' },
  { canonicalId: 'heb-chesed', word: 'חסד', transliteration: 'Chesed', gloss: 'Chesed — Mercy', script: 'hebrew', sourceCitation: 'Zohar (Sephirah 4)', theme: 'sephirot' },
  { canonicalId: 'heb-geburah', word: 'גבורה', transliteration: 'Geburah', gloss: 'Geburah — Severity', script: 'hebrew', sourceCitation: 'Zohar (Sephirah 5)', theme: 'sephirot' },
  { canonicalId: 'heb-tiphareth', word: 'תפארת', transliteration: 'Tiphareth', gloss: 'Tiphareth — Beauty', script: 'hebrew', sourceCitation: 'Zohar (Sephirah 6)', theme: 'sephirot' },
  { canonicalId: 'heb-netzach', word: 'נצח', transliteration: 'Netzach', gloss: 'Netzach — Victory', script: 'hebrew', sourceCitation: 'Zohar (Sephirah 7)', theme: 'sephirot' },
  { canonicalId: 'heb-hod', word: 'הוד', transliteration: 'Hod', gloss: 'Hod — Splendour', script: 'hebrew', sourceCitation: 'Zohar (Sephirah 8)', theme: 'sephirot' },
  { canonicalId: 'heb-yesod', word: 'יסוד', transliteration: 'Yesod', gloss: 'Yesod — Foundation', script: 'hebrew', sourceCitation: 'Zohar (Sephirah 9)', theme: 'sephirot' },
  { canonicalId: 'heb-malkuth', word: 'מלכות', transliteration: 'Malkuth', gloss: 'Malkuth — Kingdom', script: 'hebrew', sourceCitation: 'Zohar (496 -> 19 -> root 10 Malkuth)', theme: 'sephirot' },
  // Greek (15 entries) — Total 37 entries matching qabalah.py CANON
  { canonicalId: 'grk-iesous', word: 'Ἰησοῦς', transliteration: 'Iesous', gloss: 'Iesous — Jesus', script: 'greek', sourceCitation: 'Sibylline Oracles 1.324–330 (888)', theme: 'classical_isopsephy' },
  { canonicalId: 'grk-christos', word: 'Χριστός', transliteration: 'Christos', gloss: 'Christos', script: 'greek', sourceCitation: 'Early Patristic Isopsephy (1480)', theme: 'classical_isopsephy' },
  { canonicalId: 'grk-logos', word: 'Λόγος', transliteration: 'Logos', gloss: 'Logos — the Word', script: 'greek', sourceCitation: 'Hellenistic Philosophy / Gospel of John (373)', theme: 'wisdom' },
  { canonicalId: 'grk-agape', word: 'ἀγάπη', transliteration: 'agape', gloss: 'agape — love', script: 'greek', sourceCitation: 'Classical Greek · equates with thelema (93)', theme: 'wisdom' },
  { canonicalId: 'grk-thelema', word: 'θέλημα', transliteration: 'thelema', gloss: 'thelema — will', script: 'greek', sourceCitation: 'Classical Greek · equates with agape (93)', theme: 'wisdom' },
  { canonicalId: 'grk-aletheia', word: 'ἀλήθεια', transliteration: 'aletheia', gloss: 'aletheia — truth', script: 'greek', sourceCitation: 'Classical Greek (64)', theme: 'wisdom' },
  { canonicalId: 'grk-sophia', word: 'σοφία', transliteration: 'Sophia', gloss: 'Sophia — wisdom', script: 'greek', sourceCitation: 'Hellenistic Tradition (781)', theme: 'wisdom' },
  { canonicalId: 'grk-psyche', word: 'ψυχή', transliteration: 'psyche', gloss: 'psyche — soul', script: 'greek', sourceCitation: 'Classical Greek (1708)', theme: 'wisdom' },
  { canonicalId: 'grk-kosmos', word: 'κόσμος', transliteration: 'kosmos', gloss: 'kosmos — order, world', script: 'greek', sourceCitation: 'Classical Greek (600)', theme: 'classical_isopsephy' },
  { canonicalId: 'grk-arche', word: 'ἀρχή', transliteration: 'arche', gloss: 'arche — beginning', script: 'greek', sourceCitation: 'Classical Greek (709)', theme: 'wisdom' },
  { canonicalId: 'grk-amen', word: 'Ἀμήν', transliteration: 'amen', gloss: 'amen', script: 'greek', sourceCitation: 'Septuagint / Early Christian isopsephy (99)', theme: 'classical_isopsephy' },
  { canonicalId: 'grk-abrasax', word: 'Ἀβρασάξ', transliteration: 'Abrasax', gloss: 'Abrasax', script: 'greek', sourceCitation: 'Basilidean / Greek Magical Papyri (365 = solar days)', theme: 'classical_isopsephy' },
  { canonicalId: 'grk-mithras', word: 'Μίθρας', transliteration: 'Mithras', gloss: 'Mithras', script: 'greek', sourceCitation: 'Hellenistic syncretism (360 with Μείθρας = 365)', theme: 'classical_isopsephy' },
  { canonicalId: 'grk-hagion', word: 'Ἅγιον', transliteration: 'hagion', gloss: 'hagion — holy', script: 'greek', sourceCitation: 'Classical Greek (134)', theme: 'wisdom' },
  { canonicalId: 'grk-666', word: 'χξϛ', transliteration: 'chi-xi-stigma', gloss: 'the number of the beast, as written', script: 'greek', sourceCitation: 'Revelation 13:18 (600 + 60 + 6 = 666)', theme: 'classical_isopsephy' },
];

/** Summed fresh at render time — zero pre-stored totals anywhere. */
export function computeCanonReadings(): CanonComputedEntry[] {
  return CANON_WORDS.map((entry) => ({
    ...entry,
    reading:
      entry.script === 'greek'
        ? scoreGreekIsopsephy(entry.word)
        : scoreHebrewGematria(entry.word, false),
  }));
}

export function findCanonEquivalences(value: number, excludeWord = ''): CanonComputedEntry[] {
  if (value <= 0) return [];
  const trimmed = excludeWord.trim();
  return computeCanonReadings().filter(
    (item) => item.reading.total === value && item.word !== trimmed
  );
}

export function findNearEquivalences(
  value: number,
  tolerance = 5,
  excludeWord = ''
): Array<CanonComputedEntry & { delta: number }> {
  if (value <= 0) return [];
  const trimmed = excludeWord.trim();
  return computeCanonReadings()
    .filter(
      (item) =>
        item.word !== trimmed &&
        item.reading.total !== value &&
        Math.abs(item.reading.total - value) <= tolerance
    )
    .map((item) => ({ ...item, delta: item.reading.total - value }))
    .sort((a, b) => Math.abs(a.delta) - Math.abs(b.delta));
}

/**
 * Preserved legacy /summary card Markdown output for compatibility export.
 */
export function renderLegacySummaryCardText(rawText: string): string {
  const trimmed = (rawText || '').trim();
  if (!trimmed) return 'Summary Card\n\nSend text to analyze.';

  const py = scoreLegacyPythagorean(trimmed);
  const he = scoreLegacyHebrewWraparound(trimmed);
  const ch = scoreLegacyChaldean(trimmed);
  const other = readingsForText(trimmed, { includeLegacyLatin: false });

  const lines: string[] = [
    '### Isopsephy Summary Card (Legacy Compat + Qabalah)',
    '```',
    '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
    `  ${trimmed}`,
    '── AT A GLANCE (LEGACY A-Z) ──────',
    `  Pythagorean · raw ${py.total} -> root ${py.legacyMasterRoot}`,
    `  Hebrew (W=A wrap) · raw ${he.total} -> root ${he.legacyMasterRoot}`,
    `  Chaldean · raw ${ch.total} -> root ${ch.legacyMasterRoot}`,
  ];
  if (other.length > 0) {
    lines.push('── CANONICAL READINGS ────────────');
    for (const r of other) {
      lines.push(`  ${r.system} · ${r.total} (Tree root ${r.treeRoot})`);
      if (r.skipped > 0) {
        lines.push(`    ${r.skipped} skipped character(s)`);
      }
    }
  }
  lines.push('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  lines.push('```');
  return lines.join('\n');
}
