/**
 * Living Tree of Life Catalog, Tradition Switcher, Deterministic Daily Game & Astronomical Ephemeris.
 * Pure TypeScript (zero Node built-ins) shared across UI and server.
 */

import {
  CanonComputedEntry,
  computeCanonReadings,
  findCanonEquivalences,
  HEBREW_SOFIT_ROWS,
  ReadingResult,
  readingsForText,
  treeDigitalRoot,
} from './hermesCipherEngine';

export type AttributionTraditionId = 'golden_dawn' | 'gra_ari' | 'thelemic_tzaddi';

export interface AttributionTraditionMeta {
  id: AttributionTraditionId;
  name: string;
  shortLabel: string;
  sourceCitation: string;
  summary: string;
}

export const ATTRIBUTION_TRADITIONS: ReadonlyArray<AttributionTraditionMeta> = [
  {
    id: 'golden_dawn',
    name: 'Golden Dawn / Kircher (Recovered Patch Baseline)',
    shortLabel: 'Golden Dawn · Kircher',
    sourceCitation: 'Athanasius Kircher Oedipus Aegyptiacus (1652) & Mathers Kabbalah Unveiled (1887)',
    summary:
      'Recovered gateway/qabalah.py baseline mapping the 22 Hebrew letters (Paths 11–32) to Major Arcana Tarot trumps and Kircher Tree edges.',
  },
  {
    id: 'gra_ari',
    name: 'Gra / Ari (Classical Lurianic Sefer Yetzirah)',
    shortLabel: 'Gra · Ari',
    sourceCitation: 'Vilna Gaon (Gra) & Isaac Luria (Ari) Commentary on Sefer Yetzirah',
    summary:
      'Classical Jewish Kabbalah arrangement: vertical Mother/Double channels follow three pillars; excludes modern Hermetic Tarot Trumps and notes Sefer Yetzirah planetary differences.',
  },
  {
    id: 'thelemic_tzaddi',
    name: 'Thelemic / Tzaddi Swap',
    shortLabel: 'Thelemic Swap',
    sourceCitation: 'Cited directly in gateway/qabalah.py §render_qabalah_section',
    summary:
      'Retains Kircher geometry while exchanging Path 15 (He · Aries) and Path 28 (Tzaddi · Aquarius) between The Star and The Emperor.',
  },
];

export type TreePillar = 'right_mercy' | 'middle_equilibrium' | 'left_severity';

export interface SephirahNode {
  number: number; // 1..10
  name: string;
  hebrew: string;
  meaning: string;
  sphere: string;
  pillar: TreePillar;
  x: number; // 0..1000 SVG stage
  y: number; // 0..1000 SVG stage
  divineNameHeb: string;
  colorTraditionNote: string;
  elementalAffinity: 'Aether' | 'Fire' | 'Water' | 'Air' | 'Earth';
}

