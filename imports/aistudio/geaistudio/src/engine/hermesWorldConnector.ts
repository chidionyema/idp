/**
 * World Resonance 3-Layer Connector (Observed -> Calculated -> Interpreted).
 * Commercial hardening:
 *   - Bounded 64-entry LRU cache (prevents memory exhaustion under coordinate fuzzing)
 *   - Strict lat/lon validation rejecting NaN/Infinity/out-of-bounds
 *   - Upstream Circuit Breaker (CLOSED -> OPEN for 60s after 3 consecutive failures -> HALF_OPEN)
 *   - Graceful stale-cache and offline astronomical ephemeris fallback
 */

import { computeCanonReadings, scoreGreekIsopsephy, scoreHebrewGematria } from './hermesCipherEngine';
import {
  AstronomicalEphemeris,
  computeAstronomicalEphemeris,
  DailyChallengeSummary,
  getDailyChallengeForDate,
  getUtcDateString,
} from './hermesTreeCatalog';

export type SanctuaryPlaceId = 'london' | 'jerusalem' | 'alexandria' | 'tokyo' | 'custom';

export interface SanctuaryPlace {
  id: SanctuaryPlaceId;
  label: string;
  regionLabel: string;
  latitudeDeg: number; // coarse 2 decimal places max
  longitudeDeg: number;
  timezone: string;
  historicalNote: string;
}

export const SANCTUARY_PLACES: ReadonlyArray<SanctuaryPlace> = [
  {
    id: 'london',
    label: 'London Sanctuary',
    regionLabel: 'London, United Kingdom',
    latitudeDeg: 51.51,
    longitudeDeg: -0.13,
    timezone: 'Europe/London',
    historicalNote: 'Golden Dawn Hermetic manuscript archive origin (1888)',
  },
  {
    id: 'alexandria',
    label: 'Alexandria Library Observatory',
    regionLabel: 'Alexandria, Egypt',
    latitudeDeg: 31.2,
    longitudeDeg: 29.92,
    timezone: 'Africa/Cairo',
    historicalNote: 'Hellenistic isopsephy & Corpus Hermeticum classical cradle',
  },
  {
    id: 'jerusalem',
    label: 'Jerusalem Meridian',
    regionLabel: 'Jerusalem',
    latitudeDeg: 31.77,
    longitudeDeg: 35.21,
    timezone: 'Asia/Jerusalem',
    historicalNote: 'Safed / Lurianic & Sefer Yetzirah Hebrew gematria lineage',
  },
  {
    id: 'tokyo',
    label: 'Tokyo Dawn Horizon',
    regionLabel: 'Tokyo, Japan',
    latitudeDeg: 35.68,
    longitudeDeg: 139.69,
    timezone: 'Asia/Tokyo',
    historicalNote: 'Pacific meridian astronomical test bench',
  },
];

export type WeatherObservationStatus = 'LIVE' | 'CACHED' | 'OFFLINE_FALLBACK';
export type CircuitState = 'CLOSED' | 'OPEN' | 'HALF_OPEN';

export interface ObservedWeatherLayer {
  status: WeatherObservationStatus;
  circuitState: CircuitState;
  consecutiveFailures: number;
  dataKind: 'interpolated_grid_current' | 'fallback_astronomical_only';
  sourceName: string;
  sourceUrl: string;
  license: string;
  place: SanctuaryPlace;
  observedAt: string | null;
  fetchedAt: string;
  freshnessSec: number;
  ttlSec: number;
  isStale: boolean;
  temperatureC: number | null;
  precipitationMm: number | null;
  windSpeedKmh: number | null;
  cloudCoverPct: number | null;
  weatherCode: number | null;
  weatherSummary: string;
  isDay: boolean | null;
  errorReason: string | null;
}

export type AtmosphereMode = 'RAIN_WATER' | 'WIND_AIR' | 'SOLAR_FIRE' | 'NIGHT_AETHER';

export interface InterpretedResonanceLayer {
  atmosphereMode: AtmosphereMode;
  elementAffinity: 'Water' | 'Air' | 'Fire' | 'Earth' | 'Aether';
  dominantPathLetter: string;
  dominantPathNumber: number;
  visualMoodTitle: string;
  visualMoodDescription: string;
  themedPromptWords: string[];
  nonCausalNotice: string;
}

