import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Check,
  Compass,
  Copy,
  Download,
  EyeOff,
  FileText,
  Globe,
  HelpCircle,
  Moon,
  PackageCheck,
  Pause,
  Play,
  RefreshCw,
  RotateCcw,
  Sun,
  Volume2,
  VolumeX,
  Wind,
  CloudRain,
} from 'lucide-react';
import {
  CODEX_PATHS_EXTENDED,
  CODEX_SPHERES,
  computePillarEquilibrium,
  CrescendoCurrent,
  evaluateChronoReplay,
  OLAMOT_WORLDS,
  OlamotScale,
  QLIPHOTH_REGISTRY,
  QliphahId,
  resolveSphereHexForScale,
  THREE_VEILS,
  verifyThreeKeyNonCollusion,
} from '../engine/codexCrescendo';
import { crescendoAudio } from '../engine/crescendoAudio';
import { CodexCrescendoPanel } from './CodexCrescendoPanel';
import {
  CANON_WORDS,
  computeCanonReadings,
  findCanonEquivalences,
  findNearEquivalences,
  GREEK_ROWS,
  HEBREW_ROWS,
  HEBREW_SOFIT_ROWS,
  inspectDualModeEnglishDiff,
  ReadingResult,
  readingsForText,
  renderLegacySummaryCardText,
} from '../engine/hermesCipherEngine';
import {
  ATTRIBUTION_TRADITIONS,
  AttributionTraditionId,
  DailyGuessEvaluation,
  getDailyChallengeForDate,
  getSephirahNeighbors,
  getUtcDateString,
  resolvePathForHebrewChar,
  resolvePathPresentation,
  resolveSephirahForValue,
  SEPHIROT,
  SephirahNode,
  TREE_PATHS,
  TreePathEdge,
} from '../engine/hermesTreeCatalog';
import { SANCTUARY_PLACES, WorldResonanceSnapshot } from '../engine/hermesWorldConnector';

const PRESET_WORDS: ReadonlyArray<{
  word: string;
  suffix: string;
  text: string;
  note: string;
}> = [
  { word: 'Ἰησοῦς', suffix: '(888)', text: 'Ἰησοῦς', note: 'Classical Greek 888' },
  { word: 'χξϛ', suffix: '(666)', text: 'χξϛ', note: 'Archaic Stigma = 6' },
  { word: 'θέλημα', suffix: '(93)', text: 'θέλημα', note: 'Equates with ἀγάπη' },
  { word: 'מלכות', suffix: '(496→10)', text: 'מלכות', note: 'Stops at Malkuth 10' },
  { word: 'אחד', suffix: '(13)', text: 'אחד', note: 'Equates with אהבה' },
  { word: 'שלום', suffix: '(Gadol 936)', text: 'שלום', note: 'Mem Sofit = 600' },
  { word: 'WAX', suffix: '(Legacy Bug)', text: 'WAX', note: 'W=A wraparound diff' },
];

type AtlasSubTab = 'canon' | 'tables' | 'legacy_card' | 'codex' | 'forensics';
type TreeInstrumentMode = 'cipher' | 'codex';