export const SEPHIROT: ReadonlyArray<SephirahNode> = [
  {
    number: 1,
    name: 'Kether',
    hebrew: 'כתר',
    meaning: 'Crown',
    sphere: 'Primum Mobile',
    pillar: 'middle_equilibrium',
    x: 500,
    y: 95,
    divineNameHeb: 'אהיה',
    colorTraditionNote: 'Pure brilliance / Primum Mobile',
    elementalAffinity: 'Aether',
  },
  {
    number: 2,
    name: 'Chokmah',
    hebrew: 'חכמה',
    meaning: 'Wisdom',
    sphere: 'The Zodiac',
    pillar: 'right_mercy',
    x: 785,
    y: 225,
    divineNameHeb: 'יה',
    colorTraditionNote: 'Fixed stars / Mazloth',
    elementalAffinity: 'Fire',
  },
  {
    number: 3,
    name: 'Binah',
    hebrew: 'בינה',
    meaning: 'Understanding',
    sphere: 'Saturn',
    pillar: 'left_severity',
    x: 215,
    y: 225,
    divineNameHeb: 'יהוה אלהים',
    colorTraditionNote: 'Shabbathai / Great Sea',
    elementalAffinity: 'Water',
  },
  {
    number: 4,
    name: 'Chesed',
    hebrew: 'חסד',
    meaning: 'Mercy',
    sphere: 'Jupiter',
    pillar: 'right_mercy',
    x: 785,
    y: 415,
    divineNameHeb: 'אל',
    colorTraditionNote: 'Tzedeq / Benevolent Expansion',
    elementalAffinity: 'Water',
  },
  {
    number: 5,
    name: 'Geburah',
    hebrew: 'גבורה',
    meaning: 'Severity',
    sphere: 'Mars',
    pillar: 'left_severity',
    x: 215,
    y: 415,
    divineNameHeb: 'אלהים גבור',
    colorTraditionNote: 'Madim / Discernment & Form',
    elementalAffinity: 'Fire',
  },
  {
    number: 6,
    name: 'Tiphareth',
    hebrew: 'תפארת',
    meaning: 'Beauty',
    sphere: 'Sol',
    pillar: 'middle_equilibrium',
    x: 500,
    y: 525,
    divineNameHeb: 'יהוה אלוה ודעת',
    colorTraditionNote: 'Shemesh / Harmonizing Heart',
    elementalAffinity: 'Air',
  },
  {
    number: 7,
    name: 'Netzach',
    hebrew: 'נצח',
    meaning: 'Victory',
    sphere: 'Venus',
    pillar: 'right_mercy',
    x: 785,
    y: 665,
    divineNameHeb: 'יהוה צבאות',
    colorTraditionNote: 'Nogah / Endurance & Nature',
    elementalAffinity: 'Fire',
  },
  {
    number: 8,
    name: 'Hod',
    hebrew: 'הוד',
    meaning: 'Splendour',
    sphere: 'Mercury',
    pillar: 'left_severity',
    x: 215,
    y: 665,
    divineNameHeb: 'אלהים צבאות',
    colorTraditionNote: 'Kokab / Intellect & Language',
    elementalAffinity: 'Water',
  },
  {
    number: 9,
    name: 'Yesod',
    hebrew: 'יסוד',
    meaning: 'Foundation',
    sphere: 'Luna',
    pillar: 'middle_equilibrium',
    x: 500,
    y: 785,
    divineNameHeb: 'שדי אל חי',
    colorTraditionNote: 'Levanah / Lunar Tides & Memory',
    elementalAffinity: 'Air',
  },
  {
    number: 10,
    name: 'Malkuth',
    hebrew: 'מלכות',
    meaning: 'Kingdom',
    sphere: 'Earth',
    pillar: 'middle_equilibrium',
    x: 500,
    y: 920,
    divineNameHeb: 'אדני הארץ',
    colorTraditionNote: 'Olam Yesodoth / Elements of Earth',
    elementalAffinity: 'Earth',
  },
];

export type SeferYetzirahClass = 'mother' | 'double' | 'simple';

export interface TreePathEdge {
  number: number; // 11..32
  letter: string;
  letterName: string;
  fromSephirah: number;
  toSephirah: number;
  kind: SeferYetzirahClass;
  goldenDawnTrump: string;
  goldenDawnAttribution: string;
  graAriNote: string;
  thelemicSwapTrump?: string;
  thelemicSwapAttribution?: string;
}

/**
 * Exact 22 canonical paths of the Kircher Tree of Life preserving recovered qabalah.py attributes.
 */
