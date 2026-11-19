import React, { useState } from 'react';
import {
  EstateState,
  BacklogMission,
  PillarId,
  runByzantineSieve,
} from '../engine/ottoEngine';
import { Cpu, CheckCircle2, Plus, Search } from 'lucide-react';

interface SwarmBacklogViewProps {
  state: EstateState;
  onDrainMission: (missionId: string) => void;
  onCreateContract: (input: {
    title: string;
    targetRepo: string;
    bddSpec: string;
    pillar: PillarId;
    priority: BacklogMission['priority'];
  }) => void;
}

export const SwarmBacklogView: React.FC<SwarmBacklogViewProps> = ({
  state,
  onDrainMission,
  onCreateContract,
}) => {
  const [statusFilter, setStatusFilter] = useState<'ALL' | BacklogMission['status']>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const [title, setTitle] = useState('');
  const [targetRepo, setTargetRepo] = useState('argon');
  const [bddSpec, setBddSpec] = useState('');
  const [pillar, setPillar] = useState<PillarId>('SWARM_MAESTRO');
  const [priority, setPriority] = useState<BacklogMission['priority']>('P1_HIGH');
  const [formError, setFormError] = useState<string | null>(null);

  const filteredMissions = state.missions.filter((m) => {
    const matchesStatus = statusFilter === 'ALL' || m.status === statusFilter;
    const matchesQuery =
      !searchQuery.trim() ||
      m.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.targetRepo.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesStatus && matchesQuery;
  });

  const handleContractSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !bddSpec.trim()) {
      setFormError('Both a Mission Title and a verifiable BDD Specification are required.');
      return;
    }
    setFormError(null);
    onCreateContract({
      title: title.trim(),
      targetRepo,
      bddSpec: bddSpec.trim(),
      pillar,
      priority,
    });
    setTitle('');
    setBddSpec('');
  };

  return (
    <div className="space-y-8">
      {/* Header & Filter Bar */}
      <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-1.5 max-w-3xl">
            <div className="text-xs font-mono text-slate-500 dark:text-slate-400 tabular-nums">
              SWARM_MAESTRO · .genesis/missions/backlog.json · BYZANTINE SIEVE (2/3 QUORUM)
            </div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50">
              Autonomous Backlog Drainer & Subordinate Marshalling
            </h1>
            <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
              Otto reads directly from <code className="font-mono text-xs">.genesis/missions/backlog.json</code>,
              decomposes founder intent into micro-contracts, fans execution across <code className="font-mono text-xs">Claude</code>,{' '}
              <code className="font-mono text-xs">Codex</code>, and <code className="font-mono text-xs">Pi</code>, verifies
              deterministic output hashes via the Byzantine Sieve, and stages verified branches to{' '}
              <code className="font-mono text-xs">origin/propose/*</code>.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="search"
                aria-label="Filter missions by ID or title"
                placeholder="Search backlog..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-1.5 text-xs bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg text-slate-900 dark:text-slate-100"
              />
            </div>

            <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg">
              {(['ALL', 'DEMO_STAGED', 'SEALED_TO_ORIGIN', 'QUEUED'] as const).map((st) => (
                <button
                  key={st}
                  type="button"
                  onClick={() => setStatusFilter(st)}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                    statusFilter === st
                      ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                  }`}
                >
                  {st === 'ALL' ? 'All Missions' : st}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Active Backlog Missions & Byzantine Sieve Matrix */}
      <section className="space-y-4">
        {filteredMissions.length === 0 ? (
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-8 text-center space-y-3">
            <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              No missions match the current filter
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Reset the status filter or dispatch a new Founder Intent Contract below.
            </p>
            <button
              type="button"
              onClick={() => {
                setStatusFilter('ALL');
                setSearchQuery('');
              }}
              className="px-3.5 py-2 text-xs font-medium text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors cursor-pointer"
            >
              Show All Backlog Missions
            </button>
          </div>
        ) : (
          filteredMissions.map((mission) => {
            const sieve = runByzantineSieve(mission.subordinateVotes);
            return (
              <div
                key={mission.id}
                className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 space-y-5"
              >
                <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                  <div className="space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-slate-500 dark:text-slate-400 tabular-nums">
                      <span className="font-semibold text-slate-900 dark:text-slate-100">{mission.id}</span>
                      <span aria-hidden="true">·</span>
                      <span>{mission.priority}</span>
                      <span aria-hidden="true">·</span>
                      <span>repo={mission.targetRepo}</span>
                      <span aria-hidden="true">·</span>
                      <span>branch={mission.branchProposal}</span>
                      <span aria-hidden="true">·</span>
                      <span>idp-ci={mission.idpCiGate}</span>
                    </div>
                    <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                      {mission.title}
                    </h2>
                    <p className="text-xs font-mono text-slate-600 dark:text-slate-300">
                      BDD Contract: {mission.bddSpec}
                    </p>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <div className="text-right font-mono text-xs tabular-nums">
                      <div className="text-slate-500 dark:text-slate-400">
                        Sieve Quorum: <strong className="text-emerald-500">{sieve.agreementRatio}</strong>
                      </div>
                      <div className="text-slate-400">{mission.status}</div>
                    </div>
                    <button
                      type="button"
                      onClick={() => onDrainMission(mission.id)}
                      className="px-4 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer"
                    >
                      {mission.status === 'SEALED_TO_ORIGIN'
                        ? `Sealed (${mission.bundleHash.slice(0, 15)})`
                        : `Drain & Seal ${mission.id}`}
                    </button>
                  </div>
                </div>

                {/* Subordinate Agent Votes Table */}
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-800 text-xs font-mono text-slate-500 dark:text-slate-400">
                        <th className="py-2 pr-4 font-medium">Subordinate Vessel</th>
                        <th className="py-2 px-3 font-medium">Assigned Role</th>
                        <th className="py-2 px-3 font-medium">Verification Note</th>
                        <th className="py-2 px-3 font-medium text-right">BDD Checks</th>
                        <th className="py-2 px-3 font-medium text-right">Latency</th>
                        <th className="py-2 pl-3 font-medium text-right">Output Hash & Verdict</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 dark:divide-slate-800/60 text-xs font-mono tabular-nums">
                      {mission.subordinateVotes.map((vote) => (
                        <tr key={vote.agent}>
                          <td className="py-2.5 pr-4 font-semibold text-slate-900 dark:text-slate-100">
                            {vote.agent}
                          </td>
                          <td className="py-2.5 px-3 font-sans text-slate-600 dark:text-slate-300">
                            {vote.role}
                          </td>
                          <td className="py-2.5 px-3 font-sans text-slate-500 dark:text-slate-400">
                            {vote.note}
                          </td>
                          <td className="py-2.5 px-3 text-right text-slate-700 dark:text-slate-300">
                            {vote.bddAssertionsPassed} passed
                          </td>
                          <td className="py-2.5 px-3 text-right text-slate-500 dark:text-slate-400">
                            {vote.latencyMs} ms
                          </td>
                          <td className="py-2.5 pl-3 text-right">
                            <span className="text-slate-400 mr-2">{vote.outputHash}</span>
                            <span className="text-emerald-500 font-semibold">{vote.status}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          })
        )}
      </section>

      {/* Dispatch New Founder Intent Micro-Contract */}
      <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6">
        <div className="pb-4 border-b border-slate-200 dark:border-slate-800">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            Dispatch New Founder Intent Contract to Byzantine Sieve
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Breaks high-level intent into deterministic BDD assertions and marshals Claude, Codex, and Pi to 100% yield.
          </p>
        </div>

        <form onSubmit={handleContractSubmit} className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2">
            <label
              htmlFor="contract-title"
              className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1"
            >
              Mission Contract Title
            </label>
            <input
              id="contract-title"
              type="text"
              placeholder="e.g., Deduplicate argon-sync session blobs into content-addressed store"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg text-slate-900 dark:text-slate-100"
            />
          </div>

          <div>
            <label
              htmlFor="contract-repo"
              className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1"
            >
              Target Estate Repository
            </label>
            <select
              id="contract-repo"
              value={targetRepo}
              onChange={(e) => setTargetRepo(e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg text-slate-900 dark:text-slate-100"
            >
              <option value="argon">argon</option>
              <option value="idp">idp</option>
              <option value="argon-sync">argon-sync</option>
              <option value="genesis-live">genesis-live</option>
            </select>
          </div>

          <div className="md:col-span-2">
            <label
              htmlFor="contract-bdd"
              className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1"
            >
              Empirical BDD Specification (DEMO_OR_SILENCE Proof Requirement)
            </label>
            <input
              id="contract-bdd"
              type="text"
              placeholder="GIVEN 3566 dirty session files WHEN content-addressed pack runs THEN index dirty count drops to 0 with zero data loss"
              value={bddSpec}
              onChange={(e) => setBddSpec(e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg text-slate-900 dark:text-slate-100"
            />
          </div>

          <div>
            <label
              htmlFor="contract-priority"
              className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1"
            >
              Priority Class
            </label>
            <select
              id="contract-priority"
              value={priority}
              onChange={(e) => setPriority(e.target.value as BacklogMission['priority'])}
              className="w-full px-3 py-2 text-xs font-mono bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg text-slate-900 dark:text-slate-100"
            >
              <option value="P0_BLOCKER">P0_BLOCKER</option>
              <option value="P1_HIGH">P1_HIGH</option>
              <option value="P2_NORMAL">P2_NORMAL</option>
            </select>
          </div>

          <div className="md:col-span-3 flex flex-wrap items-center justify-between gap-4 pt-2">
            <div className="text-xs font-mono text-rose-500">
              {formError ? formError : ''}
            </div>
            <button
              type="submit"
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              Dispatch Contract to Swarm
            </button>
          </div>
        </form>
      </section>
    </div>
  );
};
