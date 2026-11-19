import { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  FileText,
  Lock,
  ShieldAlert,
  Unlock,
} from 'lucide-react';
import {
  build231GatesMatrix,
  evaluateGatePair,
  OLAMOT_WORLDS,
  OlamotScale,
  QLIPHOTH_REGISTRY,
  QliphahId,
  THREE_VEILS,
  verifyThreeKeyNonCollusion,
} from '../engine/codexCrescendo';
import { evaluateCrescendoGoLiveSignOff } from '../engine/crescendoThreeWayUnion';
import { TREE_PATHS } from '../engine/hermesTreeCatalog';

interface CodexCrescendoPanelProps {
  olamScale: OlamotScale;
  onSelectOlamScale: (scale: OlamotScale) => void;
  injectedQliphah: QliphahId;
  onSelectQliphah: (id: QliphahId) => void;
  keyBinah: string;
  keyChesed: string;
  keyMalkuth: string;
  onChangeKeys: (next: { keyBinah: string; keyChesed: string; keyMalkuth: string }) => void;
}

export function CodexCrescendoPanel({
  olamScale,
  onSelectOlamScale,
  injectedQliphah,
  onSelectQliphah,
  keyBinah,
  keyChesed,
  keyMalkuth,
  onChangeKeys,
}: CodexCrescendoPanelProps) {
  const [gateFilter, setGateFilter] = useState<'blocked' | 'compatible'>('blocked');
  const [testPathA, setTestPathA] = useState<number>(14);
  const [testPathB, setTestPathB] = useState<number>(32);
  const [repoMeta, setRepoMeta] = useState<{ headSha: string; bundleSha256: string | null } | null>(
    null
  );

  useEffect(() => {
    let cancelled = false;
    void fetch('/api/crescendo/signoff')
      .then((r) => (r.ok ? r.json() : null))
      .then((data: { headSha?: string; bundleSha256?: string | null } | null) => {
        if (!cancelled && data?.headSha) {
          setRepoMeta({
            headSha: data.headSha,
            bundleSha256: data.bundleSha256 ?? null,
          });
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const matrix = useMemo(() => build231GatesMatrix(), []);
  const pairEval = useMemo(() => evaluateGatePair(testPathA, testPathB), [testPathA, testPathB]);

  const threeKeyVerdict = useMemo(
    () =>
      verifyThreeKeyNonCollusion({
        keyBinah,
        keyChesed,
        keyMalkuth,
        merkleRoot: `meridian.crescendo.v1:${repoMeta?.headSha?.slice(0, 12) ?? '8b6d23f'}`,
      }),
    [keyBinah, keyChesed, keyMalkuth, repoMeta?.headSha]
  );

  const goLiveSignOff = useMemo(
    () =>
      evaluateCrescendoGoLiveSignOff({
        headSha: repoMeta?.headSha,
        bundleSha256: repoMeta?.bundleSha256,
        keyBinah,
        keyChesed,
        keyMalkuth,
        injectedQliphah,
      }),
    [repoMeta?.headSha, repoMeta?.bundleSha256, keyBinah, keyChesed, keyMalkuth, injectedQliphah]
  );

  const visibleGates = useMemo(() => {
    if (gateFilter === 'blocked') return matrix.blockedGates;
    return matrix.allGates.filter((g) => g.compatible).slice(0, 18);
  }, [gateFilter, matrix]);

  const activeWorld = OLAMOT_WORLDS.find((w) => w.id === olamScale) ?? OLAMOT_WORLDS[0];

  return (
    <div className="space-y-4 text-xs text-slate-700 min-w-0">
      {/* P0 Crescendo 3-Way Union & Go-Live Sign-Off Gate */}
      <section
        aria-label="Crescendo 3-Way Union and Go-Live Sign-Off"
        className="scroll-mt-20 rounded-lg border border-amber-300 bg-amber-50/60 p-4 space-y-3 min-w-0"
      >
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 min-w-0">
          <div className="space-y-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1 rounded bg-slate-900 px-2 py-0.5 font-mono text-[11px] font-bold text-amber-300 shrink-0">
                <ShieldAlert className="h-3.5 w-3.5" aria-hidden="true" />
                CRESCENDO GO-LIVE: {goLiveSignOff.overallDecision}
              </span>
              <span className="font-mono text-[11px] text-slate-700 [overflow-wrap:anywhere]">
                Route: <strong>{goLiveSignOff.declaredEndUserRoute}</strong> →{' '}
                {goLiveSignOff.resolvedTabId} · Custody:{' '}
                <strong>{goLiveSignOff.linkedObligationId}</strong> (0 disconnected tickets)
              </span>
            </div>
            <div className="font-semibold text-slate-900 text-sm [overflow-wrap:anywhere]">
              {goLiveSignOff.decisionHeadline}
            </div>
            <p className="text-[11px] text-slate-700 leading-relaxed [overflow-wrap:anywhere]">
              Local gates verified: <strong>{goLiveSignOff.localGatesPassed}/3</strong> (
              <code className="font-mono">GL-01</code> sign-off file,{' '}
              <code className="font-mono">GL-02</code> 231-Gate + Three-Key seal,{' '}
              <code className="font-mono">GL-03</code> <code className="font-mono">/crescendo</code>{' '}
              route + static <code className="font-mono">dist/api/export/bundle</code>). External
              production gates: <strong>{goLiveSignOff.externalGatesPassed}/3</strong> (
              <code className="font-mono">GL-04..GL-06</code> held{' '}
              <code className="font-mono">NO-GO</code> per Rego{' '}
              <code className="font-mono">R-010</code> until fleet remote sync, deployed revision
              HTTP 200 &amp; independent Key-C browser witness).
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <a
              href="/MERIDIAN_CRESCENDO_3WAY_UNION_AND_GO_LIVE_SIGN_OFF.md"
              download="MERIDIAN_CRESCENDO_3WAY_UNION_AND_GO_LIVE_SIGN_OFF.md"
              className="inline-flex items-center gap-1.5 rounded border border-slate-900 bg-slate-900 px-3 py-1.5 text-[11px] font-semibold text-white hover:bg-slate-800 whitespace-nowrap"
            >
              <FileText className="h-3.5 w-3.5 text-amber-300" aria-hidden="true" />
              Download Sign-Off (.md)
            </a>
            <a
              href="/api/export/bundle"
              download="meridian-hermes-today.bundle"
              className="inline-flex items-center gap-1.5 rounded border border-slate-300 bg-white px-3 py-1.5 text-[11px] font-semibold text-slate-800 hover:bg-slate-100 whitespace-nowrap"
            >
              <Download className="h-3.5 w-3.5 text-slate-600" aria-hidden="true" />
              Download Git Bundle
            </a>
          </div>
        </div>

        {/* 3 Source Streams */}
        <div className="grid grid-cols-1 gap-2">
          {goLiveSignOff.streams.map((stream) => (
            <div
              key={stream.id}
              className="rounded border border-slate-200 bg-white p-2.5 space-y-1 min-w-0"
            >
              <div className="flex flex-wrap items-center justify-between gap-1.5">
                <span className="font-semibold text-slate-900 [overflow-wrap:anywhere]">
                  {stream.label}
                </span>
                <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-slate-800 [overflow-wrap:anywhere]">
                  {stream.status}
                </span>
              </div>
              <div className="font-mono text-[10px] text-slate-500 [overflow-wrap:anywhere]">
                {stream.authorityRepo}
              </div>
              <div className="text-[11px] text-slate-600 [overflow-wrap:anywhere]">
                {stream.evidenceSummary}
              </div>
            </div>
          ))}
        </div>

        {/* 6 Go-Live Gates */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {goLiveSignOff.gates.map((gate) => {
            const isLocalPass =
              gate.status === 'VERIFIED_LOCAL' || gate.status === 'VERIFIED_EXTERNAL';
            const isFailed = gate.status === 'FAILED';
            return (
              <div
                key={gate.gateId}
                className={`rounded border px-3 py-2 space-y-1 min-w-0 ${
                  isFailed
                    ? 'border-red-300 bg-red-50 text-red-950'
                    : isLocalPass
                      ? 'border-emerald-200 bg-emerald-50/70 text-slate-900'
                      : 'border-amber-200 bg-white text-slate-900'
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-1 font-mono text-[10px] font-bold">
                  <span>{gate.gateId}</span>
                  <span className="[overflow-wrap:anywhere]">{gate.status}</span>
                </div>
                <div className="font-semibold text-[11px] leading-snug [overflow-wrap:anywhere]">
                  {gate.title}
                </div>
                <div className="text-[10px] text-slate-600 leading-snug [overflow-wrap:anywhere]">
                  {gate.evidence}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Four Qabalistic Worlds & Three Veils Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3.5 space-y-2">
          <div className="font-semibold text-slate-900">
            Four Worlds Scale · {activeWorld.worldName} ({activeWorld.tetragrammaton})
          </div>
          <div className="text-[11px] text-slate-600">
            {activeWorld.scaleName} · {activeWorld.meridianStratum} · {activeWorld.shaderPhysics}
          </div>
          <div className="flex flex-wrap gap-1.5 pt-1">
            {OLAMOT_WORLDS.map((w) => (
              <button
                key={w.id}
                type="button"
                onClick={() => onSelectOlamScale(w.id)}
                className={`rounded px-2.5 py-1 text-[11px] font-medium border transition-colors whitespace-nowrap shrink-0 ${
                  olamScale === w.id
                    ? 'bg-slate-900 text-white border-slate-900'
                    : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
                }`}
              >
                {w.worldName} ({w.scaleName.split(' ')[0]})
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3.5 space-y-1.5">
          <div className="font-semibold text-slate-900">
            Three Horizontal Veils (Zero-Mutation Boundaries)
          </div>
          {THREE_VEILS.map((v) => (
            <div key={v.id} className="text-[11px] leading-snug">
              <strong className="text-slate-800">{v.name}:</strong>{' '}
              <span className="text-slate-600">{v.airlockInvariant}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Three-Key Non-Collusion Theorem (Veil of Qesheth / Nehemoth) */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="font-semibold text-slate-900">
              Three-Key Non-Collusion Theorem (Veil of Qesheth Airlock)
            </div>
            <div className="text-[11px] text-slate-500">
              Malkuth (10) stays dark unless Key_Binah, Key_Chesed, and Key_Malkuth are 3 distinct keys.
            </div>
          </div>
          <div className="flex flex-wrap gap-1.5">
            <button
              type="button"
              onClick={() =>
                onChangeKeys({
                  keyBinah: 'keyA_binah_oracle_ed25519',
                  keyChesed: 'keyB_chesed_exec_ed25519',
                  keyMalkuth: 'keyC_malkuth_witness_ed25519',
                })
              }
              className="rounded border border-slate-300 bg-slate-50 px-2.5 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-100 whitespace-nowrap"
            >
              Restore 3 Independent Keys
            </button>
            <button
              type="button"
              onClick={() =>
                onChangeKeys({
                  keyBinah: 'keyB_chesed_exec_ed25519',
                  keyChesed: 'keyB_chesed_exec_ed25519',
                  keyMalkuth: 'keyB_chesed_exec_ed25519',
                })
              }
              className="rounded border border-red-300 bg-red-50 px-2.5 py-1 text-[11px] font-medium text-red-800 hover:bg-red-100 whitespace-nowrap"
            >
              Simulate Nehemoth Self-Sign
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          <label className="block space-y-1">
            <span className="text-[11px] font-medium text-slate-600">Key A · Binah Oracle</span>
            <input
              type="text"
              value={keyBinah}
              onChange={(e) => onChangeKeys({ keyBinah: e.target.value, keyChesed, keyMalkuth })}
              className="w-full rounded border border-slate-300 bg-slate-50 px-2.5 py-1 font-mono text-[11px] text-slate-900"
            />
          </label>
          <label className="block space-y-1">
            <span className="text-[11px] font-medium text-slate-600">Key B · Chesed Executor</span>
            <input
              type="text"
              value={keyChesed}
              onChange={(e) => onChangeKeys({ keyBinah, keyChesed: e.target.value, keyMalkuth })}
              className="w-full rounded border border-slate-300 bg-slate-50 px-2.5 py-1 font-mono text-[11px] text-slate-900"
            />
          </label>
          <label className="block space-y-1">
            <span className="text-[11px] font-medium text-slate-600">Key C · Malkuth Witness</span>
            <input
              type="text"
              value={keyMalkuth}
              onChange={(e) => onChangeKeys({ keyBinah, keyChesed, keyMalkuth: e.target.value })}
              className="w-full rounded border border-slate-300 bg-slate-50 px-2.5 py-1 font-mono text-[11px] text-slate-900"
            />
          </label>
        </div>

        <div
          className={`rounded-md border px-3 py-2 flex items-start gap-2 ${
            threeKeyVerdict.malkuthIlluminated
              ? 'border-emerald-300 bg-emerald-50 text-emerald-950'
              : 'border-red-300 bg-red-50 text-red-950'
          }`}
        >
          {threeKeyVerdict.malkuthIlluminated ? (
            <Unlock className="h-4 w-4 text-emerald-700 shrink-0 mt-0.5" aria-hidden="true" />
          ) : (
            <Lock className="h-4 w-4 text-red-700 shrink-0 mt-0.5" aria-hidden="true" />
          )}
          <div className="min-w-0">
            <div className="font-semibold">
              {threeKeyVerdict.malkuthIlluminated ? 'MALKUTH ILLUMINATED (3/3 Distinct Keys)' : 'QESHETH LOCKED (Collusion / Missing Key)'}
            </div>
            <div className="text-[11px]">{threeKeyVerdict.reason}</div>
            {threeKeyVerdict.malkuthIlluminated && (
              <div className="mt-1 font-mono text-[10px] text-emerald-800 truncate">
                {threeKeyVerdict.sigBinah} · {threeKeyVerdict.sigChesed} · {threeKeyVerdict.sigMalkuth}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 231 Gates Matrix + Live Syzygy Pair Evaluator */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="font-semibold text-slate-900">
              Sefer Yetzirah 231 Gates Commutative Matrix ({matrix.totalGates} Pairs)
            </div>
            <div className="text-[11px] text-slate-500">
              {matrix.compatibleCount} commutative transitions · {matrix.blockedCount} algebraically rejected deadlocks
            </div>
          </div>
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-md">
            <button
              type="button"
              onClick={() => setGateFilter('blocked')}
              className={`px-2.5 py-1 rounded text-[11px] font-medium ${
                gateFilter === 'blocked' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600'
              }`}
            >
              Rejected ({matrix.blockedCount})
            </button>
            <button
              type="button"
              onClick={() => setGateFilter('compatible')}
              className={`px-2.5 py-1 rounded text-[11px] font-medium ${
                gateFilter === 'compatible' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600'
              }`}
            >
              Compatible Sample ({matrix.compatibleCount})
            </button>
          </div>
        </div>

        {/* Live Gate Pair Tester */}
        <div className="flex flex-wrap items-center gap-2 rounded-md bg-slate-50 border border-slate-200 p-2.5">
          <span className="text-[11px] font-medium text-slate-700">Test Concurrent Pair:</span>
          <select
            aria-label="First path in gate pair"
            value={testPathA}
            onChange={(e) => setTestPathA(Number(e.target.value))}
            className="rounded border border-slate-300 bg-white px-2 py-1 text-[11px]"
          >
            {TREE_PATHS.map((p) => (
              <option key={p.number} value={p.number}>
                Path {p.number} · {p.letterName}
              </option>
            ))}
          </select>
          <span aria-hidden="true">×</span>
          <select
            aria-label="Second path in gate pair"
            value={testPathB}
            onChange={(e) => setTestPathB(Number(e.target.value))}
            className="rounded border border-slate-300 bg-white px-2 py-1 text-[11px]"
          >
            {TREE_PATHS.map((p) => (
              <option key={p.number} value={p.number}>
                Path {p.number} · {p.letterName}
              </option>
            ))}
          </select>
          <span
            className={`inline-flex items-center gap-1 font-mono text-[11px] font-semibold ${
              pairEval.compatible ? 'text-emerald-700' : 'text-red-700'
            }`}
          >
            {pairEval.compatible ? (
              <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
            ) : (
              <ShieldAlert className="h-3.5 w-3.5" aria-hidden="true" />
            )}
            {pairEval.compatible ? 'M231 = 1 (ALLOWED)' : 'M231 = 0 (REJECTED)'}
          </span>
          <span className="text-[11px] text-slate-600">{pairEval.reason}</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-44 overflow-y-auto pr-1">
          {visibleGates.map((g) => (
            <div
              key={`${g.pathA}-${g.pathB}`}
              className={`rounded border px-2.5 py-1.5 text-[11px] ${
                g.compatible ? 'border-slate-200 bg-slate-50' : 'border-red-200 bg-red-50/70'
              }`}
            >
              <div className="font-mono font-semibold text-slate-900">
                Gate ({g.pathA}, {g.pathB}) · {g.compatible ? 'PASS' : 'BLOCKED'}
              </div>
              <div className="text-slate-600 mt-0.5">{g.reason}</div>
            </div>
          ))}
        </div>
      </div>

      {/* 10 Qliphoth Registry & Interactive Fault Injector */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-2.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="font-semibold text-slate-900">
              Sitra Achra · 10 Qliphoth &amp; Mechanical Exorcisms
            </div>
            <div className="text-[11px] text-slate-500">
              Click any Qliphah to trigger chromatic fracture on the Living Tree SVG above.
            </div>
          </div>
          {injectedQliphah !== 'none' && (
            <button
              type="button"
              onClick={() => onSelectQliphah('none')}
              className="rounded border border-emerald-300 bg-emerald-50 px-2.5 py-1 text-[11px] font-medium text-emerald-900 hover:bg-emerald-100"
            >
              Heal Active Fracture
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-56 overflow-y-auto pr-1">
          {QLIPHOTH_REGISTRY.map((q) => {
            const active = injectedQliphah === q.id;
            return (
              <button
                key={q.id}
                type="button"
                onClick={() => onSelectQliphah(active ? 'none' : q.id)}
                className={`text-left rounded-md border p-2.5 transition-colors ${
                  active
                    ? 'border-red-500 bg-red-50 text-red-950'
                    : 'border-slate-200 bg-slate-50 hover:bg-slate-100'
                }`}
              >
                <div className="flex items-center justify-between gap-2 font-semibold text-slate-900">
                  <span className="flex items-center gap-1.5">
                    {active && <AlertTriangle className="h-3.5 w-3.5 text-red-600" aria-hidden="true" />}
                    {q.number}. {q.name} ({q.hebrew})
                  </span>
                  <span className="font-mono text-[10px] text-slate-500">
                    Path {q.fracturedPathNumber}
                  </span>
                </div>
                <div className="text-[11px] text-slate-700 mt-0.5">{q.byzantineFailureMode}</div>
                <div className="text-[10px] text-slate-500 mt-0.5">
                  Exorcism: {q.mechanicalExorcism}
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