export const TREE_PATHS: ReadonlyArray<TreePathEdge> = [
  { number: 11, letter: 'א', letterName: 'Aleph', fromSephirah: 1, toSephirah: 2, kind: 'mother', goldenDawnTrump: 'The Fool', goldenDawnAttribution: 'Air', graAriNote: 'Sefer Yetzirah Mother Letter: Ruach (Breath / Air)' },
  { number: 12, letter: 'ב', letterName: 'Beth', fromSephirah: 1, toSephirah: 3, kind: 'double', goldenDawnTrump: 'The Magician', goldenDawnAttribution: 'Mercury', graAriNote: 'Double Letter: Wisdom/Folly polarity; Moon/Mercury varies by manuscript' },
  { number: 13, letter: 'ג', letterName: 'Gimel', fromSephirah: 1, toSephirah: 6, kind: 'double', goldenDawnTrump: 'The High Priestess', goldenDawnAttribution: 'Luna', graAriNote: 'Middle Pillar Abyss bridge; Ari places vertical upper spine' },
  { number: 14, letter: 'ד', letterName: 'Daleth', fromSephirah: 2, toSephirah: 3, kind: 'double', goldenDawnTrump: 'The Empress', goldenDawnAttribution: 'Venus', graAriNote: 'Upper horizon connecting Wisdom (2) and Understanding (3)' },
  { number: 15, letter: 'ה', letterName: 'He', fromSephirah: 2, toSephirah: 6, kind: 'simple', goldenDawnTrump: 'The Emperor', goldenDawnAttribution: 'Aries', graAriNote: 'Simple Letter: Constitutes the vernal sense of Sight (Nisan)', thelemicSwapTrump: 'The Star (Tzaddi Swap)', thelemicSwapAttribution: 'Aquarius (Swapped)' },
  { number: 16, letter: 'ו', letterName: 'Vav', fromSephirah: 2, toSephirah: 4, kind: 'simple', goldenDawnTrump: 'The Hierophant', goldenDawnAttribution: 'Taurus', graAriNote: 'Simple Letter: Hearing (Iyar) along Right Pillar of Mercy' },
  { number: 17, letter: 'ז', letterName: 'Zayin', fromSephirah: 3, toSephirah: 6, kind: 'simple', goldenDawnTrump: 'The Lovers', goldenDawnAttribution: 'Gemini', graAriNote: 'Simple Letter: Smell (Sivan)' },
  { number: 18, letter: 'ח', letterName: 'Cheth', fromSephirah: 3, toSephirah: 5, kind: 'simple', goldenDawnTrump: 'The Chariot', goldenDawnAttribution: 'Cancer', graAriNote: 'Simple Letter: Speech (Tammuz) on Left Pillar of Severity' },
  { number: 19, letter: 'ט', letterName: 'Teth', fromSephirah: 4, toSephirah: 5, kind: 'simple', goldenDawnTrump: 'Strength', goldenDawnAttribution: 'Leo', graAriNote: 'Horizontal balance between Mercy (4) and Severity (5)' },
  { number: 20, letter: 'י', letterName: 'Yod', fromSephirah: 4, toSephirah: 6, kind: 'simple', goldenDawnTrump: 'The Hermit', goldenDawnAttribution: 'Virgo', graAriNote: 'Simple Letter: Action/Touch (Elul)' },
  { number: 21, letter: 'כ', letterName: 'Kaph', fromSephirah: 4, toSephirah: 7, kind: 'double', goldenDawnTrump: 'Wheel of Fortune', goldenDawnAttribution: 'Jupiter', graAriNote: 'Double Letter on Mercy Pillar: Life & Fortune' },
  { number: 22, letter: 'ל', letterName: 'Lamed', fromSephirah: 5, toSephirah: 6, kind: 'simple', goldenDawnTrump: 'Justice', goldenDawnAttribution: 'Libra', graAriNote: 'Simple Letter: Equilibrium / Tishrei' },
  { number: 23, letter: 'מ', letterName: 'Mem', fromSephirah: 5, toSephirah: 8, kind: 'mother', goldenDawnTrump: 'The Hanged Man', goldenDawnAttribution: 'Water', graAriNote: 'Sefer Yetzirah Mother Letter: Mayim (Water)' },
  { number: 24, letter: 'נ', letterName: 'Nun', fromSephirah: 6, toSephirah: 7, kind: 'simple', goldenDawnTrump: 'Death', goldenDawnAttribution: 'Scorpio', graAriNote: 'Simple Letter: Motion/Transformation (Cheshvan)' },
  { number: 25, letter: 'ס', letterName: 'Samekh', fromSephirah: 6, toSephirah: 9, kind: 'simple', goldenDawnTrump: 'Temperance', goldenDawnAttribution: 'Sagittarius', graAriNote: 'Lower Middle Pillar axis between Sol (6) and Luna (9)' },
  { number: 26, letter: 'ע', letterName: 'Ayin', fromSephirah: 6, toSephirah: 8, kind: 'simple', goldenDawnTrump: 'The Devil', goldenDawnAttribution: 'Capricorn', graAriNote: 'Simple Letter: Binding form (Tevet)' },
  { number: 27, letter: 'פ', letterName: 'Pe', fromSephirah: 7, toSephirah: 8, kind: 'double', goldenDawnTrump: 'The Tower', goldenDawnAttribution: 'Mars', graAriNote: 'Double Letter horizon between Desire (7) and Intellect (8)' },
  { number: 28, letter: 'צ', letterName: 'Tzaddi', fromSephirah: 7, toSephirah: 9, kind: 'simple', goldenDawnTrump: 'The Star', goldenDawnAttribution: 'Aquarius', graAriNote: 'Simple Letter: Meditation (Shevat)', thelemicSwapTrump: 'The Emperor (He Swap)', thelemicSwapAttribution: 'Aries (Swapped)' },
  { number: 29, letter: 'ק', letterName: 'Qoph', fromSephirah: 7, toSephirah: 10, kind: 'simple', goldenDawnTrump: 'The Moon', goldenDawnAttribution: 'Pisces', graAriNote: 'Simple Letter: Sleep/Tidal threshold (Adar)' },
  { number: 30, letter: 'ר', letterName: 'Resh', fromSephirah: 8, toSephirah: 9, kind: 'double', goldenDawnTrump: 'The Sun', goldenDawnAttribution: 'Sol', graAriNote: 'Double Letter on Left-to-Middle astral bridge' },
  { number: 31, letter: 'ש', letterName: 'Shin', fromSephirah: 8, toSephirah: 10, kind: 'mother', goldenDawnTrump: 'Judgement', goldenDawnAttribution: 'Fire', graAriNote: 'Sefer Yetzirah Mother Letter: Esh (Fire)' },
  { number: 32, letter: 'ת', letterName: 'Tav', fromSephirah: 9, toSephirah: 10, kind: 'double', goldenDawnTrump: 'The World', goldenDawnAttribution: 'Saturn', graAriNote: 'Double Letter closing the Middle Pillar down into Malkuth (10)' },
];