export interface WorldResonanceSnapshot {
  observed: ObservedWeatherLayer;
  calculated: {
    ephemeris: AstronomicalEphemeris;
    dailyChallenge: DailyChallengeSummary;
    canonSize: number;
  };
  interpreted: InterpretedResonanceLayer;
  forensicsRecovery: {
    repository: string;
    recoveredCommitSha: string;
    patchFile: string;
    issueSpec: string;
    verifiedVectors: Array<{ label: string; expected: number; computed: number; passed: boolean }>;
    externalDeploymentGap: string;
  };
}

export const WORLD_CACHE_TTL_MS = 5 * 60 * 1000;
export const MAX_WORLD_CACHE_ENTRIES = 64;
export const CIRCUIT_FAILURE_THRESHOLD = 3;
export const CIRCUIT_COOLDOWN_MS = 60 * 1000;

export interface WorldConnectorRuntime {
  cacheByKey: Map<string, { fetchedMs: number; observed: ObservedWeatherLayer }>;
  consecutiveFailures: number;
  circuitOpenUntilMs: number;
}

export function createWorldConnectorRuntime(): WorldConnectorRuntime {
  return {
    cacheByKey: new Map(),
    consecutiveFailures: 0,
    circuitOpenUntilMs: 0,
  };
}

const defaultRuntime = createWorldConnectorRuntime();

function setCacheBounded(
  runtime: WorldConnectorRuntime,
  key: string,
  entry: { fetchedMs: number; observed: ObservedWeatherLayer }
) {
  if (runtime.cacheByKey.has(key)) {
    runtime.cacheByKey.delete(key);
  }
  while (runtime.cacheByKey.size >= MAX_WORLD_CACHE_ENTRIES) {
    const oldestKey = runtime.cacheByKey.keys().next().value;
    if (oldestKey === undefined) break;
    runtime.cacheByKey.delete(oldestKey);
  }
  runtime.cacheByKey.set(key, entry);
}

export function validateCoordinates(lat?: number, lon?: number): { ok: boolean; error?: string } {
  if (lat === undefined && lon === undefined) return { ok: true };
  if (typeof lat !== 'number' || typeof lon !== 'number' || !Number.isFinite(lat) || !Number.isFinite(lon)) {
    return { ok: false, error: 'Coordinates must be finite numbers' };
  }
  if (lat < -90 || lat > 90) {
    return { ok: false, error: 'Latitude must fall within [-90, 90]' };
  }
  if (lon < -180 || lon > 180) {
    return { ok: false, error: 'Longitude must fall within [-180, 180]' };
  }
  return { ok: true };
}

function decodeWmoWeatherCode(code: number | null): string {
  if (code === null) return 'Observation unavailable (running pure ephemeris mode)';
  if (code === 0) return 'Clear sky';
  if (code <= 3) return 'Partly cloudy';
  if (code === 45 || code === 48) return 'Mist / fog';
  if (code >= 51 && code <= 67) return 'Rain / drizzle';
  if (code >= 71 && code <= 77) return 'Snowfall';
  if (code >= 80 && code <= 82) return 'Rain showers';
  if (code >= 95) return 'Thunderstorm';
  return `WMO code ${code}`;
}

