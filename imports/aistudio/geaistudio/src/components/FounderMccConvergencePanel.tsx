import { useMemo, useState } from 'react';
import { Play, RefreshCw, Send, ShieldAlert, Wifi, WifiOff } from 'lucide-react';
import type {
  CapabilityContract9Tuple,
  CertificationScenarioId,
  EnforcementPointId,
  ExistingEstateComponentRow,
  MccConvergenceSnapshot,
} from '../engine/meridianCapabilityCalculus';

export type MccPanelMode = 'unified_bus_mcc' | 'cert_suite_ltl' | 'reconciliation_mandate';

interface FounderMccConvergencePanelProps {
  mcc: MccConvergenceSnapshot;
  mode: MccPanelMode;
  busyKey: string | null;
  onInvokeAction: (payload: Record<string, unknown>, busyLabel: string) => Promise<void>;
}

const LIFECYCLE_STEPS: ReadonlyArray<{
  step: string;
  title: string;
  authority: string;
  rule: string;
}> = [
  {
    step: '01. DISCOVER',
    title: 'Capability & Dependency Discovery',
    authority: 'bin/capability-index · BEAST/SPIDER · bin/estate-context-compile',
    rule: 'Query existing capabilities, owners, dependencies, and fresh provenance-bound context before acting.',
  },
  {
    step: '02. ADMIT',
    title: 'Shared Bootstrap Gate (EP-A)',
    authority: 'QUAD Ed25519 · MCC-001 Contract · #8188 RFCE',
    rule: 'Admit(a,o) => D(a,o) & I(a) & C(a,o) & K(a,o). Missing prerequisites return 403 BLOCKED_ADMISSION.',
  },
  {
    step: '03. COMMUNICATE',
    title: 'Continuous Authenticated Transport (EP-B)',
    authority: 'bin/estate-fleet (#7481) · Hermes · Argon YIELD/1 · OMNIFLOW',
    rule: 'Distinguish DELIVERED != ACCEPTED != CLAIMED != EXECUTED != VERIFIED_EFFECT throughout execution.',
  },
  {
    step: '04. COLLABORATE',
    title: 'Specialist Match & Fenced Lease (EP-C)',
    authority: 'Legion · FLOW · Temporal · Capability Leases (#7787)',
    rule: 'Match capable specialist, prevent duplicate work, and grant single monotonic lease winner f_n.',
  },
  {
    step: '05. EXECUTE',
    title: 'Policy-Controlled Effect Doors (EP-D)',
    authority: 'Greenlane · QUAD Scopes · PennyD Ceilings',
    rule: 'Execute(a,x) => Admitted(a) & Authorized(a,x) & LeaseValid(a,x). Pause non-offline scopes on outage.',
  },
  {
    step: '06. VERIFY',
    title: 'Independent Outside-In Finality (EP-E)',
    authority: 'KARMA · Optimus · Genesis Evidence Projection',
    rule: 'No agent certifies its own outcome. Verified(o) <=> Postcondition(o) & IndependentEvidence(o).',
  },
  {
    step: '07. LEARN & PROPAGATE',
    title: 'Recursive Failure-Class Elimination',
    authority: 'RFCE (#8188) · KARMA · BEAST/SPIDER',
    rule: 'Compile verified root-cause fixes into inherited admission predicates K(a,o) for future sessions.',
  },
];