const PATH_BY_LETTER_MAP = new Map<string, TreePathEdge>();
for (const path of TREE_PATHS) {
  PATH_BY_LETTER_MAP.set(path.letter, path);
}
for (const [sofit, base] of HEBREW_SOFIT_ROWS) {
  const basePath = PATH_BY_LETTER_MAP.get(base);
  if (basePath) PATH_BY_LETTER_MAP.set(sofit, basePath);
}

export function resolveSephirahForValue(value: number): SephirahNode | null {
  if (value <= 0) return null;
  const root = value >= 1 && value <= 10 ? value : treeDigitalRoot(value);
  return SEPHIROT[root - 1] ?? null;
}

export function resolvePathForHebrewChar(ch: string): TreePathEdge | null {
  return PATH_BY_LETTER_MAP.get(ch) ?? null;
}

export function resolvePathPresentation(
  path: TreePathEdge,
  tradition: AttributionTraditionId
): { trumpLabel: string; attributionLabel: string; note: string } {
  if (tradition === 'gra_ari') {
    return {
      trumpLabel: `Non-Tarot (Sefer Yetzirah ${path.kind})`,
      attributionLabel: path.kind === 'mother' ? path.goldenDawnAttribution : `${path.letterName} (${path.kind})`,
      note: path.graAriNote,
    };
  }
  if (tradition === 'thelemic_tzaddi' && path.thelemicSwapTrump) {
    return {
      trumpLabel: path.thelemicSwapTrump,
      attributionLabel: path.thelemicSwapAttribution ?? path.goldenDawnAttribution,
      note: 'Liber AL Tzaddi Swap active on Path 15/28.',
    };
  }
  return {
    trumpLabel: path.goldenDawnTrump,
    attributionLabel: path.goldenDawnAttribution,
    note: `Golden Dawn / Kircher Path ${path.number} (${path.letterName})`,
  };
}

export function getSephirahNeighbors(sephirahNumber: number): {
  paths: TreePathEdge[];
  connectedSephirot: SephirahNode[];
} {
  const paths = TREE_PATHS.filter(
    (p) => p.fromSephirah === sephirahNumber || p.toSephirah === sephirahNumber
  );
  const neighborIds = new Set<number>();
  for (const p of paths) {
    neighborIds.add(p.fromSephirah === sephirahNumber ? p.toSephirah : p.fromSephirah);
  }
  const connectedSephirot = SEPHIROT.filter((s) => neighborIds.has(s.number));
  return { paths, connectedSephirot };
}

// ---------------------------------------------------------------------------
// DETERMINISTIC DAILY CHALLENGE ENGINE (Parity with Python `date.toordinal()`)
// ---------------------------------------------------------------------------