export function deriveInterpretedLayer(
  observed: ObservedWeatherLayer,
  ephemeris: AstronomicalEphemeris
): InterpretedResonanceLayer {
  const precip = observed.precipitationMm ?? 0;
  const wind = observed.windSpeedKmh ?? 0;
  const isDay = observed.isDay ?? ephemeris.isAstronomicalDay;
  const wmo = observed.weatherCode ?? 0;

  if (precip > 0.1 || (wmo >= 51 && wmo <= 82) || wmo >= 95) {
    return {
      atmosphereMode: 'RAIN_WATER',
      elementAffinity: 'Water',
      dominantPathLetter: 'מ',
      dominantPathNumber: 23,
      visualMoodTitle: 'Path 23 · Mem (Water) Resonance',
      visualMoodDescription:
        'Observed rainfall triggers cool precipitation filaments across the sanctum canopy and highlights Path 23 (מ · Water · Geburah↔Hod) & water-themed lexemes.',
      themedPromptWords: ['אל', 'בינה', 'Μίθρας', 'ψυχή'],
      nonCausalNotice:
        'Symbolic visual resonance mapped deterministically from observed weather; carries zero causal or predictive claim.',
    };
  }

  if (wind >= 22) {
    return {
      atmosphereMode: 'WIND_AIR',
      elementAffinity: 'Air',
      dominantPathLetter: 'א',
      dominantPathNumber: 11,
      visualMoodTitle: 'Path 11 · Aleph (Air / Breath) Resonance',
      visualMoodDescription:
        'Brisk wind velocity activates laminar drift vectors along Path 11 (א · Air · Kether↔Chokmah) and equilibrating middle-pillar lines.',
      themedPromptWords: ['Λόγος', 'ἀρχή', 'אהיה', 'רוח'],
      nonCausalNotice:
        'Symbolic visual resonance mapped deterministically from observed wind telemetry; carries zero causal or predictive claim.',
    };
  }

  if (isDay) {
    return {
      atmosphereMode: 'SOLAR_FIRE',
      elementAffinity: 'Fire',
      dominantPathLetter: 'ר',
      dominantPathNumber: 30,
      visualMoodTitle: 'Tiphareth · Path 30 (Sol / Illumination) Resonance',
      visualMoodDescription:
        'Daylight solar elevation warms Tiphareth (6 · Sol) and Shin/Resh gold harmonics across the Observatory dome.',
      themedPromptWords: ['Ἰησοῦς', 'Ἀβρασάξ', 'תפארת', 'אמת'],
      nonCausalNotice:
        'Symbolic visual resonance mapped deterministically from solar altitude & daylight flag; carries zero causal or predictive claim.',
    };
  }

  return {
    atmosphereMode: 'NIGHT_AETHER',
    elementAffinity: 'Aether',
    dominantPathLetter: 'ג',
    dominantPathNumber: 13,
    visualMoodTitle: `Yesod / Gimel · ${ephemeris.lunarPhaseName} (${ephemeris.lunarIlluminationPct}%)`,
    visualMoodDescription:
      'Nocturnal astronomical window illuminates the Lunar Path of Gimel (13 · Luna) and Yesod (9 · Foundation) against deep celestial indigo.',
    themedPromptWords: ['χξϛ', 'ἀγάπη', 'חכמה', 'שלום'],
    nonCausalNotice:
      'Symbolic visual resonance mapped deterministically from nocturnal phase geometry; carries zero causal or predictive claim.',
  };
}

export function resolveSanctuaryPlace(query: {
  placeId?: string;
  lat?: number;
  lon?: number;
}): SanctuaryPlace {
  if (query.placeId && query.placeId !== 'custom') {
    const found = SANCTUARY_PLACES.find((p) => p.id === query.placeId);
    if (found) return found;
  }
  if (
    typeof query.lat === 'number' &&
    typeof query.lon === 'number' &&
    Number.isFinite(query.lat) &&
    Number.isFinite(query.lon)
  ) {
    // Enforce coarse 2-decimal precision for visitor privacy
    const lat = Number(Math.max(-90, Math.min(90, query.lat)).toFixed(2));
    const lon = Number(Math.max(-180, Math.min(180, query.lon)).toFixed(2));
    return {
      id: 'custom',
      label: `Custom Coordinates (${lat}°, ${lon}°)`,
      regionLabel: `${lat}°, ${lon}° (coarse-rounded)`,
      latitudeDeg: lat,
      longitudeDeg: lon,
      timezone: 'UTC',
      historicalNote: 'User-entered coarse coordinates (2-decimal privacy rounding)',
    };
  }
  return SANCTUARY_PLACES[0];
}