export function FounderMccConvergencePanel({
  mcc,
  mode,
  busyKey,
  onInvokeAction,
}: FounderMccConvergencePanelProps) {
  const [selectedDoorId, setSelectedDoorId] = useState<EnforcementPointId>('EP_A');
  const [selectedContractId, setSelectedContractId] = useState<string>(
    'cap.greenlane.patch_passkey_verifier'
  );
  const [selectedCompositionId, setSelectedCompositionId] = useState<string>(
    'CHAIN_BLOCKED_DEPLOY_ESCALATION'
  );
  const [originSurfaceId, setOriginSurfaceId] = useState<string>('APP_FOUNDER_IPHONE');
  const [targetCapId, setTargetCapId] = useState<string>('cap.greenlane.patch_passkey_verifier');
  const [intentInput, setIntentInput] = useState<string>(
    'Verify bin/idp-passkey-verify public-key path across Web, App & Console before PR #8175 approval'
  );
  const [inventoryFilter, setInventoryFilter] = useState<
    'ALL' | ExistingEstateComponentRow['operationalVerdict']
  >('ALL');

  const selectedDoor = useMemo(
    () =>
      mcc.enforcementPoints.find((ep) => ep.id === selectedDoorId) ?? mcc.enforcementPoints[0],
    [mcc.enforcementPoints, selectedDoorId]
  );

  const selectedContract: CapabilityContract9Tuple | undefined = useMemo(
    () =>
      mcc.contracts.find((c) => c.capabilityId === selectedContractId) ?? mcc.contracts[0],
    [mcc.contracts, selectedContractId]
  );

  const selectedComposition = useMemo(
    () =>
      mcc.compositionPresets.find((p) => p.presetId === selectedCompositionId) ??
      mcc.compositionPresets[0],
    [mcc.compositionPresets, selectedCompositionId]
  );

  const filteredInventory = useMemo(() => {
    if (inventoryFilter === 'ALL') return mcc.existingEstateInventory;
    return mcc.existingEstateInventory.filter(
      (item) => item.operationalVerdict === inventoryFilter
    );
  }, [mcc.existingEstateInventory, inventoryFilter]);

  const executableTargetContracts = useMemo(
    () => mcc.contracts.filter((c) => c.truthStatus === 'OPERATING'),
    [mcc.contracts]
  );

  const connectedSurfacesCount = mcc.surfaces.filter((s) => s.connected).length;
  const totalBufferedOutbox = mcc.surfaces.reduce((acc, s) => acc + s.bufferedOutboxCount, 0);
  const certPassedCount = mcc.certificationScenarios.filter((c) => c.passedInCiEngine).length;
  const invariantsPassedCount = mcc.registryInvariantChecks.filter((i) => i.passed).length;

  if (mode === 'cert_suite_ltl') {
    return (
      <div className="space-y-6">
        {/* 10/10 Estate-Wide Certification Suite */}
        <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3 border-b border-slate-100 pb-4">
            <div className="space-y-1">
              <div className="text-xs font-mono text-slate-500">
                <span>MCC-001 Section 6 Proof Suite</span>
                <span aria-hidden="true"> · </span>
                <span className="text-emerald-700 font-semibold tabular-nums">
                  {certPassedCount}/10 Connected to Local CI Engine
                </span>
                <span aria-hidden="true"> · </span>
                <span className="text-amber-700 font-semibold tabular-nums">
                  External Multi-Repo: 0/10 Unconnected
                </span>
              </div>
              <h3 className="text-base font-bold text-slate-900">
                01. Mandatory 10-Scenario Certification Suite (CERT_01 – CERT_10)
              </h3>
              <p className="text-xs text-slate-600">
                Replaces prose manual checklists with deterministic adversarial executions against{' '}
                <code className="font-mono">EP-A..EP-E</code>, recording contract versions,
                verifier identities, and SHA-256 trace receipts while keeping cross-repo status
                explicitly uninflated.
              </p>
            </div>

            <button
              type="button"
              disabled={busyKey !== null}
              onClick={() =>
                void onInvokeAction(
                  { action: 'run_all_cert_scenarios' },
                  'run_all_cert_scenarios'
                )
              }
              className="min-h-[40px] inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50 whitespace-nowrap shrink-0"
            >
              <Play className="h-3.5 w-3.5 text-cyan-400" aria-hidden="true" />
              {busyKey === 'run_all_cert_scenarios'
                ? 'Certifying 10 Scenarios…'
                : 'Run All 10 Certification Scenarios'}
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500">
                  <th className="py-2 pr-3 font-medium">Scenario</th>
                  <th className="py-2 px-3 font-medium">Gate</th>
                  <th className="py-2 px-3 font-medium">Local CI Engine</th>
                  <th className="py-2 px-3 font-medium">External Fleet</th>
                  <th className="py-2 px-3 font-medium">Observed Enforcement Outcome &amp; Verifier</th>
                  <th className="py-2 pl-3 font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {mcc.certificationScenarios.map((sc) => (
                  <tr key={sc.scenarioId} className="hover:bg-slate-50/80">
                    <td className="py-3 pr-3 align-top">
                      <div className="font-mono font-semibold text-slate-900 tabular-nums">
                        {sc.scenarioId} · #{sc.index}
                      </div>
                      <div className="font-medium text-slate-800 mt-0.5">{sc.title}</div>
                      <div className="text-slate-500 mt-0.5">{sc.adversarialSetup}</div>
                    </td>
                    <td className="py-3 px-3 align-top font-mono font-semibold text-slate-900 whitespace-nowrap">
                      {sc.enforcementPointTriggered}
                    </td>
                    <td className="py-3 px-3 align-top font-mono font-semibold whitespace-nowrap">
                      <span className={sc.passedInCiEngine ? 'text-emerald-700' : 'text-red-700'}>
                        {sc.passedInCiEngine ? 'PASS (CI)' : 'FAIL'}
                      </span>
                    </td>
                    <td className="py-3 px-3 align-top font-mono text-[11px] text-amber-700 whitespace-nowrap">
                      0/10 UNCONNECTED
                    </td>
                    <td className="py-3 px-3 align-top">
                      <div className="text-slate-800">{sc.observedOutcome}</div>
                      <div className="mt-1 font-mono text-[11px] text-slate-500 tabular-nums">
                        <span>{sc.contractVersionChecked}</span>
                        <span aria-hidden="true"> · </span>
                        <span>{sc.verifierIdentity}</span>
                        <span aria-hidden="true"> · </span>
                        <span>sha256:{sc.traceSha256.slice(0, 12)}</span>
                      </div>
                    </td>
                    <td className="py-3 pl-3 align-top text-right">
                      <button
                        type="button"
                        disabled={busyKey !== null}
                        aria-label={`Re-verify ${sc.scenarioId}: ${sc.title}`}
                        onClick={() =>
                          void onInvokeAction(
                            {
                              action: 'run_cert_scenario',
                              scenarioId: sc.scenarioId as CertificationScenarioId,
                            },
                            `cert:${sc.scenarioId}`
                          )
                        }
                        className="min-h-[36px] inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-800 hover:bg-slate-50 disabled:opacity-50 whitespace-nowrap"
                      >
                        <RefreshCw className="h-3 w-3" aria-hidden="true" />
                        Re-verify
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Bounded LTL State-Space Model Checker & #8188 RFCE Inheritance */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
          <section className="lg:col-span-8 bg-white border border-slate-200 rounded-xl p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  02. Bounded Temporal Logic (LTL) Safety &amp; Conditional Liveness Model Check
                </h3>
                <p className="text-xs text-slate-600">
                  Exhaustively explores crashes, retries, NATS partitions, duplicate deliveries,
                  and expired leases under explicit fairness assumptions.
                </p>
              </div>
              <div className="text-xs font-mono tabular-nums text-slate-700">
                <span>{mcc.ltlModelCheck.totalStatesExplored} states</span>
                <span aria-hidden="true"> · </span>
                <span>{mcc.ltlModelCheck.totalTransitionsChecked} transitions</span>
                <span aria-hidden="true"> · </span>
                <span className="text-emerald-700 font-semibold">
                  {mcc.ltlModelCheck.allPropertiesHoldUnderAssumptions
                    ? '0 counterexamples'
                    : 'VIOLATION'}
                </span>
              </div>
            </div>

            <div className="divide-y divide-slate-100">
              {mcc.ltlModelCheck.properties.map((prop) => (
                <div key={prop.id} className="py-3 space-y-1">
                  <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
                    <div>
                      <span className="font-semibold text-slate-900">{prop.id}</span>
                      <span aria-hidden="true"> · </span>
                      <span className="text-slate-500">{prop.category}</span>
                      <span aria-hidden="true"> · </span>
                      <span className="text-slate-800">{prop.formulaLatex}</span>
                    </div>
                    <span className="text-emerald-700 font-semibold tabular-nums">
                      {prop.holdsInModel
                        ? `HOLDS (${prop.statesExplored} states, 0 counterexamples)`
                        : 'FAILED'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-700">{prop.plainLaw}</p>
                  <div className="text-[11px] text-slate-500">
                    Explicit Assumption: {prop.assumptionsExplicit}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="lg:col-span-4 bg-white border border-slate-200 rounded-xl p-5 space-y-4">
            <div className="border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-slate-900">
                03. Inherited #8188 RFCE Admission Predicates
              </h3>
              <p className="text-xs text-slate-600 mt-0.5">
                Step 7 compiles verified KARMA postmortems into mandatory bootstrap predicates{' '}
                <code className="font-mono">K(a,o)</code> enforced at EP-A.
              </p>
            </div>

            <div className="divide-y divide-slate-100">
              {mcc.inheritedRfcePredicates.map((rfce) => (
                <div key={rfce.predicateId} className="py-3 space-y-1 text-xs">
                  <div className="flex items-center justify-between gap-2 font-mono">
                    <span className="font-semibold text-slate-900">{rfce.predicateId}</span>
                    <span className="text-emerald-700 tabular-nums">
                      {rfce.sessionsImmunizedCount} sessions immunized
                    </span>
                  </div>
                  <div className="font-mono text-[11px] text-slate-500">
                    {rfce.sourceIssue} · {rfce.failureClass}
                  </div>
                  <p className="text-slate-700">{rfce.admissionRule}</p>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    );
  }

  if (mode === 'reconciliation_mandate') {
    return (
      <div className="space-y-6">
        {/* Authoritative Tool Reuse Matrix (EX-01..10) */}
        <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3 border-b border-slate-100 pb-4">
            <div>
              <h3 className="text-base font-bold text-slate-900">
                01. Authoritative Tools — Reuse, Never Duplicate (EX-01 – EX-10)
              </h3>
              <p className="text-xs text-slate-600 mt-0.5">
                Reconciles MCC-001 directly onto existing IDP commands, context compilers, MGE-001
                specifications, capability leases, and symphony workstreams without creating a
                competing registry.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-1 bg-slate-100 p-1 rounded-lg">
              {(
                [
                  ['ALL', 'All (10)'],
                  ['OPERATING_LOCAL_GATE', 'Operating Gate'],
                  ['PARTIAL_SOURCE_FOUND', 'Partial Source'],
                  ['SPECIFIED_NOT_ON_MAIN', 'Spec / Draft'],
                ] as const
              ).map(([filterKey, label]) => (
                <button
                  key={filterKey}
                  type="button"
                  onClick={() => setInventoryFilter(filterKey)}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap ${
                    inventoryFilter === filterKey
                      ? 'bg-white text-slate-900 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500">
                  <th className="py-2 pr-3 font-medium">ID &amp; Existing Authority</th>
                  <th className="py-2 px-3 font-medium">Source Verdict</th>
                  <th className="py-2 px-3 font-medium">Existing Capability</th>
                  <th className="py-2 px-3 font-medium">Confirmed Fragmentation Gap</th>
                  <th className="py-2 pl-3 font-medium">MCC-001 Convergence Wiring</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredInventory.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/80">
                    <td className="py-3 pr-3 align-top">
                      <div className="font-mono font-semibold text-slate-900">
                        {item.id} · {item.component}
                      </div>
                      <div className="font-mono text-[11px] text-slate-500 mt-0.5">
                        {item.verifiedSourceEvidence}
                      </div>
                    </td>
                    <td className="py-3 px-3 align-top font-mono text-[11px] font-semibold whitespace-nowrap">
                      <span
                        className={
                          item.operationalVerdict === 'OPERATING_LOCAL_GATE'
                            ? 'text-emerald-700'
                            : item.operationalVerdict === 'PARTIAL_SOURCE_FOUND'
                              ? 'text-blue-700'
                              : 'text-amber-700'
                        }
                      >
                        {item.operationalVerdict}
                      </span>
                    </td>
                    <td className="py-3 px-3 align-top text-slate-700">
                      {item.existingCapability}
                    </td>
                    <td className="py-3 px-3 align-top text-slate-600">
                      {item.confirmedFragmentationGap}
                    </td>
                    <td className="py-3 pl-3 align-top text-slate-800">
                      {item.mccReconciliationAction}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Cross-Repository Protocol Reconciliation (5 Repos) */}
        <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
          <div className="border-b border-slate-100 pb-3">
            <h3 className="text-base font-bold text-slate-900">
              02. Cross-Repository Authority vs Adapter Reconciliation (5 Estate Repositories)
            </h3>
            <p className="text-xs text-slate-600 mt-0.5">
              Establishes one authoritative owner per plane while classifying Argon, Growmos, Crew,
              and Hermes mechanisms as deterministic adapters rather than competing control planes.
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500">
                  <th className="py-2 pr-3 font-medium">Repository</th>
                  <th className="py-2 px-3 font-medium">Resolved Role</th>
                  <th className="py-2 px-3 font-medium">Authoritative Scope</th>
                  <th className="py-2 px-3 font-medium">Adapter Bridge Rule</th>
                  <th className="py-2 pl-3 font-medium">External Live Proof</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {mcc.crossRepoReconciliation.map((repo) => (
                  <tr key={repo.repoId} className="hover:bg-slate-50/80">
                    <td className="py-3 pr-3 align-top">
                      <div className="font-mono font-semibold text-slate-900">
                        {repo.repositoryName}
                      </div>
                      <div className="text-slate-500 mt-0.5">{repo.documentedMechanism}</div>
                    </td>
                    <td className="py-3 px-3 align-top font-mono text-[11px] font-semibold">
                      <span
                        className={
                          repo.resolvedRole === 'AUTHORITATIVE_PLANE_OWNER'
                            ? 'text-emerald-700'
                            : 'text-blue-700'
                        }
                      >
                        {repo.resolvedRole}
                      </span>
                    </td>
                    <td className="py-3 px-3 align-top text-slate-700">
                      {repo.authoritativeFor}
                    </td>
                    <td className="py-3 px-3 align-top text-slate-800">
                      {repo.adapterBridgeRule}
                    </td>
                    <td className="py-3 pl-3 align-top font-mono text-[11px] text-amber-700 whitespace-nowrap">
                      {repo.liveExternalVerification}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* P0 Convergence Mandate (P0-01..10) */}
        <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
          <div className="border-b border-slate-100 pb-3">
            <h3 className="text-base font-bold text-slate-900">
              03. Consolidation &amp; Rollout — 10-Point P0 Convergence Mandate
            </h3>
            <p className="text-xs text-slate-600 mt-0.5">
              Tracks exact completion criteria across Meridian Symphony (#8169), Fleet Comms
              (#7481), Capability Leases (#7787), Continuity (#7790), and RFCE (#8188).
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500">
                  <th className="py-2 pr-3 font-medium">ID &amp; P0 Fragmentation Problem</th>
                  <th className="py-2 px-3 font-medium">Required Architectural Correction</th>
                  <th className="py-2 px-3 font-medium">Proof-of-Completion Criterion</th>
                  <th className="py-2 pl-3 font-medium">Engine vs External Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {mcc.convergenceMandateMatrix.map((row) => (
                  <tr key={row.id} className="hover:bg-slate-50/80">
                    <td className="py-3 pr-3 align-top font-semibold text-slate-900">
                      <span className="font-mono">{row.id}</span> · {row.p0Problem}
                    </td>
                    <td className="py-3 px-3 align-top text-slate-700">
                      {row.requiredCorrection}
                    </td>
                    <td className="py-3 px-3 align-top text-slate-700">
                      {row.proofOfCompletionCriterion}
                    </td>
                    <td className="py-3 pl-3 align-top font-mono text-[11px] whitespace-nowrap">
                      <div className="text-emerald-700 font-semibold">
                        {row.sandboxEnforcementStatus}
                      </div>
                      <div className="text-amber-700">{row.externalEstateStatus}</div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    );
  }

  // Default flagship mode: 'unified_bus_mcc'
  return (
    <div className="space-y-6">
      {/* Constitutional Rule & 7-Step Lifecycle + 5 Enforcement Doors */}
      <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-5">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3 border-b border-slate-100 pb-4">
          <div className="space-y-1 max-w-4xl">
            <div className="text-xs font-mono text-slate-500 break-words">
              <span>{mcc.programmeAnchor}</span>
              <span aria-hidden="true"> · </span>
              <span className="text-emerald-700 font-semibold">
                {invariantsPassedCount}/5 bin/capability-index Invariants
              </span>
              <span aria-hidden="true"> · </span>
              <span className="text-amber-700 font-semibold">
                External Multi-Repo: {mcc.honestEstateVerdict.externalMultiRepoEnforcement}
              </span>
            </div>
            <h3 className="text-base sm:text-lg font-bold text-slate-900 text-balance">
              01. Mandatory 7-Step Recursive Agent Lifecycle &amp; 5 Non-Bypassable Enforcement Doors
            </h3>
            <p className="text-xs text-slate-700">{mcc.constitutionalRule}</p>
          </div>

          <button
            type="button"
            disabled={busyKey !== null}
            onClick={() =>
              void onInvokeAction({ action: 'run_all_cert_scenarios' }, 'run_all_cert_scenarios')
            }
            className="min-h-[40px] inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-900 hover:bg-slate-50 disabled:opacity-50 whitespace-nowrap shrink-0"
          >
            <ShieldAlert className="h-3.5 w-3.5 text-slate-700" aria-hidden="true" />
            {busyKey === 'run_all_cert_scenarios'
              ? 'Verifying 10 Scenarios…'
              : `Verify 10/10 Enforcement Doors (${certPassedCount}/10)`}
          </button>
        </div>

        {/* 7-Step Recursive Lifecycle Strip */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-7 gap-2.5">
          {LIFECYCLE_STEPS.map((st) => (
            <div
              key={st.step}
              className="rounded-lg border border-slate-200 bg-slate-50/70 p-3 flex flex-col justify-between gap-2"
            >
              <div>
                <div className="text-[11px] font-mono font-bold text-slate-900">{st.step}</div>
                <div className="text-xs font-semibold text-slate-800 mt-0.5">{st.title}</div>
                <p className="text-[11px] text-slate-600 mt-1 leading-snug">{st.rule}</p>
              </div>
              <div className="text-[10px] font-mono text-slate-500 pt-1 border-t border-slate-200/80">
                {st.authority}
              </div>
            </div>
          ))}
        </div>

        {/* 5 Enforcement Points Interactive Selector */}
        <div className="space-y-3 pt-1">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-xs font-semibold text-slate-900">
              Select Enforcement Point to Inspect Executable Predicate &amp; Reused IDP Authority
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              {mcc.enforcementPoints.map((ep) => (
                <button
                  key={ep.id}
                  type="button"
                  onClick={() => setSelectedDoorId(ep.id)}
                  className={`min-h-[36px] px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition-colors whitespace-nowrap ${
                    selectedDoor.id === ep.id
                      ? 'bg-slate-900 text-white'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  {ep.id.replace('_', '-')} · Blocked {ep.blockedViolationsCount}
                </button>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-950 text-slate-100 p-4 grid grid-cols-1 lg:grid-cols-12 gap-4 items-center">
            <div className="lg:col-span-5 space-y-1">
              <div className="text-xs font-mono text-cyan-300">{selectedDoor.name}</div>
              <div className="text-sm font-mono font-semibold text-white break-words">
                {selectedDoor.formula}
              </div>
              <div className="text-xs text-slate-400">
                Reused Authority: <span className="text-slate-200">{selectedDoor.existingAuthorityReused}</span>
              </div>
            </div>
            <div className="lg:col-span-4 text-xs text-slate-300">
              <div className="text-slate-400 font-mono text-[11px]">Latest Gateway Decision</div>
              <div className="mt-0.5">{selectedDoor.lastDecisionNote}</div>
            </div>
            <div className="lg:col-span-3 flex items-center lg:justify-end gap-6 font-mono tabular-nums">
              <div>
                <div className="text-[11px] text-slate-400">Admitted</div>
                <div className="text-lg font-bold text-emerald-400">
                  {selectedDoor.admittedCount}
                </div>
              </div>
              <div>
                <div className="text-[11px] text-slate-400">Violations Blocked</div>
                <div className="text-lg font-bold text-amber-300">
                  {selectedDoor.blockedViolationsCount}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Unified Real-Time Web · App · Console Collaboration Fabric */}
      <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-5">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3 border-b border-slate-100 pb-4">
          <div className="space-y-1">
            <div className="text-xs font-mono text-slate-500 tabular-nums">
              <span>Connected Surfaces: {connectedSurfacesCount}/{mcc.surfaces.length}</span>
              <span aria-hidden="true"> · </span>
              <span>Offline Outbox Queue: {totalBufferedOutbox}</span>
              <span aria-hidden="true"> · </span>
              <span>Transport: Server-Authoritative SSE (0 Polling)</span>
            </div>
            <h3 className="text-base font-bold text-slate-900">
              02. Unified Real-Time Web · App · Console Collaboration &amp; Offline Lease Continuity
            </h3>
            <p className="text-xs text-slate-600">
              Disconnect any Web browser, Mobile/WhatsApp app, or CLI console surface below,
              dispatch a directive to verify durable offline outbox buffering, then reconnect to
              observe zero-duplicate automatic reconciliation through <code className="font-mono">EP-A..EP-E</code>.
            </p>
          </div>
        </div>

        {/* 6 Connected Surface Endpoints across WEB / APP / CONSOLE */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {mcc.surfaces.map((surf) => (
            <div
              key={surf.surfaceId}
              className={`rounded-lg border p-3.5 flex flex-col justify-between gap-3 ${
                surf.connected
                  ? 'border-slate-200 bg-white'
                  : 'border-amber-300 bg-amber-50/40'
              }`}
            >
              <div className="space-y-1.5">
                <div className="flex items-center justify-between gap-2 text-xs font-mono">
                  <span className="font-bold text-slate-900">
                    {surf.modality} · {surf.roleClassification === 'AUTHORITATIVE_CORE' ? 'CORE' : 'ADAPTER'}
                  </span>
                  <span
                    className={`font-semibold ${
                      surf.connected ? 'text-emerald-700' : 'text-amber-800'
                    }`}
                  >
                    {surf.connected ? 'CONNECTED' : 'OFFLINE (LEASE BOUNDED)'}
                  </span>
                </div>
                <div className="text-sm font-semibold text-slate-900">{surf.label}</div>
                <div className="text-xs text-slate-600">{surf.protocolAdapter}</div>
                <div className="text-[11px] font-mono text-slate-500 tabular-nums">
                  <span>Receipts: {surf.deliveredReceiptsCount}</span>
                  <span aria-hidden="true"> · </span>
                  <span>Outbox: {surf.bufferedOutboxCount}</span>
                  <span aria-hidden="true"> · </span>
                  <span>Offline Scopes: {surf.offlineLeaseAllowedScopes.join(', ')}</span>
                </div>
              </div>

              <div className="flex items-center justify-between gap-2 pt-2 border-t border-slate-100">
                <span className="text-[11px] font-mono text-slate-500 truncate">
                  Last: {surf.lastCorrelationId ?? 'none'}
                </span>
                <button
                  type="button"
                  disabled={busyKey !== null}
                  aria-label={
                    surf.connected
                      ? `Disconnect ${surf.label}`
                      : `Reconnect and reconcile ${surf.label}`
                  }
                  onClick={() =>
                    void onInvokeAction(
                      {
                        action: 'toggle_unified_surface',
                        surfaceId: surf.surfaceId,
                        connected: !surf.connected,
                      },
                      `surf:${surf.surfaceId}`
                    )
                  }
                  className={`min-h-[36px] inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition-colors whitespace-nowrap ${
                    surf.connected
                      ? 'border border-slate-300 bg-white text-slate-800 hover:bg-slate-50'
                      : 'bg-slate-900 text-white hover:bg-slate-800'
                  }`}
                >
                  {surf.connected ? (
                    <>
                      <WifiOff className="h-3.5 w-3.5" aria-hidden="true" />
                      Disconnect
                    </>
                  ) : (
                    <>
                      <Wifi className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
                      Reconnect &amp; Reconcile
                    </>
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Cross-Surface Directive Form + Live Collaboration Envelope Stream */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 pt-1 items-start">
          <form
            className="lg:col-span-5 rounded-lg border border-slate-200 bg-slate-50/70 p-4 space-y-3"
            onSubmit={(ev) => {
              ev.preventDefault();
              if (!intentInput.trim()) return;
              void onInvokeAction(
                {
                  action: 'dispatch_unified_surface',
                  surfaceId: originSurfaceId,
                  targetCapabilityId: targetCapId,
                  intentSummary: intentInput.trim(),
                },
                'dispatch_unified_surface'
              );
            }}
          >
            <div className="text-xs font-bold text-slate-900">
              Dispatch Authenticated Cross-Surface Intent
            </div>

            <div className="space-y-1">
              <label
                htmlFor="mcc-origin-surface"
                className="block text-xs font-medium text-slate-700"
              >
                Origin Surface (Web / App / Console)
              </label>
              <select
                id="mcc-origin-surface"
                value={originSurfaceId}
                onChange={(e) => setOriginSurfaceId(e.target.value)}
                className="w-full min-h-[40px] rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900"
              >
                {mcc.surfaces.map((s) => (
                  <option key={s.surfaceId} value={s.surfaceId}>
                    [{s.modality}] {s.label} {s.connected ? '(Online)' : '(Offline -> Outbox)'}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1">
              <label
                htmlFor="mcc-target-cap"
                className="block text-xs font-medium text-slate-700"
              >
                Contracted Capability Target (MCC-001 9-Tuple)
              </label>
              <select
                id="mcc-target-cap"
                value={targetCapId}
                onChange={(e) => setTargetCapId(e.target.value)}
                className="w-full min-h-[40px] rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-mono text-slate-900"
              >
                {executableTargetContracts.map((c) => (
                  <option key={c.capabilityId} value={c.capabilityId}>
                    {c.capabilityId} ({c.V.semver})
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1">
              <label
                htmlFor="mcc-intent-input"
                className="block text-xs font-medium text-slate-700"
              >
                Mission / Collaboration Directive
              </label>
              <input
                id="mcc-intent-input"
                type="text"
                value={intentInput}
                onChange={(e) => setIntentInput(e.target.value)}
                placeholder="Describe cross-surface obligation…"
                className="w-full min-h-[40px] rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900"
              />
            </div>

            <button
              type="submit"
              disabled={busyKey !== null || !intentInput.trim()}
              className="w-full min-h-[40px] inline-flex items-center justify-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
            >
              <Send className="h-3.5 w-3.5 text-cyan-400" aria-hidden="true" />
              {busyKey === 'dispatch_unified_surface'
                ? 'Routing Across Web · App · Console…'
                : 'Dispatch Across Web · App · Console'}
            </button>
          </form>

          <div className="lg:col-span-7 space-y-2.5">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-slate-900">
                Unified Collaboration Ledger (FLOW Custody + YIELD/1 Receipts)
              </span>
              <span className="font-mono text-slate-500 tabular-nums">
                {mcc.collaborationStream.length} envelopes
              </span>
            </div>

            <div className="divide-y divide-slate-100 rounded-lg border border-slate-200 bg-white">
              {mcc.collaborationStream.slice(0, 6).map((env) => (
                <div key={env.envelopeId} className="p-3.5 space-y-1 text-xs">
                  <div className="flex flex-wrap items-center justify-between gap-2 font-mono">
                    <div className="text-slate-900 font-semibold tabular-nums">
                      <span>{env.envelopeId}</span>
                      <span aria-hidden="true"> · </span>
                      <span>{env.originModality}</span>
                      <span aria-hidden="true"> · </span>
                      <span className="text-slate-600">{env.originSurfaceId}</span>
                    </div>
                    <span
                      className={`font-semibold ${
                        env.settlementState === 'VERIFIED_EFFECT'
                          ? 'text-emerald-700'
                          : env.settlementState === 'BUFFERED_OFFLINE_OUTBOX'
                            ? 'text-amber-700'
                            : 'text-red-700'
                      }`}
                    >
                      {env.settlementState}
                      {env.fencingToken ? ` · f_${env.fencingToken}` : ''}
                    </span>
                  </div>
                  <div className="text-slate-800 font-medium">{env.intentSummary}</div>
                  <div className="font-mono text-[11px] text-slate-500 tabular-nums">
                    <span>Cap: {env.targetCapabilityId}</span>
                    <span aria-hidden="true"> · </span>
                    <span>
                      Doors:{' '}
                      {env.enforcementDoorsPassed.length > 0
                        ? env.enforcementDoorsPassed.join(' -> ')
                        : 'Pending Reconnect'}
                    </span>
                    <span aria-hidden="true"> · </span>
                    <span>sha256:{env.receiptSha256.slice(0, 12)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Universal 9-Tuple Contract Explorer + Sequential Composition & Authority Narrowing */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        <section className="lg:col-span-6 bg-white border border-slate-200 rounded-xl p-5 space-y-4">
          <div className="border-b border-slate-100 pb-3 space-y-1">
            <h3 className="text-base font-bold text-slate-900">
              03. Universal 9-Tuple Capability Contract Explorer — C_c = (I, O, P, Q, A, E, F, R, V)
            </h3>
            <p className="text-xs text-slate-600">
              Bound to <code className="font-mono">bin/capability-index</code> invariants: 1 writer
              per plane, fresh receipt required for <code className="font-mono">OPERATING</code>,
              and cryptographic tombstones for retired capabilities.
            </p>
          </div>

          <div className="space-y-1">
            <label
              htmlFor="mcc-contract-select"
              className="block text-xs font-medium text-slate-700"
            >
              Inspect Registered Estate Capability Contract ({mcc.contracts.length} records)
            </label>
            <select
              id="mcc-contract-select"
              value={selectedContract?.capabilityId ?? ''}
              onChange={(e) => setSelectedContractId(e.target.value)}
              className="w-full min-h-[40px] rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-mono text-slate-900"
            >
              {mcc.contracts.map((c) => (
                <option key={c.capabilityId} value={c.capabilityId}>
                  {c.capabilityId} · {c.truthStatus} ({c.planeOwner})
                </option>
              ))}
            </select>
          </div>

          {selectedContract && (
            <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-3.5 space-y-2.5 text-xs">
              <div className="flex flex-wrap items-center justify-between gap-2 font-mono">
                <span className="font-bold text-slate-900">{selectedContract.displayName}</span>
                <span
                  className={`font-semibold ${
                    selectedContract.truthStatus === 'OPERATING'
                      ? 'text-emerald-700'
                      : selectedContract.truthStatus === 'TOMBSTONED'
                        ? 'text-red-700'
                        : 'text-amber-700'
                  }`}
                >
                  {selectedContract.truthStatus} · {selectedContract.freshnessState}
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                <div>
                  <span className="font-mono font-bold text-slate-900">I (Pre):</span>{' '}
                  <span className="text-slate-700">
                    {selectedContract.I.requiredPredicates.join(', ') || 'none (root)'}
                  </span>
                </div>
                <div>
                  <span className="font-mono font-bold text-slate-900">O (Post):</span>{' '}
                  <span className="text-slate-700">
                    {selectedContract.O.guaranteedPredicates.join(', ') || 'none'}
                  </span>
                </div>
                <div>
                  <span className="font-mono font-bold text-slate-900">P (Policy):</span>{' '}
                  <span className="font-mono text-slate-700">
                    {selectedContract.P.requiredScopes.join(', ')} ({selectedContract.P.regoRuleIds.join(', ')})
                  </span>
                </div>
                <div>
                  <span className="font-mono font-bold text-slate-900">Q (SLA):</span>{' '}
                  <span className="font-mono tabular-nums text-slate-700">
                    p95 &le; {selectedContract.Q.maxLatencyP95Ms}ms · ${selectedContract.Q.maxCostUsd} ·{' '}
                    {selectedContract.Q.minAvailabilityPct}%
                  </span>
                </div>
                <div>
                  <span className="font-mono font-bold text-slate-900">A (Authority):</span>{' '}
                  <span className="font-mono text-slate-700">
                    Delegable: [{selectedContract.A.delegableSubset.join(', ') || 'none'}]
                  </span>
                </div>
                <div>
                  <span className="font-mono font-bold text-slate-900">E (Evidence):</span>{' '}
                  <span className="font-mono text-slate-700">
                    {selectedContract.E.requiredReceiptFormat} · Indep={String(selectedContract.E.requiresIndependentObserver)}
                  </span>
                </div>
                <div>
                  <span className="font-mono font-bold text-slate-900">F (Failures):</span>{' '}
                  <span className="text-slate-700">
                    {selectedContract.F.declaredFailureModes.join(', ')}
                  </span>
                </div>
                <div>
                  <span className="font-mono font-bold text-slate-900">R &amp; V:</span>{' '}
                  <span className="font-mono tabular-nums text-slate-700">
                    Lease {selectedContract.R.leaseTtlMs}ms · v{selectedContract.V.semver} ·{' '}
                    {selectedContract.V.contractSha256.slice(0, 10)}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* 5 bin/capability-index invariants */}
          <div className="divide-y divide-slate-100 border-t border-slate-100 pt-2">
            {mcc.registryInvariantChecks.map((inv) => (
              <div key={inv.invariantIndex} className="py-2 flex items-start justify-between gap-3 text-xs">
                <div>
                  <span className="font-mono font-semibold text-slate-900">
                    Inv #{inv.invariantIndex}:
                  </span>{' '}
                  <span className="font-medium text-slate-800">{inv.rule}</span>
                  <div className="text-[11px] text-slate-500">{inv.detail}</div>
                </div>
                <span className="font-mono font-semibold text-emerald-700 shrink-0">
                  {inv.passed ? 'VERIFIED' : 'VIOLATION'}
                </span>
              </div>
            ))}
          </div>
        </section>

        <section className="lg:col-span-6 bg-white border border-slate-200 rounded-xl p-5 space-y-4">
          <div className="border-b border-slate-100 pb-3 space-y-1">
            <h3 className="text-base font-bold text-slate-900">
              04. MGE-001 Composition Prover, Authority Narrowing &amp; Zero-Change Provider Evolution
            </h3>
            <p className="text-xs text-slate-600">
              Enforces <code className="font-mono">Post(C_1) =&gt; Pre(C_2)</code> and{' '}
              <code className="font-mono">Authority(e) &sube; Authority(issuer) &cap; Policy(C)</code>{' '}
              so workflow edits never silently acquire production deploy rights.
            </p>
          </div>

          <div className="space-y-1.5">
            <div className="text-xs font-medium text-slate-700">
              Select Workflow Composition Chain to Verify
            </div>
            <div className="grid grid-cols-1 gap-1.5">
              {mcc.compositionPresets.map((preset) => (
                <button
                  key={preset.presetId}
                  type="button"
                  onClick={() => setSelectedCompositionId(preset.presetId)}
                  className={`text-left rounded-lg border px-3 py-2 text-xs transition-colors ${
                    selectedComposition.presetId === preset.presetId
                      ? 'border-slate-900 bg-slate-900 text-white'
                      : 'border-slate-200 bg-slate-50/70 text-slate-800 hover:bg-slate-100'
                  }`}
                >
                  <div className="flex flex-wrap items-baseline justify-between gap-x-2 gap-y-0.5 font-mono">
                    <span className="font-semibold">{preset.title}</span>
                    <span
                      className={`text-[11px] ${
                        preset.compatible
                          ? selectedComposition.presetId === preset.presetId
                            ? 'text-emerald-300'
                            : 'text-emerald-700'
                          : selectedComposition.presetId === preset.presetId
                            ? 'text-amber-300'
                            : 'text-red-700'
                      }`}
                    >
                      {preset.compatible ? 'ADMITTED' : `BLOCKED · ${preset.failureCode}`}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {selectedComposition && (
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3.5 space-y-2 text-xs">
              <div className="flex flex-wrap items-center justify-between gap-2 font-mono">
                <span className="font-bold text-slate-900">
                  Verdict:{' '}
                  {selectedComposition.compatible
                    ? 'VALID_COMPOSITION'
                    : selectedComposition.failureCode}
                </span>
                <span className="text-slate-500 tabular-nums">
                  p95={selectedComposition.cumulativeLatencyP95Ms}ms · $
                  {selectedComposition.cumulativeMaxCostUsd.toFixed(4)}
                </span>
              </div>
              <div className="font-mono text-[11px] text-slate-600 break-words">
                Chain: {selectedComposition.chainCapabilityIds.join(' -> ')}
              </div>
              <p className="text-slate-800 font-medium">{selectedComposition.explanation}</p>
              <div className="font-mono text-[11px] text-slate-500 tabular-nums">
                <span>Post=&gt;Pre: {String(selectedComposition.postImpliesPrePassed)}</span>
                <span aria-hidden="true"> · </span>
                <span>
                  Authority Narrowed: {String(selectedComposition.authorityNarrowingPassed)}
                </span>
                <span aria-hidden="true"> · </span>
                <span>sha256:{selectedComposition.proofSha256.slice(0, 12)}</span>
              </div>
            </div>
          )}

          {/* Contravariant / Covariant Refinement Proof */}
          {mcc.refinementProofs.map((ref) => (
            <div
              key={ref.newCapabilityId}
              className="rounded-lg border border-slate-200 bg-white p-3.5 space-y-1.5 text-xs"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 font-mono">
                <span className="font-bold text-slate-900">
                  Future Capability Refinement ({ref.oldCapabilityId} &rarr; {ref.newCapabilityId})
                </span>
                <span className="text-emerald-700 font-semibold">
                  {ref.validRefinement && ref.zeroCoreChangesRequired
                    ? '0 CORE CHANGES REQUIRED'
                    : 'REQUIRES ADAPTER'}
                </span>
              </div>
              <p className="text-slate-700">{ref.summary}</p>
              <div className="font-mono text-[11px] text-slate-500">
                Pre Weakened/Equal={String(ref.preconditionWeakenedOrEqual)} · Post
                Strengthened/Equal={String(ref.postconditionStrengthenedOrEqual)} · Recovery
                Preserved={String(ref.recoveryPreserved)}
              </div>
            </div>
          ))}
        </section>
      </div>
    </div>
  );
}