export interface DailyChallengeSummary {
  utcDate: string;
  dateOrdinal: number;
  targetNumber: number;
  targetTreeRoot: number;
  targetSephirahName: string;
  reachableCanonCount: number;
  // Kept server-only during verification or revealed only via explicit hint/reveal
  hintTier1Sephirah: string;
  hintTier2Script: string;
  hintTier3InitialGlyph: string;
  canonicalSeedWordCount: number;
}

export interface DailyGuessEvaluation {
  utcDate: string;
  targetNumber: number;
  guess: string;
  hit: boolean;
  hittingSystems: string[];
  closestSystem: string | null;
  closestTotal: number | null;
  distance: number | null;
  matchedEquivalences: Array<{ word: string; transliteration: string; gloss: string; system: string }>;
  readings: ReadingResult[];
}

/** Matches Python datetime.date.toordinal() for Gregorian calendar dates YYYY-MM-DD */
export function computeGregorianOrdinal(utcDateStr: string): number {
  const [yStr, mStr, dStr] = utcDateStr.split('-');
  const y = Number(yStr) || 2026;
  const m = Number(mStr) || 1;
  const d = Number(dStr) || 1;
  const epochDays = Math.floor(Date.UTC(y, m - 1, d) / 86_400_000);
  // 1970-01-01 has Python ordinal 719163
  return 719163 + epochDays;
}

export function getUtcDateString(date = new Date()): string {
  return date.toISOString().slice(0, 10);
}

function sortedDistinctCanonPool(): Array<{ total: number; entries: CanonComputedEntry[] }> {
  const map = new Map<number, CanonComputedEntry[]>();
  for (const entry of computeCanonReadings()) {
    const arr = map.get(entry.reading.total) ?? [];
    arr.push(entry);
    map.set(entry.reading.total, arr);
  }
  return Array.from(map.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([total, entries]) => ({ total, entries }));
}

export function getDailyChallengeForDate(utcDateStr = getUtcDateString()): DailyChallengeSummary {
  const ordinal = computeGregorianOrdinal(utcDateStr);
  const pool = sortedDistinctCanonPool();
  const picked = pool[ordinal % pool.length];
  const primaryWord = picked.entries[0];
  const seph = resolveSephirahForValue(picked.total);

  return {
    utcDate: utcDateStr,
    dateOrdinal: ordinal,
    targetNumber: picked.total,
    targetTreeRoot: seph?.number ?? treeDigitalRoot(picked.total),
    targetSephirahName: seph ? `${seph.number} ${seph.name} (${seph.meaning})` : 'None',
    reachableCanonCount: picked.entries.length,
    hintTier1Sephirah: seph
      ? `The target reduces to Tree root ${seph.number} — ${seph.name} (${seph.sphere}).`
      : 'Reduces directly to its numeric root.',
    hintTier2Script: `A canonical ${primaryWord.script === 'greek' ? 'Greek Isopsephy' : 'Hebrew Gematria'} concept reaches ${picked.total} (${picked.entries.map((e) => e.theme.replace('_', ' ')).join(' / ')}).`,
    hintTier3InitialGlyph: `Canon anchor begins with "${Array.from(primaryWord.word)[0]}" (${primaryWord.transliteration.slice(0, 2)}…).`,
    canonicalSeedWordCount: pool.length,
  };
}

export function evaluateDailyChallengeGuess(
  guess: string,
  utcDateStr = getUtcDateString(),
  customTarget?: number
): DailyGuessEvaluation {
  const challenge = getDailyChallengeForDate(utcDateStr);
  const targetNumber = customTarget && customTarget > 0 ? customTarget : challenge.targetNumber;
  const reads = readingsForText(guess, { includeLegacyLatin: false });
  const hits = reads.filter((r) => r.total === targetNumber);
  const closest =
    reads.length > 0
      ? reads.reduce((best, cur) =>
          Math.abs(cur.total - targetNumber) < Math.abs(best.total - targetNumber) ? cur : best
        )
      : null;

  const equivs = findCanonEquivalences(targetNumber, guess.trim());

  return {
    utcDate: utcDateStr,
    targetNumber,
    guess,
    hit: hits.length > 0,
    hittingSystems: hits.map((h) => h.system),
    closestSystem: closest ? closest.system : null,
    closestTotal: closest ? closest.total : null,
    distance: closest ? Math.abs(closest.total - targetNumber) : null,
    matchedEquivalences: hits.length
      ? equivs.map((e) => ({
          word: e.word,
          transliteration: e.transliteration,
          gloss: e.gloss,
          system: e.reading.system,
        }))
      : [],
    readings: reads,
  };
}