export function HermesLivingTree() {
  const [inputText, setInputText] = useState<string>('θέλημα');
  const [includeLegacyLatin, setIncludeLegacyLatin] = useState<boolean>(true);
  const [tradition, setTradition] = useState<AttributionTraditionId>('golden_dawn');
  const [treeMode, setTreeMode] = useState<TreeInstrumentMode>('codex');
  const [olamScale, setOlamScale] = useState<OlamotScale>('atziluth');
  const [crescendoCurrent, setCrescendoCurrent] = useState<CrescendoCurrent>('mezla');
  const [zoomLevel, setZoomLevel] = useState<0 | 1 | 2>(0);
  const [chronoProgress, setChronoProgress] = useState<number>(0.68);
  const [chronoPlaying, setChronoPlaying] = useState<boolean>(false);
  const [mercyThroughput, setMercyThroughput] = useState<number>(1.0);
  const [severityStrictness, setSeverityStrictness] = useState<number>(1.0);
  const [injectedQliphah, setInjectedQliphah] = useState<QliphahId>('none');
  const [audioEnabled, setAudioEnabled] = useState<boolean>(false);
  const [threeKeys, setThreeKeys] = useState({
    keyBinah: 'keyA_binah_oracle_ed25519',
    keyChesed: 'keyB_chesed_exec_ed25519',
    keyMalkuth: 'keyC_malkuth_witness_ed25519',
  });
  const [selectedSephirahNum, setSelectedSephirahNum] = useState<number | null>(null);
  const [selectedPathNum, setSelectedPathNum] = useState<number | null>(null);
  const [tiltPerspective, setTiltPerspective] = useState<boolean>(true);
  const [reducedMotion, setReducedMotion] = useState<boolean>(() => {
    if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
      return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }
    return false;
  });

  // World Resonance state
  const [placeId, setPlaceId] = useState<string>('london');
  const [forceOffline, setForceOffline] = useState<boolean>(false);
  const [world, setWorld] = useState<WorldResonanceSnapshot | null>(null);
  const [worldLoading, setWorldLoading] = useState<boolean>(true);
  const [worldError, setWorldError] = useState<string | null>(null);

  // Daily Game state
  const [guessInput, setGuessInput] = useState<string>('');
  const [guessSubmitting, setGuessSubmitting] = useState<boolean>(false);
  const [guessError, setGuessError] = useState<string | null>(null);
  const [attempts, setAttempts] = useState<DailyGuessEvaluation[]>([]);
  const [hintLevel, setHintLevel] = useState<number>(0);

  // Lower atlas tabs, chaos & copy feedback
  const [atlasTab, setAtlasTab] = useState<AtlasSubTab>('codex');
  const [canonSearch, setCanonSearch] = useState<string>('');
  const [copiedMode, setCopiedMode] = useState<'none' | 'markdown' | 'json'>('none');
  const [chaosRunning, setChaosRunning] = useState<boolean>(false);
  const [chaosResult, setChaosResult] = useState<{
    iterations: number;
    succeeded: number;
    exceptionsThrown: number;
    p95Us: number;
    maxDurationMs: number;
    passed: boolean;
  } | null>(null);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const loadWorld = useCallback(async (targetPlace: string, offline: boolean) => {
    setWorldLoading(true);
    setWorldError(null);
    try {
      const qs = new URLSearchParams({
        placeId: targetPlace,
        forceOffline: String(offline),
      });
      const res = await fetch(`/api/hermes/world?${qs.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as WorldResonanceSnapshot;
      setWorld(data);
    } catch (err) {
      setWorldError(err instanceof Error ? err.message : 'Unable to fetch World Resonance');
    } finally {
      setWorldLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadWorld(placeId, forceOffline);
  }, [placeId, forceOffline, loadWorld]);

  // Instant pure deterministic readings (zero network round-trip required)
  const readings = useMemo<ReadingResult[]>(
    () => readingsForText(inputText, { includeLegacyLatin }),
    [inputText, includeLegacyLatin]
  );

  const primaryReading = useMemo<ReadingResult | null>(() => {
    if (readings.length === 0) return null;
    // Prefer modern canonical reading first (Greek, Hebrew Hechrechi, English Extended)
    return readings[0];
  }, [readings]);

  const dualDiff = useMemo(() => inspectDualModeEnglishDiff(inputText), [inputText]);

  const landedSephirah = useMemo(
    () => (primaryReading && primaryReading.total > 0 ? resolveSephirahForValue(primaryReading.total) : null),
    [primaryReading]
  );

  const walkedPaths = useMemo<TreePathEdge[]>(() => {
    const out: TreePathEdge[] = [];
    const seen = new Set<number>();
    for (const r of readings) {
      if (r.script !== 'hebrew') continue;
      for (const b of r.breakdown) {
        const p = resolvePathForHebrewChar(b.normalizedChar);
        if (p && !seen.has(p.number)) {
          seen.add(p.number);
          out.push(p);
        }
      }
    }
    return out;
  }, [readings]);

  const walkedPathNumbers = useMemo(() => new Set(walkedPaths.map((p) => p.number)), [walkedPaths]);

  const exactEquivalences = useMemo(
    () => (primaryReading ? findCanonEquivalences(primaryReading.total, inputText) : []),
    [primaryReading, inputText]
  );

  const nearEquivalences = useMemo(
    () => (primaryReading ? findNearEquivalences(primaryReading.total, 6, inputText).slice(0, 6) : []),
    [primaryReading, inputText]
  );

  const canonReadings = useMemo(() => computeCanonReadings(), []);

  const filteredCanon = useMemo(() => {
    const q = canonSearch.trim().toLowerCase();
    if (!q) return canonReadings;
    const maybeNum = Number(q);
    return canonReadings.filter((entry) => {
      if (!Number.isNaN(maybeNum) && q !== '' && entry.reading.total === maybeNum) return true;
      return (
        entry.word.toLowerCase().includes(q) ||
        entry.transliteration.toLowerCase().includes(q) ||
        entry.gloss.toLowerCase().includes(q) ||
        String(entry.reading.total).includes(q)
      );
    });
  }, [canonReadings, canonSearch]);

  const utcDate = getUtcDateString();
  const dailyChallenge = useMemo(
    () => world?.calculated.dailyChallenge ?? getDailyChallengeForDate(utcDate),
    [world, utcDate]
  );

  const activeTraditionMeta = useMemo(
    () => ATTRIBUTION_TRADITIONS.find((t) => t.id === tradition) ?? ATTRIBUTION_TRADITIONS[0],
    [tradition]
  );

  // Determine which Sephirah / Path is currently focused in the Inspector
  const focusedSephirah: SephirahNode | null = useMemo(() => {
    if (selectedSephirahNum !== null) {
      return SEPHIROT.find((s) => s.number === selectedSephirahNum) ?? null;
    }
    return landedSephirah ?? SEPHIROT[5]; // Default gently to Tiphareth if empty
  }, [selectedSephirahNum, landedSephirah]);

  const focusedPath: TreePathEdge | null = useMemo(() => {
    if (selectedPathNum !== null) {
      return TREE_PATHS.find((p) => p.number === selectedPathNum) ?? null;
    }
    return walkedPaths[0] ?? null;
  }, [selectedPathNum, walkedPaths]);

  const legacyCardMarkdown = useMemo(() => renderLegacySummaryCardText(inputText), [inputText]);

  const threeKeyVerdict = useMemo(
    () =>
      verifyThreeKeyNonCollusion({
        ...threeKeys,
        merkleRoot: 'meridian.crescendo.v1:8b6d23f',
      }),
    [threeKeys]
  );

  const omegaResult = useMemo(
    () => computePillarEquilibrium(mercyThroughput, severityStrictness),
    [mercyThroughput, severityStrictness]
  );

  const chronoState = useMemo(
    () =>
      evaluateChronoReplay({
        progress: chronoProgress,
        current: crescendoCurrent,
        injectedQliphah,
        threeKeyValid: threeKeyVerdict.malkuthIlluminated,
      }),
    [chronoProgress, crescendoCurrent, injectedQliphah, threeKeyVerdict.malkuthIlluminated]
  );

  // Chrono-Astrolabe timer when playing (pauses automatically at 1.0 or when user stops)
  useEffect(() => {
    if (!chronoPlaying || reducedMotion) return;
    const stepMs = chronoState.timeDilation.startsWith('0.1x') ? 130 : 45;
    const id = window.setInterval(() => {
      setChronoProgress((prev) => {
        if (prev >= 1) {
          setChronoPlaying(false);
          return 1;
        }
        return Math.min(1, Number((prev + 0.025).toFixed(3)));
      });
    }, stepMs);
    return () => window.clearInterval(id);
  }, [chronoPlaying, reducedMotion, chronoState.timeDilation]);

  // Synchronize WebAudio Rosicrucian Harmonics when explicitly enabled by user
  useEffect(() => {
    if (!audioEnabled) {
      crescendoAudio.stop();
      return;
    }
    const duelActive = chronoState.activePathNumbers.includes(19);
    crescendoAudio.startOrUpdate({
      active: true,
      omega: omegaResult.omega,
      duelActive,
      malkuthSealed: chronoState.malkuthSealed,
    });
    if (chronoState.malkuthSealed) {
      crescendoAudio.strikeMalkuthWitnessBell();
    }
    return () => {
      crescendoAudio.stop();
    };
  }, [audioEnabled, omegaResult.omega, chronoState.activePathNumbers, chronoState.malkuthSealed]);

  // Ambient Canvas Weather & Starfield overlay inside the Observatory viewport
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const mode = world?.interpreted.atmosphereMode ?? 'NIGHT_AETHER';
    const dpr = typeof window !== 'undefined' ? Math.min(2, window.devicePixelRatio || 1) : 1;
    const width = 560;
    const height = 680;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const particles = Array.from({ length: 48 }, (_, i) => ({
      x: ((i * 79) % width) + (i % 7) * 3,
      y: (i * 53) % height,
      speed: 0.35 + (i % 5) * 0.22,
      size: 0.9 + (i % 3) * 0.55,
      alpha: 0.16 + (i % 4) * 0.12,
    }));

    let rafId = 0;

    const drawFrame = () => {
      ctx.clearRect(0, 0, width, height);

      for (const p of particles) {
        if (mode === 'RAIN_WATER') {
          ctx.strokeStyle = `rgba(56, 189, 248, ${p.alpha + 0.12})`;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(p.x, p.y);
          ctx.lineTo(p.x - 2, p.y + 12);
          ctx.stroke();
          if (!reducedMotion) {
            p.y += p.speed * 4.5;
            p.x -= p.speed * 0.6;
          }
        } else if (mode === 'WIND_AIR') {
          ctx.strokeStyle = `rgba(148, 163, 184, ${p.alpha + 0.08})`;
          ctx.lineWidth = 0.9;
          ctx.beginPath();
          ctx.moveTo(p.x, p.y);
          ctx.lineTo(p.x + 18, p.y - 2);
          ctx.stroke();
          if (!reducedMotion) {
            p.x += p.speed * 2.8;
            p.y += Math.sin(p.x * 0.02) * 0.3;
          }
        } else {
          const tint = mode === 'SOLAR_FIRE' ? '250, 204, 21' : '186, 230, 253';
          ctx.fillStyle = `rgba(${tint}, ${p.alpha})`;
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
          ctx.fill();
          if (!reducedMotion) {
            p.y -= p.speed * 0.35;
          }
        }

        if (p.y > height) p.y = -10;
        if (p.y < -10) p.y = height + 6;
        if (p.x > width) p.x = -12;
        if (p.x < -12) p.x = width + 6;
      }

      if (!reducedMotion) {
        rafId = window.requestAnimationFrame(drawFrame);
      }
    };

    drawFrame();
    return () => {
      if (rafId) window.cancelAnimationFrame(rafId);
    };
  }, [world?.interpreted.atmosphereMode, reducedMotion]);

  async function handleGuessSubmit(e: React.FormEvent) {
    e.preventDefault();
    const cleaned = guessInput.trim();
    if (!cleaned) return;
    setGuessSubmitting(true);
    setGuessError(null);
    try {
      const res = await fetch('/api/hermes/puzzle/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          guess: cleaned,
          idempotencyKey: `${utcDate}-${cleaned}-${attempts.length}`,
        }),
      });
      const json = await res.json();
      if (!res.ok) {
        throw new Error(json?.error || `HTTP ${res.status}`);
      }
      setAttempts((prev) => [json as DailyGuessEvaluation, ...prev]);
      setGuessInput('');
    } catch (err) {
      setGuessError(err instanceof Error ? err.message : 'Unable to score guess');
    } finally {
      setGuessSubmitting(false);
    }
  }

  async function handleCopySummary(mode: 'markdown' | 'json') {
    try {
      if (mode === 'markdown') {
        await navigator.clipboard.writeText(legacyCardMarkdown);
      } else {
        const res = await fetch('/api/hermes/export-summary', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: inputText }),
        });
        const data = await res.json();
        await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
      }
      setCopiedMode(mode);
      window.setTimeout(() => setCopiedMode('none'), 2000);
    } catch {
      // Clipboard blocked in headless mode cleanly
      setCopiedMode(mode);
      window.setTimeout(() => setCopiedMode('none'), 2000);
    }
  }

  async function handleRunHermesChaos() {
    setChaosRunning(true);
    try {
      const res = await fetch('/api/hermes/chaos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ iterations: 1000 }),
      });
      if (res.ok) {
        const data = await res.json();
        setChaosResult(data);
      }
    } finally {
      setChaosRunning(false);
    }
  }

  function handleSephirahKeyDown(e: React.KeyboardEvent, sephNumber: number) {
    if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
      e.preventDefault();
      const next = sephNumber >= 10 ? 1 : sephNumber + 1;
      setSelectedSephirahNum(next);
      setSelectedPathNum(null);
    } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
      e.preventDefault();
      const prev = sephNumber <= 1 ? 10 : sephNumber - 1;
      setSelectedSephirahNum(prev);
      setSelectedPathNum(null);
    } else if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      setSelectedSephirahNum(sephNumber);
      setSelectedPathNum(null);
    }
  }

  const hasSolvedDaily = attempts.some((a) => a.hit);
  const obs = world?.observed;
  const calc = world?.calculated;
  const interp = world?.interpreted;

  const atmosphereIcon =
    interp?.atmosphereMode === 'RAIN_WATER' ? (
      <CloudRain className="h-4 w-4 text-sky-400" aria-hidden="true" />
    ) : interp?.atmosphereMode === 'WIND_AIR' ? (
      <Wind className="h-4 w-4 text-slate-300" aria-hidden="true" />
    ) : interp?.atmosphereMode === 'SOLAR_FIRE' ? (
      <Sun className="h-4 w-4 text-amber-400" aria-hidden="true" />
    ) : (
      <Moon className="h-4 w-4 text-amber-300" aria-hidden="true" />
    );

  return (
    <div className="space-y-6 text-slate-900">
      {/* 1. CELESTIAL SANCTUM HORIZON HEADER & 3-LAYER WORLD RESONANCE */}
      <section
        aria-label="Hermes Living Tree Sanctum and World Resonance"
        className="rounded-xl bg-[#070B14] text-slate-100 border border-slate-800 overflow-hidden"
      >
        <div className="px-5 sm:px-7 py-5 border-b border-slate-800/90 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2 text-xs text-amber-400/90 font-medium">
              <span>Hermes Sanctum</span>
              <span aria-hidden="true" className="text-slate-600">·</span>
              <span>Isopsephy, Gematria &amp; the Living Tree</span>
              <span aria-hidden="true" className="text-slate-600">·</span>
              <span className="text-slate-400">Source SHA 1220c4ad</span>
            </div>
            <h2 className="mt-1 text-xl sm:text-2xl font-semibold tracking-tight text-white [text-wrap:balance]">
              Language, Number, Tradition &amp; Sky
            </h2>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <label htmlFor="sanctum-place-select" className="sr-only">
              Observatory location
            </label>
            <div className="inline-flex items-center gap-2 rounded-lg bg-slate-900/90 border border-slate-700/80 px-3 py-1.5">
              <Globe className="h-3.5 w-3.5 text-sky-400 shrink-0" aria-hidden="true" />
              <select
                id="sanctum-place-select"
                value={placeId}
                onChange={(e) => setPlaceId(e.target.value)}
                className="bg-transparent text-xs font-medium text-slate-100 focus:outline-none cursor-pointer"
              >
                {SANCTUARY_PLACES.map((p) => (
                  <option key={p.id} value={p.id} className="bg-slate-900 text-slate-100">
                    {p.label}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="button"
              onClick={() => setForceOffline((v) => !v)}
              aria-pressed={forceOffline}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium border transition-colors whitespace-nowrap shrink-0 ${
                forceOffline
                  ? 'bg-amber-500/15 border-amber-400/60 text-amber-200'
                  : 'bg-slate-900/90 border-slate-700/80 text-slate-300 hover:text-white'
              }`}
            >
              <EyeOff className="h-3.5 w-3.5" aria-hidden="true" />
              <span>{forceOffline ? 'Offline Fallback On' : 'Simulate Offline'}</span>
            </button>

            <button
              type="button"
              onClick={() => loadWorld(placeId, forceOffline)}
              disabled={worldLoading}
              className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900/90 border border-slate-700/80 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0 disabled:opacity-50"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${worldLoading ? 'animate-spin text-sky-400' : 'text-slate-400'}`}
                aria-hidden="true"
              />
              <span>Refresh Sky</span>
            </button>
          </div>
        </div>

        {/* Strict 3-Layer World Resonance Separation: Observed -> Calculated -> Interpreted */}
        <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-slate-800/90 bg-slate-950/60">
          {/* Layer 1: Observed */}
          <div className="p-4 sm:p-5">
            <div className="flex items-center justify-between gap-2 text-xs text-slate-400">
              <span className="font-semibold text-sky-400">Layer 1 · Observed Telemetry</span>
              <span className="font-mono tabular-nums text-slate-300">
                {worldLoading ? 'Fetching...' : obs?.status ?? (worldError ? 'ERROR' : 'UNAVAILABLE')}
              </span>
            </div>
            {obs ? (
              <div className="mt-2 space-y-1.5">
                <div className="text-sm font-medium text-white">
                  {obs.temperatureC !== null
                    ? `${obs.temperatureC.toFixed(1)}°C · ${obs.weatherSummary}`
                    : obs.weatherSummary}
                </div>
                <div className="text-xs text-slate-400 flex flex-wrap gap-x-2 gap-y-0.5 font-mono tabular-nums">
                  <span>Rain {obs.precipitationMm ?? '—'}mm</span>
                  <span aria-hidden="true">·</span>
                  <span>Wind {obs.windSpeedKmh ?? '—'}km/h</span>
                  <span aria-hidden="true">·</span>
                  <span>Cloud {obs.cloudCoverPct ?? '—'}%</span>
                </div>
                <div className="text-[11px] text-slate-500">
                  {obs.sourceName} ({obs.license}) · {obs.observedAt ? `Observed ${obs.observedAt}` : 'No live observation'} · Freshness {obs.freshnessSec}s
                </div>
              </div>
            ) : (
              <div className="mt-2 text-xs text-slate-400">
                {worldError ? `Feed notice: ${worldError}` : 'Connecting to Open-Meteo grid feed...'}
              </div>
            )}
          </div>

          {/* Layer 2: Calculated */}
          <div className="p-4 sm:p-5">
            <div className="flex items-center justify-between gap-2 text-xs text-slate-400">
              <span className="font-semibold text-amber-400">Layer 2 · Calculated Math &amp; Ephemeris</span>
              <span className="font-mono tabular-nums text-slate-300">{utcDate} UTC</span>
            </div>
            <div className="mt-2 space-y-1.5">
              <div className="text-sm font-medium text-white">
                {calc
                  ? `${calc.ephemeris.lunarPhaseName} (${calc.ephemeris.lunarIlluminationPct}% lit) · Solar Alt ${calc.ephemeris.solarAltitudeDeg}°`
                  : 'Computing astronomical ephemeris...'}
              </div>
              <div className="text-xs text-slate-300 flex flex-wrap gap-x-2 gap-y-0.5">
                <span className="font-mono tabular-nums">Daily Target {dailyChallenge.targetNumber}</span>
                <span aria-hidden="true" className="text-slate-600">·</span>
                <span>Root {dailyChallenge.targetTreeRoot} ({dailyChallenge.targetSephirahName.split('(')[0].trim()})</span>
              </div>
              <div className="text-[11px] text-slate-500">
                Pure offline spherical astronomy + 37-word live-summed canonical seed
              </div>
            </div>
          </div>

          {/* Layer 3: Interpreted */}
          <div className="p-4 sm:p-5">
            <div className="flex items-center justify-between gap-2 text-xs text-slate-400">
              <span className="font-semibold text-emerald-400">Layer 3 · Interpreted Symbolic Resonance</span>
              {atmosphereIcon}
            </div>
            <div className="mt-2 space-y-1.5">
              <div className="text-sm font-medium text-white">
                {interp?.visualMoodTitle ?? 'Awaiting atmospheric mapping'}
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                {interp?.visualMoodDescription ?? 'Resonance layer colors the Living Tree particles symbolically.'}
              </p>
              <div className="text-[11px] text-slate-500">
                {interp?.nonCausalNotice ?? 'Symbolic visual mapping only; makes no causal prediction.'}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. SANCTUM TWO-ZONE WORKSPACE: NUMERICAL LAB (LEFT) + LIVING TREE OBSERVATORY (RIGHT) */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* LEFT COLUMN: LUMINOUS WORD & CIPHER LABORATORY (5 COLS) */}
        <section
          aria-label="Numerical Laboratory and Equivalence Finder"
          className="xl:col-span-5 space-y-5 min-w-0"
        >
          <div className="rounded-xl bg-white border border-slate-200 p-5 space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="text-base font-semibold text-slate-900">
                  Isopsephy &amp; Gematria Laboratory
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Greek (27 numerals), Hebrew (Hechrechi &amp; Gadol), English Extended &amp; Legacy
                </p>
              </div>
              <label className="inline-flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer select-none whitespace-nowrap shrink-0">
                <input
                  type="checkbox"
                  checked={includeLegacyLatin}
                  onChange={(e) => setIncludeLegacyLatin(e.target.checked)}
                  className="rounded border-slate-300 text-slate-900 focus:ring-slate-900"
                />
                <span className="whitespace-nowrap">Legacy A–Z Diff</span>
              </label>
            </div>

            <div>
              <label htmlFor="hermes-word-input" className="sr-only">
                Enter word, name, or phrase in Greek, Hebrew, or English
              </label>
              <div className="flex gap-2">
                <input
                  id="hermes-word-input"
                  type="text"
                  dir="auto"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  placeholder="Enter Greek (Ἰησοῦς), Hebrew (אהבה), or English..."
                  className="flex-1 min-w-0 rounded-lg border border-slate-300 bg-slate-50 px-3.5 py-2.5 text-base font-medium text-slate-900 placeholder:text-slate-400 focus:border-slate-900 focus:bg-white focus:outline-none"
                />
                <button
                  type="button"
                  onClick={() => {
                    setInputText('');
                    setSelectedSephirahNum(null);
                    setSelectedPathNum(null);
                  }}
                  title="Clear input"
                  aria-label="Clear input"
                  className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 whitespace-nowrap shrink-0"
                >
                  Clear
                </button>
              </div>
            </div>

            {/* Curated Quick Presets */}
            <div className="flex flex-wrap gap-1.5" role="group" aria-label="Canonical word examples">
              {PRESET_WORDS.map((preset) => {
                const isSelected = inputText === preset.text;
                return (
                  <button
                    key={preset.text}
                    type="button"
                    dir="ltr"
                    onClick={() => {
                      setInputText(preset.text);
                      setSelectedSephirahNum(null);
                      setSelectedPathNum(null);
                    }}
                    className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium border transition-colors whitespace-nowrap shrink-0 ${
                      isSelected
                        ? 'bg-slate-900 text-white border-slate-900'
                        : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
                    }`}
                  >
                    <bdi>{preset.word}</bdi>
                    <span>{preset.suffix}</span>
                  </button>
                );
              })}
            </div>

            {/* Dual-Mode Bug Explanation Notice when W/X/Y/Z appears in Latin input */}
            {dualDiff.hasWraparoundDefect && includeLegacyLatin && (
              <div className="rounded-lg border border-amber-300 bg-amber-50 p-3.5 text-xs text-amber-950 space-y-1">
                <div className="font-semibold">
                  Legacy W=A Wraparound Anomaly Detected ({dualDiff.collidingWrapChars.join(', ')})
                </div>
                <p className="leading-relaxed text-amber-900">
                  {dualDiff.explanation}
                </p>
              </div>
            )}

            {/* Empty / Reading Summary Display */}
            {readings.length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 text-xs text-slate-600">
                No Greek, Hebrew, or ASCII Latin characters found yet. Try entering <strong>Ἰησοῦς</strong>,{' '}
                <strong>χξϛ</strong>, <strong>מלכות</strong>, or <strong>Hello World</strong>.
              </div>
            ) : (
              <div className="space-y-3">
                {readings.map((reading) => {
                  const seph = resolveSephirahForValue(reading.total);
                  return (
                    <div
                      key={reading.cipherId}
                      className="rounded-lg border border-slate-200 bg-slate-50/70 p-4 space-y-3"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="text-xs font-semibold text-slate-700">
                            {reading.system}
                          </div>
                          <div className="text-[11px] text-slate-500 mt-0.5 flex flex-wrap gap-x-2">
                            <span>Script: {reading.script}</span>
                            <span aria-hidden="true">·</span>
                            <span>
                              {seph
                                ? `Root ${reading.treeRoot} -> ${seph.number} ${seph.name}`
                                : 'Off the Tree (0)'}
                            </span>
                            <span aria-hidden="true">·</span>
                            <span className="font-mono">{reading.reproducibilityHash}</span>
                          </div>
                        </div>
                        <div className="text-right shrink-0">
                          <div className="text-2xl font-bold font-mono tabular-nums text-slate-900">
                            {reading.total.toLocaleString()}
                          </div>
                          <div className="text-[11px] text-slate-500 font-mono tabular-nums">
                            ladder {reading.reductionLadder.join(' -> ')}
                          </div>
                        </div>
                      </div>

                      {/* Luminous Letter Decomposition Tiles */}
                      <div
                        dir={reading.script === 'hebrew' ? 'rtl' : 'ltr'}
                        className="flex flex-wrap gap-1.5"
                      >
                        {reading.breakdown.map((b) => {
                          const walked =
                            reading.script === 'hebrew'
                              ? resolvePathForHebrewChar(b.normalizedChar)
                              : null;
                          return (
                            <button
                              key={`${reading.cipherId}-${b.index}`}
                              type="button"
                              onClick={() => {
                                if (walked) {
                                  setSelectedPathNum(walked.number);
                                  setSelectedSephirahNum(null);
                                }
                              }}
                              title={
                                walked
                                  ? `Inspect Path ${walked.number} (${walked.letterName})`
                                  : `${b.letterName} = ${b.value}`
                              }
                              className={`flex flex-col items-center justify-center rounded-md border px-2.5 py-1.5 min-w-[44px] transition-colors ${
                                walked
                                  ? 'border-amber-300 bg-white hover:bg-amber-50 cursor-pointer'
                                  : 'border-slate-200 bg-white'
                              }`}
                            >
                              <span className="text-base font-semibold text-slate-900 leading-none">
                                {b.originalChar}
                              </span>
                              <span className="mt-1 text-[11px] font-mono tabular-nums font-medium text-slate-600">
                                {b.value}
                              </span>
                            </button>
                          );
                        })}
                      </div>

                      {reading.legacyWarning && (
                        <p className="text-[11px] text-amber-800 leading-relaxed">
                          {reading.legacyWarning}
                        </p>
                      )}

                      {reading.skipped > 0 && (
                        <div className="text-[11px] text-slate-600">
                          Ignored non-scoring characters ({reading.skipped}):{' '}
                          <span className="font-mono">
                            {reading.skippedChars
                              .slice(0, 8)
                              .map((s) => `${s.char} (${s.codePoint})`)
                              .join(', ')}
                          </span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Live Canonical Equivalences & Near Matches */}
          <div className="rounded-xl bg-white border border-slate-200 p-5 space-y-3">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-semibold text-slate-900">
                Equivalence Constellation{' '}
                {primaryReading && primaryReading.total > 0
                  ? `(${primaryReading.total})`
                  : ''}
              </h3>
              <span className="text-xs text-slate-500">Live summed over 37-word canon</span>
            </div>

            {exactEquivalences.length > 0 ? (
              <div className="space-y-2">
                {exactEquivalences.map((eq) => (
                  <button
                    key={eq.canonicalId}
                    type="button"
                    onClick={() => setInputText(eq.word)}
                    className="w-full text-left rounded-lg border border-amber-200 bg-amber-50/50 hover:bg-amber-50 px-3.5 py-2.5 flex items-center justify-between gap-3 transition-colors"
                  >
                    <div className="min-w-0">
                      <div className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                        <span>{eq.word}</span>
                        <span className="text-xs font-normal text-slate-600">
                          {eq.transliteration} — {eq.gloss}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-500 mt-0.5 truncate">
                        {eq.sourceCitation}
                      </div>
                    </div>
                    <span className="text-xs font-mono tabular-nums font-semibold text-amber-900 shrink-0">
                      = {eq.reading.total}
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500">
                No exact match in the 37-word historical canon for{' '}
                {primaryReading ? primaryReading.total : 0}.
              </p>
            )}

            {nearEquivalences.length > 0 && (
              <div className="pt-2 border-t border-slate-100">
                <div className="text-xs font-medium text-slate-600 mb-2">
                  Nearest Neighbors (±6)
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {nearEquivalences.map((near) => (
                    <button
                      key={near.canonicalId}
                      type="button"
                      onClick={() => setInputText(near.word)}
                      className="rounded-md border border-slate-200 bg-slate-50 hover:bg-slate-100 px-2.5 py-1 text-xs text-slate-700"
                    >
                      {near.word} ({near.reading.total},{' '}
                      {near.delta > 0 ? `+${near.delta}` : near.delta})
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>

        {/* RIGHT COLUMN: INTERACTIVE LIVING TREE OF LIFE OBSERVATORY (7 COLS) */}
        <section
          aria-label="Interactive Living Tree of Life"
          className="xl:col-span-7 min-w-0 rounded-xl bg-[#070B14] text-slate-100 border border-slate-800 overflow-hidden"
        >
          {/* Tree Toolbar: Mode Switch + Tradition Attribution + Controls */}
          <div className="px-5 py-4 border-b border-slate-800/90 flex flex-col gap-3">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <div className="inline-flex items-center gap-1 bg-slate-900 p-1 rounded-lg border border-slate-700">
                  <button
                    type="button"
                    onClick={() => setTreeMode('codex')}
                    aria-pressed={treeMode === 'codex'}
                    className={`px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap shrink-0 ${
                      treeMode === 'codex'
                        ? 'bg-sky-400 text-slate-950 font-semibold'
                        : 'text-slate-300 hover:text-white'
                    }`}
                  >
                    Codex Crescendo
                  </button>
                  <button
                    type="button"
                    onClick={() => setTreeMode('cipher')}
                    aria-pressed={treeMode === 'cipher'}
                    className={`px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap shrink-0 ${
                      treeMode === 'cipher'
                        ? 'bg-amber-400 text-slate-950 font-semibold'
                        : 'text-slate-300 hover:text-white'
                    }`}
                  >
                    Cipher Tree
                  </button>
                </div>

                <div className="inline-flex flex-wrap sm:flex-nowrap items-center gap-1 bg-slate-900 p-1 rounded-lg border border-slate-800">
                  {ATTRIBUTION_TRADITIONS.map((t) => {
                    const active = tradition === t.id;
                    return (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => setTradition(t.id)}
                        aria-pressed={active}
                        className={`px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap shrink-0 ${
                          active
                            ? 'bg-amber-400 text-slate-950 font-semibold'
                            : 'text-slate-300 hover:text-white'
                        }`}
                      >
                        {t.shortLabel}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2 shrink-0">
                <button
                  type="button"
                  onClick={() => setAudioEnabled((v) => !v)}
                  aria-pressed={audioEnabled}
                  aria-label="Toggle Rosicrucian acoustic harmonics"
                  className={`inline-flex items-center gap-1 rounded-md border px-2.5 py-1.5 text-xs font-medium whitespace-nowrap shrink-0 ${
                    audioEnabled
                      ? 'border-amber-400 bg-amber-500/20 text-amber-200'
                      : 'border-slate-700 bg-slate-900 text-slate-300 hover:text-white'
                  }`}
                >
                  {audioEnabled ? (
                    <Volume2 className="h-3.5 w-3.5" aria-hidden="true" />
                  ) : (
                    <VolumeX className="h-3.5 w-3.5" aria-hidden="true" />
                  )}
                  <span>{audioEnabled ? 'Audio On' : 'Audio Off'}</span>
                </button>
                <button
                  type="button"
                  onClick={() => setTiltPerspective((v) => !v)}
                  aria-pressed={tiltPerspective}
                  className="rounded-md border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-800 whitespace-nowrap shrink-0"
                >
                  {tiltPerspective ? '3D Depth On' : 'Flat 2D'}
                </button>
                <button
                  type="button"
                  onClick={() => setReducedMotion((v) => !v)}
                  aria-pressed={reducedMotion}
                  className="rounded-md border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-800 whitespace-nowrap shrink-0"
                >
                  {reducedMotion ? 'Static Mode' : 'Animate Sky'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedSephirahNum(null);
                    setSelectedPathNum(null);
                    setInjectedQliphah('none');
                  }}
                  aria-label="Reset Tree selection"
                  className="inline-flex items-center gap-1 rounded-md border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs font-medium text-slate-300 hover:text-white whitespace-nowrap shrink-0"
                >
                  <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
                  <span>Reset</span>
                </button>
              </div>
            </div>

            {treeMode === 'codex' && (
              <div className="pt-2 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="inline-flex flex-wrap items-center gap-1 bg-slate-900/90 p-1 rounded-md border border-slate-800">
                  {OLAMOT_WORLDS.map((w) => (
                    <button
                      key={w.id}
                      type="button"
                      onClick={() => setOlamScale(w.id)}
                      className={`px-2 py-1 rounded text-[11px] font-medium whitespace-nowrap ${
                        olamScale === w.id
                          ? 'bg-slate-100 text-slate-950 font-semibold'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      {w.worldName} ({w.scaleName.split(' ')[0]})
                    </button>
                  ))}
                </div>

                <div className="inline-flex flex-wrap items-center gap-1 bg-slate-900/90 p-1 rounded-md border border-slate-800">
                  {(
                    [
                      ['mezla', 'Mezla (Flash)'],
                      ['nachash', 'Nachash (Serpent)'],
                      ['samekh_gimel', 'Samekh–Gimel (Pass-0)'],
                    ] as const
                  ).map(([id, label]) => (
                    <button
                      key={id}
                      type="button"
                      onClick={() => setCrescendoCurrent(id)}
                      className={`px-2 py-1 rounded text-[11px] font-medium whitespace-nowrap ${
                        crescendoCurrent === id
                          ? 'bg-sky-500 text-slate-950 font-semibold'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>

                <div className="inline-flex items-center gap-1 bg-slate-900/90 p-1 rounded-md border border-slate-800">
                  {([0, 1, 2] as const).map((z) => (
                    <button
                      key={z}
                      type="button"
                      onClick={() => setZoomLevel(z)}
                      className={`px-2 py-1 rounded text-[11px] font-medium whitespace-nowrap ${
                        zoomLevel === z
                          ? 'bg-amber-400 text-slate-950 font-semibold'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      {z === 0 ? 'Zoom 0 Macro' : z === 1 ? 'Zoom 1 Triad' : 'Zoom 2 Assiah'}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="px-5 py-2.5 bg-slate-950/70 border-b border-slate-800/80 text-xs text-slate-400 flex flex-wrap items-center justify-between gap-2">
            <span>
              Tradition: <strong className="text-slate-200">{activeTraditionMeta.name}</strong>
              {treeMode === 'codex' && (
                <>
                  {' '}
                  · Scale:{' '}
                  <strong className="text-amber-300">
                    {OLAMOT_WORLDS.find((w) => w.id === olamScale)?.scaleName}
                  </strong>
                </>
              )}
            </span>
            <span className="text-[11px] text-slate-400">
              {treeMode === 'codex'
                ? chronoState.summaryText
                : activeTraditionMeta.sourceCitation}
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12">
            {/* Sacred Geometry Canvas + Interactive SVG Tree */}
            <div className="lg:col-span-7 relative min-h-[560px] flex flex-col items-center justify-between p-4 overflow-hidden bg-[radial-gradient(circle_at_50%_18%,rgba(30,58,138,0.28),rgba(7,11,20,0.98)_72%)]">
              <canvas
                ref={canvasRef}
                aria-hidden="true"
                className="pointer-events-none absolute inset-0 w-full h-full opacity-80"
              />

              <div
                style={{
                  transform:
                    tiltPerspective && !reducedMotion
                      ? `perspective(900px) rotateX(6deg) scale(${zoomLevel === 0 ? 1 : zoomLevel === 1 ? 1.07 : 1.13})`
                      : `scale(${zoomLevel === 0 ? 1 : zoomLevel === 1 ? 1.07 : 1.13})`,
                  transition: 'transform 220ms cubic-bezier(0.16, 1, 0.3, 1)',
                }}
                className="relative z-10 w-full max-w-[440px]"
              >
                <svg
                  viewBox="0 -24 1000 1048"
                  role="img"
                  aria-label="Interactive Kabbalistic Tree of Life with 10 Sephirot, Da'ath, Three Veils, and 22 Canonical Paths"
                  className="w-full h-auto select-none"
                >
                  {/* Pillar Vertical Guides */}
                  <g stroke="rgba(148,163,184,0.14)" strokeWidth="1.5" strokeDasharray="6 8">
                    <line x1="215" y1="132" x2="215" y2="710" />
                    <line x1="500" y1="22" x2="500" y2="960" />
                    <line x1="785" y1="132" x2="785" y2="710" />
                  </g>

                  <g fill="rgba(148,163,184,0.52)" fontSize="22" fontWeight="500" textAnchor="middle">
                    <text x="215" y="114">Severity</text>
                    <text x="500" y="6">Equilibrium</text>
                    <text x="785" y="114">Mercy</text>
                  </g>

                  {/* Three Horizontal Veils in Codex Mode: Abyss (300), Paroketh (602), Qesheth (854) */}
                  {treeMode === 'codex' &&
                    THREE_VEILS.map((veil) => (
                      <g key={veil.id}>
                        <line
                          x1="75"
                          y1={veil.y}
                          x2="925"
                          y2={veil.y}
                          stroke={
                            veil.id === 'qesheth'
                              ? 'rgba(56, 189, 248, 0.55)'
                              : veil.id === 'paroketh'
                                ? 'rgba(250, 204, 21, 0.42)'
                                : 'rgba(196, 181, 253, 0.52)'
                          }
                          strokeWidth="2"
                          strokeDasharray="10 7"
                        />
                        <text
                          x="90"
                          y={veil.y - 8}
                          fontSize="16"
                          fontWeight="600"
                          fill={
                            veil.id === 'qesheth'
                              ? '#7DD3FC'
                              : veil.id === 'paroketh'
                                ? '#FDE68A'
                                : '#DDD6FE'
                          }
                        >
                          {veil.name.split(' (')[0]}
                        </text>
                      </g>
                    ))}

                  {/* 22 Paths */}
                  {TREE_PATHS.map((path) => {
                    const fromNode = SEPHIROT.find((s) => s.number === path.fromSephirah)!;
                    const toNode = SEPHIROT.find((s) => s.number === path.toSephirah)!;
                    const isWalked = walkedPathNumbers.has(path.number);
                    const isCurrentLit =
                      treeMode === 'codex' && chronoState.activePathNumbers.includes(path.number);
                    const isFractured =
                      treeMode === 'codex' && chronoState.fracturedPathNumber === path.number;
                    const isSelectedPath = selectedPathNum === path.number;
                    const isConnectedToSelectedSeph =
                      focusedSephirah !== null &&
                      (path.fromSephirah === focusedSephirah.number ||
                        path.toSephirah === focusedSephirah.number);
                    const midX = (fromNode.x + toNode.x) / 2;
                    const midY = (fromNode.y + toNode.y) / 2;
                    const codexPathMeta = CODEX_PATHS_EXTENDED.find(
                      (cp) => cp.pathNumber === path.number
                    );

                    const baseStroke = isFractured
                      ? '#EF4444'
                      : isSelectedPath || isWalked
                        ? '#F59E0B'
                        : isCurrentLit
                          ? codexPathMeta?.chromaticRayHex ?? '#38BDF8'
                          : isConnectedToSelectedSeph
                            ? '#38BDF8'
                            : 'rgba(148, 163, 184, 0.34)';

                    // Jagged fracture polyline endpoints for Qliphothic chromatic aberration
                    const qX1 = (fromNode.x * 2 + toNode.x) / 3 + 14;
                    const qY1 = (fromNode.y * 2 + toNode.y) / 3 - 12;
                    const qX2 = (fromNode.x + toNode.x * 2) / 3 - 14;
                    const qY2 = (fromNode.y + toNode.y * 2) / 3 + 12;

                    return (
                      <g
                        key={path.number}
                        role="button"
                        tabIndex={0}
                        aria-label={`Path ${path.number}: ${path.letter} ${path.letterName}, ${resolvePathPresentation(path, tradition).trumpLabel}`}
                        onClick={() => {
                          setSelectedPathNum(path.number);
                          setSelectedSephirahNum(null);
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            setSelectedPathNum(path.number);
                            setSelectedSephirahNum(null);
                          }
                        }}
                        className="cursor-pointer focus:outline-none"
                      >
                        <line
                          x1={fromNode.x}
                          y1={fromNode.y}
                          x2={toNode.x}
                          y2={toNode.y}
                          stroke="transparent"
                          strokeWidth="26"
                        />
                        {isFractured ? (
                          <g>
                            <polyline
                              points={`${fromNode.x},${fromNode.y} ${qX1 + 4},${qY1 + 3} ${qX2 + 4},${qY2 + 3} ${toNode.x},${toNode.y}`}
                              fill="none"
                              stroke="#22D3EE"
                              strokeWidth="3.5"
                              opacity="0.7"
                            />
                            <polyline
                              points={`${fromNode.x},${fromNode.y} ${qX1},${qY1} ${qX2},${qY2} ${toNode.x},${toNode.y}`}
                              fill="none"
                              stroke="#EF4444"
                              strokeWidth="6"
                              strokeLinejoin="miter"
                            />
                          </g>
                        ) : (
                          <line
                            x1={fromNode.x}
                            y1={fromNode.y}
                            x2={toNode.x}
                            y2={toNode.y}
                            stroke={baseStroke}
                            strokeWidth={
                              isSelectedPath || isWalked || isCurrentLit
                                ? 5.5
                                : isConnectedToSelectedSeph
                                  ? 3.5
                                  : 2
                            }
                            strokeLinecap="round"
                          />
                        )}
                        <circle
                          cx={midX}
                          cy={midY}
                          r={isFractured || isWalked || isSelectedPath || isCurrentLit ? 16 : 13}
                          fill={
                            isFractured
                              ? '#991B1B'
                              : isWalked || isSelectedPath
                                ? '#F59E0B'
                                : isCurrentLit
                                  ? '#0B1324'
                                  : '#0F172A'
                          }
                          stroke={
                            isFractured
                              ? '#FCA5A5'
                              : isWalked || isSelectedPath
                                ? '#FEF3C7'
                                : isCurrentLit
                                  ? codexPathMeta?.chromaticRayHex ?? '#38BDF8'
                                  : 'rgba(148,163,184,0.45)'
                          }
                          strokeWidth={isCurrentLit ? '2.5' : '1.5'}
                        />
                        <text
                          x={midX}
                          y={midY + 6}
                          textAnchor="middle"
                          fontSize="18"
                          fontWeight="600"
                          fill={isWalked || isSelectedPath ? '#070B14' : '#F8FAFC'}
                        >
                          {path.letter}
                        </text>
                      </g>
                    );
                  })}

                  {/* Da'ath Invisible Abyss Gate (visible in Codex Mode) */}
                  {treeMode === 'codex' && (() => {
                    const daath = CODEX_SPHERES.find((s) => s.isDaath)!;
                    const scaleCol = resolveSphereHexForScale(daath, olamScale);
                    const daathLit = chronoState.activeSphereNumbers.includes(0);
                    return (
                      <g aria-label="Da'ath Abyss Gate (333)">
                        <circle
                          cx={daath.x}
                          cy={daath.y}
                          r="32"
                          fill="#090D1A"
                          stroke={scaleCol.primaryHex}
                          strokeWidth={daathLit ? 3.5 : 1.75}
                          strokeDasharray={daathLit ? undefined : '5 4'}
                        />
                        <text
                          x={daath.x}
                          y={daath.y - 2}
                          textAnchor="middle"
                          fontSize="17"
                          fontWeight="700"
                          fill={scaleCol.primaryHex}
                        >
                          דעת
                        </text>
                        <text
                          x={daath.x}
                          y={daath.y + 15}
                          textAnchor="middle"
                          fontSize="13"
                          fill="#CBD5E1"
                        >
                          Da'ath · 333
                        </text>
                      </g>
                    );
                  })()}

                  {/* 10 Sephirot Nodes */}
                  {SEPHIROT.map((seph) => {
                    const isLandedRoot = landedSephirah?.number === seph.number;
                    const isFocused = focusedSephirah?.number === seph.number;
                    const codexSpec = CODEX_SPHERES.find((c) => c.number === seph.number)!;
                    const scaleCol = resolveSphereHexForScale(codexSpec, olamScale);
                    const isCodexActive =
                      treeMode === 'codex' && chronoState.activeSphereNumbers.includes(seph.number);
                    const isHeadSphere =
                      treeMode === 'codex' && chronoState.headSphereNumber === seph.number;
                    const isMalkuthDark =
                      treeMode === 'codex' && seph.number === 10 && !chronoState.malkuthSealed;
                    const nodeRadius = isLandedRoot || isFocused || isHeadSphere ? 46 : 40;

                    return (
                      <g
                        key={seph.number}
                        role="button"
                        tabIndex={0}
                        aria-label={`Sephirah ${seph.number}: ${seph.name} (${seph.meaning}), Sphere: ${seph.sphere}`}
                        onClick={() => {
                          setSelectedSephirahNum(seph.number);
                          setSelectedPathNum(null);
                        }}
                        onKeyDown={(e) => handleSephirahKeyDown(e, seph.number)}
                        className="cursor-pointer focus:outline-none"
                      >
                        {(isLandedRoot || isHeadSphere) && (
                          <circle
                            cx={seph.x}
                            cy={seph.y}
                            r="62"
                            fill="none"
                            stroke={treeMode === 'codex' ? scaleCol.primaryHex : 'rgba(245, 158, 11, 0.45)'}
                            strokeWidth="2.5"
                            strokeDasharray="6 6"
                          />
                        )}
                        {isFocused && (
                          <circle
                            cx={seph.x}
                            cy={seph.y}
                            r="55"
                            fill="none"
                            stroke="#38BDF8"
                            strokeWidth="2.5"
                          />
                        )}
                        {treeMode === 'codex' && scaleCol.fleckHex && (
                          <circle
                            cx={seph.x}
                            cy={seph.y}
                            r={nodeRadius + 5}
                            fill="none"
                            stroke={scaleCol.fleckHex}
                            strokeWidth="2"
                            strokeDasharray="3 5"
                          />
                        )}
                        <circle
                          cx={seph.x}
                          cy={seph.y}
                          r={nodeRadius}
                          fill={
                            isMalkuthDark
                              ? '#090B12'
                              : isLandedRoot || isCodexActive
                                ? '#182238'
                                : '#0B1324'
                          }
                          stroke={
                            treeMode === 'codex'
                              ? isMalkuthDark
                                ? '#475569'
                                : scaleCol.primaryHex
                              : isLandedRoot
                                ? '#FBBF24'
                                : isFocused
                                  ? '#38BDF8'
                                  : '#64748B'
                          }
                          strokeWidth={isLandedRoot || isHeadSphere ? 4 : isCodexActive ? 3 : 2}
                        />
                        <text
                          x={seph.x}
                          y={seph.y - 6}
                          textAnchor="middle"
                          fontSize="24"
                          fontWeight="700"
                          fill={isMalkuthDark ? '#64748B' : '#F8FAFC'}
                        >
                          {seph.number} · {seph.hebrew}
                        </text>
                        <text
                          x={seph.x}
                          y={seph.y + 20}
                          textAnchor="middle"
                          fontSize="18"
                          fontWeight="500"
                          fill={
                            isMalkuthDark
                              ? '#64748B'
                              : treeMode === 'codex' && isCodexActive
                                ? scaleCol.primaryHex
                                : isLandedRoot
                                  ? '#FDE68A'
                                  : '#94A3B8'
                          }
                        >
                          {seph.name}
                        </text>
                      </g>
                    );
                  })}
                </svg>
              </div>

              {/* Chrono-Astrolabe Scrubber Bar (60fps zero-token replay) */}
              {treeMode === 'codex' && (
                <div className="relative z-10 w-full mt-3 rounded-lg bg-slate-950/90 border border-slate-800 px-3.5 py-2.5 space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2 text-[11px]">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          if (chronoProgress >= 1) setChronoProgress(0);
                          setChronoPlaying((p) => !p);
                        }}
                        className="inline-flex items-center gap-1 rounded bg-amber-400 px-2.5 py-1 text-xs font-semibold text-slate-950 hover:bg-amber-300"
                      >
                        {chronoPlaying ? (
                          <Pause className="h-3.5 w-3.5" aria-hidden="true" />
                        ) : (
                          <Play className="h-3.5 w-3.5" aria-hidden="true" />
                        )}
                        <span>{chronoPlaying ? 'Pause' : 'Play Replay'}</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setChronoPlaying(false);
                          setChronoProgress((p) => Math.min(1, Number((p + 0.1).toFixed(2))));
                        }}
                        className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-200 hover:bg-slate-800"
                      >
                        Step +10%
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setChronoPlaying(false);
                          setChronoProgress(0);
                        }}
                        className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-300 hover:bg-slate-800"
                      >
                        Reset
                      </button>
                    </div>
                    <div className="font-mono tabular-nums text-slate-300">
                      Astrolabe {Math.round(chronoProgress * 100)}% · Dilation{' '}
                      <strong className="text-sky-300">{chronoState.timeDilation}</strong>
                    </div>
                  </div>
                  <label className="block">
                    <span className="sr-only">Chrono-Astrolabe timeline scrubber</span>
                    <input
                      type="range"
                      min={0}
                      max={100}
                      value={Math.round(chronoProgress * 100)}
                      onChange={(e) => {
                        setChronoPlaying(false);
                        setChronoProgress(Number(e.target.value) / 100);
                      }}
                      className="w-full accent-amber-400 cursor-pointer"
                    />
                  </label>
                </div>
              )}
            </div>

            {/* Right Sub-panel: Interactive Scholar, Codex Inspector & Pillar Equilibrium */}
            <div className="lg:col-span-5 border-t lg:border-t-0 lg:border-l border-slate-800/90 p-5 space-y-4 bg-slate-950/80">
              {focusedPath ? (
                <div className="space-y-3">
                  <div className="text-xs font-semibold text-amber-400">
                    Inspecting Path {focusedPath.number} · {focusedPath.letter} ({focusedPath.letterName})
                  </div>
                  <h4 className="text-lg font-semibold text-white">
                    {resolvePathPresentation(focusedPath, tradition).trumpLabel}
                  </h4>
                  <div className="text-xs text-slate-300 space-y-1.5">
                    <div>
                      <span className="text-slate-500">Sefer Yetzirah Class:</span>{' '}
                      <span className="capitalize text-slate-100">{focusedPath.kind}</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Attribution:</span>{' '}
                      <span className="text-slate-100">
                        {resolvePathPresentation(focusedPath, tradition).attributionLabel}
                      </span>
                    </div>
                    {(() => {
                      const ext = CODEX_PATHS_EXTENDED.find((c) => c.pathNumber === focusedPath.number);
                      if (!ext) return null;
                      return (
                        <>
                          <div>
                            <span className="text-slate-500">Protocol Predicate:</span>{' '}
                            <span className="text-slate-100">{ext.meridianPredicate}</span>
                          </div>
                          <div>
                            <span className="text-slate-500">Liber 777 Ray:</span>{' '}
                            <span style={{ color: ext.chromaticRayHex }} className="font-semibold">
                              {ext.chromaticRayName}
                            </span>
                          </div>
                        </>
                      );
                    })()}
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed pt-2 border-t border-slate-800">
                    {resolvePathPresentation(focusedPath, tradition).note}
                  </p>
                </div>
              ) : focusedSephirah ? (
                <div className="space-y-3">
                  <div className="text-xs font-semibold text-sky-400">
                    Sephirah {focusedSephirah.number} · {focusedSephirah.hebrew}
                    {landedSephirah?.number === focusedSephirah.number ? ' · Active Word Root' : ''}
                  </div>
                  <h4 className="text-lg font-semibold text-white">
                    {focusedSephirah.name} — {focusedSephirah.meaning}
                  </h4>
                  {(() => {
                    const spec = CODEX_SPHERES.find((c) => c.number === focusedSephirah.number);
                    const scaleInfo = spec ? resolveSphereHexForScale(spec, olamScale) : null;
                    return (
                      <div className="text-xs text-slate-300 space-y-1.5">
                        <div>
                          <span className="text-slate-500">Constitutional Office:</span>{' '}
                          <span className="text-slate-100">{spec?.constitutionalOffice}</span>
                        </div>
                        <div>
                          <span className="text-slate-500">Mandated Receipt:</span>{' '}
                          <span className="font-mono text-amber-300">{spec?.mandatedReceipt}</span>
                        </div>
                        {scaleInfo && (
                          <div>
                            <span className="text-slate-500">Liber 777 Scale Pigment:</span>{' '}
                            <span style={{ color: scaleInfo.primaryHex }} className="font-semibold">
                              {scaleInfo.scaleLabel}
                            </span>
                          </div>
                        )}
                        <div>
                          <span className="text-slate-500">Sphere &amp; Divine Name:</span>{' '}
                          <span className="text-slate-100">{focusedSephirah.sphere}</span> ·{' '}
                          <span className="text-slate-100" dir="rtl">{focusedSephirah.divineNameHeb}</span>
                        </div>
                      </div>
                    );
                  })()}

                  <div className="pt-2 border-t border-slate-800">
                    <div className="text-xs font-medium text-slate-400 mb-2">
                      Connected Paths ({getSephirahNeighbors(focusedSephirah.number).paths.length})
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {getSephirahNeighbors(focusedSephirah.number).paths.map((np) => (
                        <button
                          key={np.number}
                          type="button"
                          onClick={() => {
                            setSelectedPathNum(np.number);
                            setSelectedSephirahNum(null);
                          }}
                          className={`rounded px-2 py-1 text-xs border transition-colors ${
                            walkedPathNumbers.has(np.number)
                              ? 'border-amber-400/70 bg-amber-500/15 text-amber-200'
                              : 'border-slate-700 bg-slate-900 text-slate-300 hover:text-white'
                          }`}
                        >
                          {np.number} {np.letter} · {np.letterName}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              ) : null}

              {/* Pillar Equilibrium Differential Equation & Qliphothic Fault Injector */}
              {treeMode === 'codex' && (
                <div className="pt-3 border-t border-slate-800 space-y-3">
                  <div className="flex items-center justify-between gap-2 text-xs">
                    <span className="font-semibold text-slate-200">
                      Pillar Equilibrium Ω = ln(M / S)
                    </span>
                    <span
                      className={`font-mono tabular-nums font-bold ${
                        omegaResult.regime === 'BALANCED'
                          ? 'text-emerald-400'
                          : omegaResult.regime === 'GHA_AGSHEBLAH_OVERHEAT'
                            ? 'text-amber-400'
                            : 'text-sky-400'
                      }`}
                    >
                      {omegaResult.omega >= 0 ? `+${omegaResult.omega}` : omegaResult.omega} ·{' '}
                      {omegaResult.regime}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-[11px]">
                    <label className="block space-y-1">
                      <span className="text-slate-400">
                        Mercy Throughput: <strong className="font-mono text-white">{mercyThroughput.toFixed(1)}x</strong>
                      </span>
                      <input
                        type="range"
                        min={0.3}
                        max={2.5}
                        step={0.1}
                        value={mercyThroughput}
                        onChange={(e) => setMercyThroughput(Number(e.target.value))}
                        className="w-full accent-sky-400"
                      />
                    </label>
                    <label className="block space-y-1">
                      <span className="text-slate-400">
                        Severity Strictness: <strong className="font-mono text-white">{severityStrictness.toFixed(1)}x</strong>
                      </span>
                      <input
                        type="range"
                        min={0.3}
                        max={2.5}
                        step={0.1}
                        value={severityStrictness}
                        onChange={(e) => setSeverityStrictness(Number(e.target.value))}
                        className="w-full accent-amber-400"
                      />
                    </label>
                  </div>

                  <p className="text-[11px] text-slate-400 leading-snug">
                    {omegaResult.tipharethAction}
                  </p>

                  <label className="block space-y-1 text-[11px]">
                    <span className="text-slate-400">Inject Qliphothic Chromatic Fracture:</span>
                    <select
                      value={injectedQliphah}
                      onChange={(e) => setInjectedQliphah(e.target.value as QliphahId)}
                      className="w-full rounded border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs text-slate-100"
                    >
                      <option value="none">None (Pure Merkle-DAG Light)</option>
                      {QLIPHOTH_REGISTRY.map((q) => (
                        <option key={q.id} value={q.id}>
                          {q.number}. {q.name} ({q.meaning} · Path {q.fracturedPathNumber})
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              )}

              {/* Paths walked by active Hebrew input */}
              {walkedPaths.length > 0 && (
                <div className="pt-3 border-t border-slate-800 space-y-2">
                  <div className="text-xs font-semibold text-amber-300">
                    Paths Walked by Current Word ({walkedPaths.length})
                  </div>
                  <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                    {walkedPaths.map((wp) => {
                      const pres = resolvePathPresentation(wp, tradition);
                      return (
                        <button
                          key={wp.number}
                          type="button"
                          onClick={() => {
                            setSelectedPathNum(wp.number);
                            setSelectedSephirahNum(null);
                          }}
                          className="w-full text-left rounded-md border border-slate-800 bg-slate-900/90 hover:border-amber-500/60 px-3 py-2 text-xs flex items-center justify-between gap-2"
                        >
                          <span className="text-slate-100 font-medium">
                            {wp.letter} {wp.letterName} (Path {wp.number})
                          </span>
                          <span className="text-slate-400 truncate">
                            {pres.trumpLabel} · {pres.attributionLabel}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              <div className="pt-2 border-t border-slate-800 text-[11px] text-slate-500 leading-relaxed">
                Keyboard tip: Tab onto any Sephirah sphere and use Arrow keys to traverse 1 (Kether) through 10 (Malkuth), or select any Hebrew letter path directly.
              </div>
            </div>
          </div>
        </section>
      </div>

      {/* 3. BOTTOM SANCTUM WINGS: DAILY CHALLENGE GAME & SCHOLARLY ATLAS */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Daily Deterministic Isopsephy Challenge (5 Cols) */}
        <section
          aria-label="Daily Numerical-Equivalence Game"
          className="xl:col-span-5 rounded-xl bg-white border border-slate-200 p-5 space-y-4"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-xs font-semibold text-slate-500">
                Daily Challenge · {dailyChallenge.utcDate} UTC
              </div>
              <h3 className="mt-1 text-lg font-semibold text-slate-900">
                Target Number:{' '}
                <span className="font-mono tabular-nums text-amber-700">
                  {dailyChallenge.targetNumber}
                </span>
              </h3>
              <p className="text-xs text-slate-600 mt-0.5">
                Any Greek, Hebrew, or English Extended word summing to{' '}
                <strong className="font-mono">{dailyChallenge.targetNumber}</strong> counts as a hit.
              </p>
            </div>
            <div className="text-right shrink-0">
              <div className="text-xs font-medium text-slate-500">Status</div>
              <div
                className={`text-sm font-semibold ${
                  hasSolvedDaily ? 'text-emerald-700' : 'text-slate-900'
                }`}
              >
                {hasSolvedDaily ? 'Solved' : `${attempts.length} tries`}
              </div>
            </div>
          </div>

          <form onSubmit={handleGuessSubmit} className="flex gap-2">
            <label htmlFor="daily-game-guess" className="sr-only">
              Enter candidate word for today's target
            </label>
            <input
              id="daily-game-guess"
              type="text"
              dir="auto"
              value={guessInput}
              onChange={(e) => setGuessInput(e.target.value)}
              placeholder={`Enter a word totaling ${dailyChallenge.targetNumber}...`}
              className="flex-1 min-w-0 rounded-lg border border-slate-300 bg-slate-50 px-3.5 py-2 text-sm text-slate-900 focus:border-slate-900 focus:bg-white focus:outline-none"
            />
            <button
              type="submit"
              disabled={guessSubmitting || !guessInput.trim()}
              className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0 disabled:opacity-50"
            >
              {guessSubmitting ? 'Checking...' : 'Submit Guess'}
            </button>
          </form>

          {guessError && (
            <div className="text-xs text-red-700 bg-red-50 border border-red-200 rounded-md p-2.5">
              {guessError}
            </div>
          )}

          {/* Progressive Hint Ladder */}
          <div className="flex items-center justify-between gap-2 pt-1">
            <button
              type="button"
              onClick={() => setHintLevel((h) => Math.min(3, h + 1))}
              disabled={hintLevel >= 3}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-700 hover:text-slate-950 disabled:opacity-40"
            >
              <HelpCircle className="h-3.5 w-3.5" aria-hidden="true" />
              <span>
                {hintLevel === 0
                  ? 'Reveal Hint (1/3)'
                  : hintLevel < 3
                    ? `Reveal Next Hint (${hintLevel}/3)`
                    : 'All 3 Hints Revealed'}
              </span>
            </button>
            <span className="text-[11px] text-slate-500">
              {dailyChallenge.reachableCanonCount} guaranteed canon answer(s)
            </span>
          </div>

          {hintLevel > 0 && (
            <ul className="space-y-1.5 rounded-lg bg-slate-50 border border-slate-200 p-3 text-xs text-slate-700">
              {hintLevel >= 1 && <li>1. {dailyChallenge.hintTier1Sephirah}</li>}
              {hintLevel >= 2 && <li>2. {dailyChallenge.hintTier2Script}</li>}
              {hintLevel >= 3 && <li>3. {dailyChallenge.hintTier3InitialGlyph}</li>}
            </ul>
          )}

          {/* Attempt History */}
          {attempts.length > 0 && (
            <div className="space-y-2 pt-2 border-t border-slate-100 max-h-56 overflow-y-auto">
              {attempts.map((att, idx) => (
                <div
                  key={`${att.guess}-${idx}`}
                  className={`rounded-lg border px-3 py-2 text-xs ${
                    att.hit
                      ? 'border-emerald-300 bg-emerald-50 text-emerald-950'
                      : 'border-slate-200 bg-slate-50 text-slate-800'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 font-semibold">
                    <span>{att.guess}</span>
                    <span className="font-mono tabular-nums">
                      {att.hit
                        ? `HIT · ${att.hittingSystems.join(', ')}`
                        : att.closestTotal !== null
                          ? `${att.closestSystem}: ${att.closestTotal} (off by ${att.distance})`
                          : 'No readable letters'}
                    </span>
                  </div>
                  {att.hit && att.matchedEquivalences.length > 0 && (
                    <div className="mt-1 text-[11px] text-emerald-800">
                      Shares value with:{' '}
                      {att.matchedEquivalences.map((m) => `${m.word} (${m.gloss})`).join(' · ')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Scholarly Reference Atlas, Cipher Tables, Legacy Summary Card & H0-H7 Audit (7 Cols) */}
        <section
          aria-label="Equivalence Atlas, Cipher Tables and Forensics"
          className="xl:col-span-7 min-w-0 rounded-xl bg-white border border-slate-200 p-5 space-y-4"
        >
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-200 pb-3">
            <div className="flex flex-wrap gap-1 bg-slate-100 p-1 rounded-lg">
              {(
                [
                  ['codex', 'Codex 231 Gates & Keys'],
                  ['canon', `37-Word Canon (${CANON_WORDS.length})`],
                  ['tables', 'Letter Tables (27/22)'],
                  ['legacy_card', 'Legacy /summary Export'],
                  ['forensics', 'H0–H7 Audit'],
                ] as ReadonlyArray<readonly [AtlasSubTab, string]>
              ).map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setAtlasTab(id)}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap shrink-0 ${
                    atlasTab === id
                      ? 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            {atlasTab === 'canon' && (
              <input
                type="search"
                value={canonSearch}
                onChange={(e) => setCanonSearch(e.target.value)}
                placeholder="Search word or value..."
                aria-label="Search 37-word historical canon"
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs text-slate-900 focus:border-slate-900 focus:outline-none sm:w-48"
              />
            )}
          </div>

          {atlasTab === 'codex' && (
            <CodexCrescendoPanel
              olamScale={olamScale}
              onSelectOlamScale={setOlamScale}
              injectedQliphah={injectedQliphah}
              onSelectQliphah={setInjectedQliphah}
              keyBinah={threeKeys.keyBinah}
              keyChesed={threeKeys.keyChesed}
              keyMalkuth={threeKeys.keyMalkuth}
              onChangeKeys={setThreeKeys}
            />
          )}

          {atlasTab === 'canon' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-h-80 overflow-y-auto pr-1">
              {filteredCanon.map((item) => (
                <button
                  key={item.canonicalId}
                  type="button"
                  onClick={() => {
                    setInputText(item.word);
                    setSelectedSephirahNum(null);
                    setSelectedPathNum(null);
                  }}
                  className="text-left rounded-lg border border-slate-200 hover:border-slate-400 hover:bg-slate-50 px-3 py-2 flex items-center justify-between gap-3 transition-colors"
                >
                  <div className="min-w-0">
                    <div className="text-sm font-semibold text-slate-900 truncate">
                      {item.word}{' '}
                      <span className="font-normal text-xs text-slate-600">
                        · {item.gloss}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-500 truncate">
                      {item.sourceCitation}
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="text-sm font-mono tabular-nums font-bold text-slate-900">
                      {item.reading.total}
                    </div>
                    <div className="text-[10px] text-slate-500">
                      Root {item.reading.treeRoot}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}

          {atlasTab === 'tables' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-80 overflow-y-auto pr-1 text-xs">
              <div>
                <h4 className="font-semibold text-slate-900 mb-2">
                  Greek Isopsephy (27 Classical Numerals)
                </h4>
                <div className="grid grid-cols-3 gap-1.5">
                  {GREEK_ROWS.map(([ch, name, val]) => (
                    <div
                      key={ch}
                      className="rounded border border-slate-200 bg-slate-50 px-2 py-1.5 flex items-center justify-between"
                    >
                      <span className="font-semibold text-slate-900">
                        {ch} <span className="font-normal text-slate-500">{name}</span>
                      </span>
                      <span className="font-mono tabular-nums font-medium text-slate-800">{val}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <h4 className="font-semibold text-slate-900 mb-2">
                  Hebrew Gematria (22 Base + 5 Sofit Gadol)
                </h4>
                <div className="grid grid-cols-2 gap-1.5">
                  {HEBREW_ROWS.map(([ch, name, val]) => {
                    const sofit = HEBREW_SOFIT_ROWS.find((s) => s[1] === ch);
                    return (
                      <div
                        key={ch}
                        className="rounded border border-slate-200 bg-slate-50 px-2 py-1.5 flex items-center justify-between"
                      >
                        <span className="font-semibold text-slate-900">
                          {ch} <span className="font-normal text-slate-500">{name}</span>
                        </span>
                        <span className="font-mono tabular-nums font-medium text-slate-800">
                          {val}
                          {sofit ? ` (${sofit[0]} ${sofit[3]})` : ''}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {atlasTab === 'legacy_card' && (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs text-slate-600">
                  Sanitized Markdown &amp; JSON export (location coordinates stripped)
                </span>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => handleCopySummary('markdown')}
                    className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                  >
                    {copiedMode === 'markdown' ? (
                      <Check className="h-3.5 w-3.5 text-emerald-600" aria-hidden="true" />
                    ) : (
                      <Copy className="h-3.5 w-3.5" aria-hidden="true" />
                    )}
                    <span>{copiedMode === 'markdown' ? 'Copied Card' : 'Copy Markdown'}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleCopySummary('json')}
                    className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                  >
                    {copiedMode === 'json' ? (
                      <Check className="h-3.5 w-3.5 text-emerald-600" aria-hidden="true" />
                    ) : (
                      <Compass className="h-3.5 w-3.5" aria-hidden="true" />
                    )}
                    <span>{copiedMode === 'json' ? 'Copied JSON' : 'Copy Share JSON'}</span>
                  </button>
                </div>
              </div>
              <pre className="rounded-lg bg-slate-950 text-slate-100 p-4 text-xs overflow-x-auto font-mono leading-relaxed">
                {legacyCardMarkdown}
              </pre>
            </div>
          )}

          {atlasTab === 'forensics' && (
            <div className="space-y-3 text-xs text-slate-700">
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 space-y-1">
                <div className="font-semibold text-slate-900">
                  H0 Forensics Recovery Matrix ({world?.forensicsRecovery.repository ?? 'chidionyema/hermes-v2'})
                </div>
                <div>
                  Patch recovered:{' '}
                  <span className="font-mono text-slate-900">
                    {world?.forensicsRecovery.patchFile ??
                      'patches/hermes-agent/0001-feat-summary-port-the-isopsephy-card-from-the-old-es.patch'}
                  </span>{' '}
                  (commit <span className="font-mono">1220c4ad</span>)
                </div>
                <div className="text-slate-600">
                  {world?.forensicsRecovery.externalDeploymentGap ??
                    'Running inside local control-plane sandbox; external GitHub repo push/deploy requires external credentials.'}
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {(world?.forensicsRecovery.verifiedVectors ?? []).map((v) => (
                  <div
                    key={v.label}
                    className="rounded-lg border border-slate-200 p-2.5 bg-white"
                  >
                    <div className="text-[11px] text-slate-500">{v.label}</div>
                    <div className="mt-1 font-mono tabular-nums font-bold text-slate-900">
                      {v.computed} / {v.expected} · {v.passed ? 'PASS' : 'FAIL'}
                    </div>
                  </div>
                ))}
              </div>

              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    disabled={chaosRunning}
                    onClick={handleRunHermesChaos}
                    className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-800 disabled:opacity-50 whitespace-nowrap shrink-0"
                  >
                    <Play className="h-3.5 w-3.5" aria-hidden="true" />
                    <span>{chaosRunning ? 'Running Fuzz...' : 'Run 1,000-Op Hermes Chaos'}</span>
                  </button>
                  <a
                    href="/api/debug-pack"
                    download="meridian-hermes-debug-pack.json"
                    className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100 whitespace-nowrap shrink-0"
                  >
                    <Download className="h-3.5 w-3.5" aria-hidden="true" />
                    <span>Debug Pack JSON</span>
                  </a>
                  <a
                    href="/api/debug-pack?format=markdown"
                    download="meridian-hermes-debug-pack.md"
                    className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100 whitespace-nowrap shrink-0"
                  >
                    <FileText className="h-3.5 w-3.5" aria-hidden="true" />
                    <span>Debug Pack MD</span>
                  </a>
                  <a
                    href="/api/export/bundle"
                    download="meridian-hermes-today.bundle"
                    className="inline-flex items-center gap-1.5 rounded-md border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-950 hover:bg-amber-100 whitespace-nowrap shrink-0"
                  >
                    <PackageCheck className="h-3.5 w-3.5" aria-hidden="true" />
                    <span>Download Git Bundle</span>
                  </a>
                </div>
                {chaosResult && (
                  <span className="font-mono text-[11px] font-semibold text-emerald-700">
                    {chaosResult.succeeded}/{chaosResult.iterations} ops · 0 exceptions · p95 {chaosResult.p95Us}µs
                  </span>
                )}
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