export async function fetchWorldResonanceSnapshot(options: {
  placeId?: string;
  lat?: number;
  lon?: number;
  forceOffline?: boolean;
  now?: Date;
  runtime?: WorldConnectorRuntime;
  fetchImpl?: typeof fetch;
  timeoutMs?: number;
} = {}): Promise<WorldResonanceSnapshot> {
  const now = options.now ?? new Date();
  const runtime = options.runtime ?? defaultRuntime;
  const doFetch = options.fetchImpl ?? fetch;
  const timeoutMs = options.timeoutMs ?? 3800;

  const place = resolveSanctuaryPlace({
    placeId: options.placeId,
    lat: options.lat,
    lon: options.lon,
  });
  const cacheKey = `${place.id}:${place.latitudeDeg}:${place.longitudeDeg}`;
  const ephemeris = computeAstronomicalEphemeris(now, place.latitudeDeg, place.longitudeDeg);
  const dailyChallenge = getDailyChallengeForDate(getUtcDateString(now));

  const currentCircuitState = (): CircuitState => {
    if (runtime.circuitOpenUntilMs > now.getTime()) return 'OPEN';
    if (runtime.consecutiveFailures >= CIRCUIT_FAILURE_THRESHOLD) return 'HALF_OPEN';
    return 'CLOSED';
  };

  let observed: ObservedWeatherLayer;

  if (options.forceOffline) {
    observed = {
      status: 'OFFLINE_FALLBACK',
      circuitState: currentCircuitState(),
      consecutiveFailures: runtime.consecutiveFailures,
      dataKind: 'fallback_astronomical_only',
      sourceName: 'Open-Meteo Weather API (bypassed — offline simulation)',
      sourceUrl: 'https://open-meteo.com/',
      license: 'CC BY 4.0',
      place,
      observedAt: null,
      fetchedAt: now.toISOString(),
      freshnessSec: 0,
      ttlSec: Math.round(WORLD_CACHE_TTL_MS / 1000),
      isStale: true,
      temperatureC: null,
      precipitationMm: null,
      windSpeedKmh: null,
      cloudCoverPct: null,
      weatherCode: null,
      weatherSummary: 'Offline sanctuary mode active — astronomical ephemeris remains live',
      isDay: null,
      errorReason: 'forceOffline flag active',
    };
  } else {
    const cached = runtime.cacheByKey.get(cacheKey);
    if (cached && now.getTime() - cached.fetchedMs < WORLD_CACHE_TTL_MS) {
      observed = {
        ...cached.observed,
        status: 'CACHED',
        circuitState: currentCircuitState(),
        consecutiveFailures: runtime.consecutiveFailures,
        freshnessSec: Math.round((now.getTime() - cached.fetchedMs) / 1000),
        isStale: false,
      };
    } else if (runtime.circuitOpenUntilMs > now.getTime()) {
      // Circuit is OPEN — fail-fast without blocking event loop on dead upstream
      observed = cached
        ? {
            ...cached.observed,
            status: 'CACHED',
            circuitState: 'OPEN',
            consecutiveFailures: runtime.consecutiveFailures,
            freshnessSec: Math.round((now.getTime() - cached.fetchedMs) / 1000),
            isStale: true,
            errorReason: 'Upstream circuit OPEN; serving stale cache without remote call',
          }
        : {
            status: 'OFFLINE_FALLBACK',
            circuitState: 'OPEN',
            consecutiveFailures: runtime.consecutiveFailures,
            dataKind: 'fallback_astronomical_only',
            sourceName: 'Open-Meteo Weather API (circuit open)',
            sourceUrl: 'https://open-meteo.com/',
            license: 'CC BY 4.0',
            place,
            observedAt: null,
            fetchedAt: now.toISOString(),
            freshnessSec: 0,
            ttlSec: Math.round(WORLD_CACHE_TTL_MS / 1000),
            isStale: true,
            temperatureC: null,
            precipitationMm: null,
            windSpeedKmh: null,
            cloudCoverPct: null,
            weatherCode: null,
            weatherSummary: 'Circuit open — offline astronomical ephemeris active',
            isDay: null,
            errorReason: 'Circuit open cooldown active',
          };
    } else {
      const apiUrl = `https://api.open-meteo.com/v1/forecast?latitude=${place.latitudeDeg}&longitude=${place.longitudeDeg}&current=temperature_2m,precipitation,cloud_cover,wind_speed_10m,weather_code,is_day&timezone=auto`;
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), timeoutMs);

      try {
        const res = await doFetch(apiUrl, { signal: controller.signal });
        if (!res.ok) {
          throw new Error(`Open-Meteo HTTP ${res.status}`);
        }
        const json = (await res.json()) as {
          current?: {
            time?: unknown;
            temperature_2m?: unknown;
            precipitation?: unknown;
            cloud_cover?: unknown;
            wind_speed_10m?: unknown;
            weather_code?: unknown;
            is_day?: unknown;
          };
        };
        const cur = json?.current;
        if (!cur || typeof cur.temperature_2m !== 'number' || !Number.isFinite(cur.temperature_2m)) {
          throw new Error('Malformed Open-Meteo payload: missing numeric temperature_2m');
        }

        // Healthy response resets circuit breaker
        runtime.consecutiveFailures = 0;
        runtime.circuitOpenUntilMs = 0;

        const weatherCode =
          typeof cur.weather_code === 'number' && Number.isFinite(cur.weather_code)
            ? cur.weather_code
            : null;
        const precip =
          typeof cur.precipitation === 'number' && Number.isFinite(cur.precipitation)
            ? Math.max(0, cur.precipitation)
            : 0;
        const wind =
          typeof cur.wind_speed_10m === 'number' && Number.isFinite(cur.wind_speed_10m)
            ? Math.max(0, cur.wind_speed_10m)
            : null;
        const cloud =
          typeof cur.cloud_cover === 'number' && Number.isFinite(cur.cloud_cover)
            ? Math.max(0, Math.min(100, cur.cloud_cover))
            : null;

        observed = {
          status: 'LIVE',
          circuitState: 'CLOSED',
          consecutiveFailures: 0,
          dataKind: 'interpolated_grid_current',
          sourceName: 'Open-Meteo Current Grid Feed',
          sourceUrl: 'https://api.open-meteo.com/',
          license: 'CC BY 4.0',
          place,
          observedAt: typeof cur.time === 'string' ? cur.time : now.toISOString(),
          fetchedAt: now.toISOString(),
          freshnessSec: 0,
          ttlSec: Math.round(WORLD_CACHE_TTL_MS / 1000),
          isStale: false,
          temperatureC: Number(cur.temperature_2m.toFixed(1)),
          precipitationMm: precip,
          windSpeedKmh: wind,
          cloudCoverPct: cloud,
          weatherCode,
          weatherSummary: decodeWmoWeatherCode(weatherCode),
          isDay: typeof cur.is_day === 'number' ? cur.is_day === 1 : null,
          errorReason: null,
        };
        setCacheBounded(runtime, cacheKey, { fetchedMs: now.getTime(), observed });
      } catch (err) {
        const reason = err instanceof Error ? err.message : 'Weather upstream unreachable';
        runtime.consecutiveFailures += 1;
        if (runtime.consecutiveFailures >= CIRCUIT_FAILURE_THRESHOLD) {
          runtime.circuitOpenUntilMs = now.getTime() + CIRCUIT_COOLDOWN_MS;
        }
        const stateAfterFail = currentCircuitState();

        if (cached) {
          observed = {
            ...cached.observed,
            status: 'CACHED',
            circuitState: stateAfterFail,
            consecutiveFailures: runtime.consecutiveFailures,
            isStale: true,
            freshnessSec: Math.round((now.getTime() - cached.fetchedMs) / 1000),
            errorReason: `Showing stale cached observation (${reason})`,
          };
        } else {
          observed = {
            status: 'OFFLINE_FALLBACK',
            circuitState: stateAfterFail,
            consecutiveFailures: runtime.consecutiveFailures,
            dataKind: 'fallback_astronomical_only',
            sourceName: 'Open-Meteo Weather API (unreachable)',
            sourceUrl: 'https://open-meteo.com/',
            license: 'CC BY 4.0',
            place,
            observedAt: null,
            fetchedAt: now.toISOString(),
            freshnessSec: 0,
            ttlSec: Math.round(WORLD_CACHE_TTL_MS / 1000),
            isStale: true,
            temperatureC: null,
            precipitationMm: null,
            windSpeedKmh: null,
            cloudCoverPct: null,
            weatherCode: null,
            weatherSummary: 'Weather feed offline — falling back cleanly to pure ephemeris',
            isDay: null,
            errorReason: reason,
          };
        }
      } finally {
        clearTimeout(timeout);
      }
    }
  }

  const interpreted = deriveInterpretedLayer(observed, ephemeris);
  const canon = computeCanonReadings();

  const iesous = scoreGreekIsopsephy('Ἰησοῦς').total;
  const beast = scoreGreekIsopsephy('χξϛ').total;
  const echad = scoreHebrewGematria('אחד').total;
  const malkuth = scoreHebrewGematria('מלכות').total;

  return {
    observed,
    calculated: {
      ephemeris,
      dailyChallenge,
      canonSize: canon.length,
    },
    interpreted,
    forensicsRecovery: {
      repository: 'chidionyema/hermes-v2 (public)',
      recoveredCommitSha: '1220c4ad246839f444d48acd94d7bc79a5c652b6',
      patchFile: 'patches/hermes-agent/0001-feat-summary-port-the-isopsephy-card-from-the-old-es.patch',
      issueSpec: 'chidionyema/hermes-v2#120',
      verifiedVectors: [
        { label: 'Ἰησοῦς (Greek)', expected: 888, computed: iesous, passed: iesous === 888 },
        { label: 'χξϛ (Greek 666)', expected: 666, computed: beast, passed: beast === 666 },
        { label: 'אחד (Hebrew)', expected: 13, computed: echad, passed: echad === 13 },
        { label: 'מלכות (Malkuth 496->10)', expected: 496, computed: malkuth, passed: malkuth === 496 },
      ],
      externalDeploymentGap:
        'Live sandbox runs HERMES: THE LIVING TREE on local Express + React control plane (port 3000); external GitHub PR merge / Fly.io production deployment on chidionyema/hermes-v2 requires maintainer repository credentials.',
    },
  };
}