// ---------------------------------------------------------------------------
// PURE ASTRONOMICAL EPHEMERIS CALCULATOR (OFFLINE-CAPABLE CALCULATED LAYER)
// ---------------------------------------------------------------------------

export interface AstronomicalEphemeris {
  calculatedAtUtc: string;
  lunarAgeDays: number;
  lunarIlluminationPct: number;
  lunarPhaseName: string;
  solarAltitudeDeg: number;
  isAstronomicalDay: boolean;
  algorithmNote: string;
}

/**
 * Pure deterministic lunar synodic phase (Meeus epoch J2000 new moon) + solar elevation approximation.
 * Works identically offline or when network feeds fail.
 */
export function computeAstronomicalEphemeris(
  now = new Date(),
  latitudeDeg = 51.5074,
  longitudeDeg = -0.1278
): AstronomicalEphemeris {
  const SYNODIC_MONTH = 29.53058867;
  // Known New Moon reference: 2000-01-06T18:14:00Z
  const refNewMoonMs = Date.UTC(2000, 0, 6, 18, 14, 0);
  const daysSince = (now.getTime() - refNewMoonMs) / 86_400_000;
  const lunarAgeDays = Number(
    ((((daysSince % SYNODIC_MONTH) + SYNODIC_MONTH) % SYNODIC_MONTH)).toFixed(2)
  );
  const phaseAngle = (lunarAgeDays / SYNODIC_MONTH) * 2 * Math.PI;
  const illumination = (1 - Math.cos(phaseAngle)) / 2;
  const lunarIlluminationPct = Number((illumination * 100).toFixed(1));

  let lunarPhaseName = 'New Moon';
  if (lunarAgeDays < 1.85 || lunarAgeDays >= 27.68) lunarPhaseName = 'New Moon';
  else if (lunarAgeDays < 5.54) lunarPhaseName = 'Waxing Crescent';
  else if (lunarAgeDays < 9.23) lunarPhaseName = 'First Quarter';
  else if (lunarAgeDays < 12.92) lunarPhaseName = 'Waxing Gibbous';
  else if (lunarAgeDays < 16.61) lunarPhaseName = 'Full Moon';
  else if (lunarAgeDays < 20.3) lunarPhaseName = 'Waning Gibbous';
  else if (lunarAgeDays < 23.99) lunarPhaseName = 'Last Quarter';
  else lunarPhaseName = 'Waning Crescent';

  // Approximate solar declination and hour angle for horizon altitude
  const startOfYear = Date.UTC(now.getUTCFullYear(), 0, 1);
  const dayOfYear = Math.floor((now.getTime() - startOfYear) / 86_400_000) + 1;
  const declRad = (23.44 * Math.PI / 180) * Math.sin(((2 * Math.PI) / 365) * (dayOfYear - 81));
  const latRad = (latitudeDeg * Math.PI) / 180;
  const utcHours = now.getUTCHours() + now.getUTCMinutes() / 60;
  const solarHourDeg = (utcHours - 12) * 15 + longitudeDeg;
  const hourAngleRad = (solarHourDeg * Math.PI) / 180;
  const sinAlt =
    Math.sin(latRad) * Math.sin(declRad) +
    Math.cos(latRad) * Math.cos(declRad) * Math.cos(hourAngleRad);
  const solarAltitudeDeg = Number(((Math.asin(Math.max(-1, Math.min(1, sinAlt))) * 180) / Math.PI).toFixed(1));

  return {
    calculatedAtUtc: now.toISOString(),
    lunarAgeDays,
    lunarIlluminationPct,
    lunarPhaseName,
    solarAltitudeDeg,
    isAstronomicalDay: solarAltitudeDeg > -0.833,
    algorithmNote: 'Deterministic J2000 synodic lunar cycle + spherical solar elevation (offline-capable)',
  };
}
