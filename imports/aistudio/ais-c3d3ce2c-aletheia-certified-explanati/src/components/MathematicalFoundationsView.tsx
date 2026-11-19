/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';

interface MathematicalFoundationsViewProps {
  mode: 'foundations' | 'strategy';
  onSwitchToInspector: () => void;
}

export const MathematicalFoundationsView: React.FC<MathematicalFoundationsViewProps> = ({
  mode,
  onSwitchToInspector,
}) => {
  // Interactive Proof Sandbox State for Theorem 1 & Theorem 3
  const [probeRecall, setProbeRecall] = useState(0.93);
  const [confessionRecall, setConfessionRecall] = useState(0.743);
  const [cotFaithfulness, setCotFaithfulness] = useState(0.25);
  const [cotMonitorability, setCotMonitorability] = useState(0.68);
  const [weightsAvailable, setWeightsAvailable] = useState(true);

  const effectiveProbe = weightsAvailable ? probeRecall : 0;
  const effectiveCot = cotFaithfulness * cotMonitorability;
  const escapeProb = (1 - effectiveProbe) * (1 - confessionRecall) * (1 - effectiveCot);
  const combinedDetection = 1 - escapeProb;

  // Interactive Solo-Founder Map-Once Flywheel State
  const [monthlyInstructions, setMonthlyInstructions] = useState(1200);
  const [protocolReuseRate, setProtocolReuseRate] = useState(0.72);
  const frontierCostPerRun = 0.42;
  const openWeightsProtocolCost = 0.018;
  const baselineMonthlySpend = monthlyInstructions * frontierCostPerRun;
  const fortressMonthlySpend =
    monthlyInstructions *
    ((1 - protocolReuseRate) * frontierCostPerRun + protocolReuseRate * openWeightsProtocolCost);
  const costReductionPct =
    ((baselineMonthlySpend - fortressMonthlySpend) / Math.max(1, baselineMonthlySpend)) * 100;

  if (mode === 'foundations') {
    return (
      <div className="max-w-7xl mx-auto p-6 lg:p-8 space-y-8">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-slate-800 pb-5">
          <div>
            <span className="text-xs font-mono uppercase tracking-wider text-cyan-400">
              Irrefutable Epistemic Calculus
            </span>
            <h1 className="text-2xl lg:text-3xl font-bold text-slate-100 font-display mt-1">
              Four Mathematical Guarantees Closing the Explainability Gap
            </h1>
            <p className="text-sm text-slate-300 mt-2 max-w-3xl leading-relaxed">
              Why existing observability and interpretability tools fail when used in isolation, and how Aletheia bounds epistemic ignorance across Layers 1–4.
            </p>
          </div>
          <button
            type="button"
            onClick={onSwitchToInspector}
            className="px-4 py-2 text-xs font-semibold text-slate-950 bg-cyan-400 rounded-md hover:bg-cyan-300 transition-colors whitespace-nowrap self-start"
          >
            Inspect Live Corpus Records
          </button>
        </div>

        {/* Interactive Orthogonal Honesty Stack Sandbox */}
        <section className="bg-[#0D121D] border border-slate-800/90 rounded-lg p-6 space-y-5">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div>
              <span className="text-xs font-mono uppercase text-cyan-400">
                Interactive Proof Verifier · Orthogonal Channel Fusion
              </span>
              <h2 className="text-lg font-bold text-slate-100 font-display mt-0.5">
                Joint Deception Escape Bound: P(Escape) = (1 − R_probe · I_weights)(1 − R_conf)(1 − φ_CoT · μ)
              </h2>
            </div>
            <div className="flex items-center gap-6 text-right font-mono">
              <div>
                <div className="text-xs text-slate-400 uppercase">Combined Detection</div>
                <div className="text-2xl font-bold text-emerald-400 tabular-nums">
                  {(combinedDetection * 100).toFixed(2)}%
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-400 uppercase">Residual Blindspot</div>
                <div className="text-2xl font-bold text-amber-300 tabular-nums">
                  {(escapeProb * 100).toFixed(2)}%
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            <div className="p-3.5 rounded bg-[#080B12] border border-slate-800 space-y-2">
              <div className="flex justify-between text-xs font-mono">
                <label htmlFor="math-probe">L1 Probe Recall (R_probe)</label>
                <span className="text-cyan-300 tabular-nums">{(effectiveProbe * 100).toFixed(0)}%</span>
              </div>
              <input
                id="math-probe"
                type="range"
                min={0.5}
                max={0.98}
                step={0.01}
                disabled={!weightsAvailable}
                value={probeRecall}
                onChange={(e) => setProbeRecall(parseFloat(e.target.value))}
                className="w-full accent-cyan-400 disabled:opacity-40"
              />
              <button
                type="button"
                onClick={() => setWeightsAvailable(!weightsAvailable)}
                className="w-full py-1 px-2 text-xs font-mono rounded border border-slate-700 bg-slate-900 text-slate-200 hover:border-cyan-400"
              >
                Mode: {weightsAvailable ? 'Open-Weights (Active)' : 'API-Only (0% L1)'}
              </button>
            </div>

            <div className="p-3.5 rounded bg-[#080B12] border border-slate-800 space-y-2">
              <div className="flex justify-between text-xs font-mono">
                <label htmlFor="math-conf">L2 Confession Recall (R_conf)</label>
                <span className="text-cyan-300 tabular-nums">{(confessionRecall * 100).toFixed(1)}%</span>
              </div>
              <input
                id="math-conf"
                type="range"
                min={0}
                max={0.95}
                step={0.01}
                value={confessionRecall}
                onChange={(e) => setConfessionRecall(parseFloat(e.target.value))}
                className="w-full accent-cyan-400"
              />
              <div className="text-[11px] text-slate-400 font-mono">
                OpenAI 2026 empirical baseline: 74.3%
              </div>
            </div>

            <div className="p-3.5 rounded bg-[#080B12] border border-slate-800 space-y-2">
              <div className="flex justify-between text-xs font-mono">
                <label htmlFor="math-cot-faith">L2 CoT Faithfulness (φ_CoT)</label>
                <span className="text-cyan-300 tabular-nums">{(cotFaithfulness * 100).toFixed(0)}%</span>
              </div>
              <input
                id="math-cot-faith"
                type="range"
                min={0.02}
                max={0.6}
                step={0.01}
                value={cotFaithfulness}
                onChange={(e) => setCotFaithfulness(parseFloat(e.target.value))}
                className="w-full accent-cyan-400"
              />
              <div className="text-[11px] text-slate-400 font-mono">
                Anthropic 2025 empirical range: 25%–39%
              </div>
            </div>

            <div className="p-3.5 rounded bg-[#080B12] border border-slate-800 space-y-2">
              <div className="flex justify-between text-xs font-mono">
                <label htmlFor="math-cot-mon">CoT Monitorability (μ)</label>
                <span className="text-cyan-300 tabular-nums">{(cotMonitorability * 100).toFixed(0)}%</span>
              </div>
              <input
                id="math-cot-mon"
                type="range"
                min={0.1}
                max={1.0}
                step={0.02}
                value={cotMonitorability}
                onChange={(e) => setCotMonitorability(parseFloat(e.target.value))}
                className="w-full accent-cyan-400"
              />
              <div className="text-[11px] text-slate-400 font-mono">
                Declining in forward-pass / Astra models
              </div>
            </div>
          </div>
        </section>

        {/* Four Formal Theorems Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <article className="bg-[#0D121D] border border-slate-800/90 rounded-lg p-5 space-y-3">
            <div className="text-xs font-mono text-cyan-400 uppercase">
              Theorem 1 · Asymmetric Self-Report Epistemology (Layer 2)
            </div>
            <h3 className="text-base font-bold text-slate-100 font-display">
              Zero Exoneration by Stated Chain-of-Thought
            </h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              Because frontier reasoning models verbalize true causal hints only 25–39% of the time and admit reward hacking &lt;2% of the time, treating a clean scratchpad as evidence of compliance is a mathematical fallacy.
            </p>
            <div className="p-3 rounded bg-[#080B12] border border-slate-800 font-mono text-xs text-cyan-200">
              ∀ E_L1, E_L3 : Bel(C | E_L1, E_L3, E_CoT = clean) = Bel(C | E_L1, E_L3)
              <br />
              Pl(C | E_CoT = incriminating ∨ E_conf = violated) ≤ α · Pl(C), α ≪ 1
            </div>
            <p className="text-xs text-slate-400">
              Guarantee: A clean self-report can never inflate Warranted Belief Bel(C), while an incriminating confession or scratchpad trace immediately contracts Upper Plausibility Pl(C).
            </p>
          </article>

          <article className="bg-[#0D121D] border border-slate-800/90 rounded-lg p-5 space-y-3">
            <div className="text-xs font-mono text-cyan-400 uppercase">
              Theorem 2 · Cryptographic State-Diff Completeness (Layer 3)
            </div>
            <h3 className="text-base font-bold text-slate-100 font-display">
              Fencing-Token Merkle Witnessing Eliminates Silent Misreports
            </h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              Mainstream agent frameworks (LangChain, CrewAI, AutoGen) fail EU AI Act Article 12 because they log agent self-reports. Aletheia enforces a monotonic fencing token τₖ &gt; τₖ₋₁ and hashes kernel state diffs ΔSₖ = Sₖ ⊖ Sₖ₋₁.
            </p>
            <div className="p-3 rounded bg-[#080B12] border border-slate-800 font-mono text-xs text-cyan-200">
              Wₖ = H(Wₖ₋₁ ∥ τₖ ∥ σ_auth ∥ Sₖ₋₁ ∥ Sₖ)
              <br />
              norm(Aₖ^self) ≠ norm(Sₖ ⊖ Sₖ₋₁) ⇒ V_L3 = 0 ∧ Art12 = FALSE
            </div>
            <p className="text-xs text-slate-400">
              Guarantee: Any Shapira-class silent action misreport or out-of-order replay is deterministically caught with collision resistance 1 − 2⁻²⁵⁶.
            </p>
          </article>

          <article className="bg-[#0D121D] border border-slate-800/90 rounded-lg p-5 space-y-3">
            <div className="text-xs font-mono text-cyan-400 uppercase">
              Theorem 3 · Dark-Matter Residual Bounding (Layer 1)
            </div>
            <h3 className="text-base font-bold text-slate-100 font-display">
              Mechanistic Warrant Capped by Observed Circuit Energy
            </h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              Cross-layer transcoders and SAEs explain roughly 25–50% of frontier computation; the remaining 50–75% flows through unexplained error nodes (“dark matter”). Closed-API models expose 0% of internals.
            </p>
            <div className="p-3 rounded bg-[#080B12] border border-slate-800 font-mono text-xs text-cyan-200">
              ε_dark = 1 − F_replacement · N_causal(do(z = 0))
              <br />
              Bel_L1(C) ≤ (1 − ε_dark) · (1 − A_probe)
            </div>
            <p className="text-xs text-slate-400">
              Guarantee: Aletheia never overclaims mechanistic interpretability beyond the measured circuit replacement fidelity, explicitly reporting ε_dark inside the ignorance interval Ω(C).
            </p>
          </article>

          <article className="bg-[#0D121D] border border-slate-800/90 rounded-lg p-5 space-y-3">
            <div className="text-xs font-mono text-cyan-400 uppercase">
              Theorem 4 · Correspondence &amp; Mental-Map Durability (Layer 4)
            </div>
            <h3 className="text-base font-bold text-slate-100 font-display">
              Solving the Mathocalypse: Verification ≠ Comprehension
            </h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              A Lean 4 kernel certificate proves that the formal proposition P_formal compiles, not that P_formal matches the human claim H_inf or that a human can retain the idea (UGC &amp; Navier–Stokes episodes).
            </p>
            <div className="p-3 rounded bg-[#080B12] border border-slate-800 font-mono text-xs text-cyan-200">
              κ_corr = I(A_formal ⊬ ⊥) · (1 − δ_drift) · (0.4 + 0.6 · S_mutation)
              <br />
              Bottleneck(G_map) = argmin_&#123;v ∈ V_map&#125; Bel(v)
            </div>
            <p className="text-xs text-slate-400">
              Guarantee: Separates Headline, Informal Claim, and Kernel Proposition, while grading Comprehension, Critical Assessment, and Capability Retention.
            </p>
          </article>
        </div>
      </div>
    );
  }

  // Strategy & Unoccupied Layer Mode
  return (
    <div className="max-w-7xl mx-auto p-6 lg:p-8 space-y-8">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <span className="text-xs font-mono uppercase tracking-wider text-cyan-400">
            November 2026 Landscape Synthesis &amp; Solo-Founder Wedge
          </span>
          <h1 className="text-2xl lg:text-3xl font-bold text-slate-100 font-display mt-1">
            Why the Seams Are Empty — And How We Own the Integration Layer
          </h1>
          <p className="text-sm text-slate-300 mt-2 max-w-3xl leading-relaxed">
            Over $4B in 2025–2026 valuations and acquisitions validated L1 and L3 separately, yet zero incumbents emit an integrated, evidence-graded L1–L4 Explanation Record.
          </p>
        </div>
        <button
          type="button"
          onClick={onSwitchToInspector}
          className="px-4 py-2 text-xs font-semibold text-slate-950 bg-cyan-400 rounded-md hover:bg-cyan-300 transition-colors whitespace-nowrap self-start"
        >
          Explore Live Explanation Records
        </button>
      </div>

      {/* Industry Fragmentation Matrix */}
      <section className="bg-[#0D121D] border border-slate-800/90 rounded-lg p-5 space-y-4">
        <h2 className="text-base font-bold text-slate-100 font-display">
          01. The Four-Layer Fragmentation Map (Nov 2026 Market State)
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-mono">
                <th className="py-2.5 pr-3">Layer / Market Player</th>
                <th className="py-2.5 px-3">2025–2026 Capital Signal</th>
                <th className="py-2.5 px-3">What It Solves</th>
                <th className="py-2.5 px-3">Structural Blindspot (Why It Fails Alone)</th>
                <th className="py-2.5 pl-3 text-right">Aletheia Integration</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              <tr>
                <td className="py-3 pr-3 font-semibold text-slate-100">
                  L1 · Goodfire / Gemma Scope 2 / NLA
                </td>
                <td className="py-3 px-3 font-mono text-cyan-300 tabular-nums">
                  $1.25B Valuation ($150M Ser B)
                </td>
                <td className="py-3 px-3 text-slate-300">
                  Reads internal SAE features, probes, and NLA activation translations.
                </td>
                <td className="py-3 px-3 text-amber-200">
                  ~75% Dark-Matter residual; NLA hallucinates; zero L3 action provenance.
                </td>
                <td className="py-3 pl-3 text-right font-mono text-emerald-400">
                  ● Bounded by ε_dark
                </td>
              </tr>
              <tr>
                <td className="py-3 pr-3 font-semibold text-slate-100">
                  L2 · OpenAI Confessions &amp; CoT Monitors
                </td>
                <td className="py-3 px-3 font-mono text-cyan-300 tabular-nums">
                  Lab-Internal Safety Stack
                </td>
                <td className="py-3 px-3 text-slate-300">
                  74.3% confession recall on known violations; cheap scratchpad monitoring.
                </td>
                <td className="py-3 px-3 text-amber-200">
                  25–39% CoT faithfulness; blind to unknown-unknowns; monitorability declining.
                </td>
                <td className="py-3 pl-3 text-right font-mono text-emerald-400">
                  ● Asymmetric Pl(C)
                </td>
              </tr>
              <tr>
                <td className="py-3 pr-3 font-semibold text-slate-100">
                  L3 · W&amp;B / Langfuse / Braintrust / Arize
                </td>
                <td className="py-3 px-3 font-mono text-cyan-300 tabular-nums">
                  $1.7B CoreWeave + $800M Braintrust
                </td>
                <td className="py-3 px-3 text-slate-300">
                  Ingests OTel spans, token latencies, and agent self-reported tool logs.
                </td>
                <td className="py-3 px-3 text-amber-200">
                  Logs what happened, never why; non-compliant with EU AI Act Art. 12 &amp; 86.
                </td>
                <td className="py-3 pl-3 text-right font-mono text-emerald-400">
                  ● Merkle State Gate
                </td>
              </tr>
              <tr>
                <td className="py-3 pr-3 font-semibold text-slate-100">
                  L4 · Lean 4 Kernel &amp; Artisanal Math Audit
                </td>
                <td className="py-3 px-3 font-mono text-cyan-300 tabular-nums">
                  13M Lines / 11 Days Autoformalized
                </td>
                <td className="py-3 px-3 text-slate-300">
                  Machine-checkable proof correctness (zero-trust deductive kernel).
                </td>
                <td className="py-3 px-3 text-amber-200">
                  Certifies truth without human understanding (UGC &amp; Navier–Stokes crisis).
                </td>
                <td className="py-3 pl-3 text-right font-mono text-emerald-400">
                  ● Mental-Map DAG
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* Interactive Solo-Founder Map-Once Flywheel & Open-Weights Economics */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <section className="lg:col-span-6 bg-[#0D121D] border border-slate-800/90 rounded-lg p-5 space-y-4">
          <div className="border-b border-slate-800 pb-3">
            <span className="text-xs font-mono uppercase text-cyan-400">
              Data Moat &amp; Cost Discipline Simulator
            </span>
            <h2 className="text-base font-bold text-slate-100 font-display mt-0.5">
              02. The Map-Once Protocol Flywheel (Open-Weights + Provenance Gate)
            </h2>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed">
            Every unprotocolled instruction generates a journey map of friction and failure modes, distilling into a reusable, open-weights executable protocol with complete L1–L4 instrumentation (Gemma Scope 2).
          </p>

          <div className="space-y-4 pt-2">
            <div>
              <div className="flex justify-between text-xs font-mono mb-1">
                <label htmlFor="sim-volume">Monthly Gated Instructions</label>
                <span className="text-cyan-300 tabular-nums">
                  {monthlyInstructions.toLocaleString()} runs/mo
                </span>
              </div>
              <input
                id="sim-volume"
                type="range"
                min={200}
                max={10000}
                step={200}
                value={monthlyInstructions}
                onChange={(e) => setMonthlyInstructions(Number(e.target.value))}
                className="w-full accent-cyan-400"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-mono mb-1">
                <label htmlFor="sim-reuse">Distilled Map-Once Protocol Coverage</label>
                <span className="text-emerald-400 tabular-nums">
                  {(protocolReuseRate * 100).toFixed(0)}% offloaded from Frontier API
                </span>
              </div>
              <input
                id="sim-reuse"
                type="range"
                min={0.1}
                max={0.95}
                step={0.01}
                value={protocolReuseRate}
                onChange={(e) => setProtocolReuseRate(parseFloat(e.target.value))}
                className="w-full accent-cyan-400"
              />
            </div>

            <div className="grid grid-cols-3 gap-3 bg-[#080B12] p-3.5 rounded border border-slate-800 font-mono">
              <div>
                <div className="text-[11px] text-slate-400 uppercase">Frontier API Spend</div>
                <div className="text-lg font-bold text-slate-300 tabular-nums">
                  ${baselineMonthlySpend.toFixed(0)}
                </div>
              </div>
              <div>
                <div className="text-[11px] text-slate-400 uppercase">Map-Once Spend</div>
                <div className="text-lg font-bold text-emerald-400 tabular-nums">
                  ${fortressMonthlySpend.toFixed(0)}
                </div>
              </div>
              <div>
                <div className="text-[11px] text-slate-400 uppercase">Cost Reduction</div>
                <div className="text-lg font-bold text-cyan-300 tabular-nums">
                  {costReductionPct.toFixed(1)}%
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* 124-Machine-Hour Execution Sequence */}
        <section className="lg:col-span-6 bg-[#0D121D] border border-slate-800/90 rounded-lg p-5 space-y-4">
          <div className="border-b border-slate-800 pb-3">
            <span className="text-xs font-mono uppercase text-cyan-400">
              124-Machine-Hour Phased Rollout
            </span>
            <h2 className="text-base font-bold text-slate-100 font-display mt-0.5">
              03. Execution Sequence Ahead of EU AI Act Deadlines
            </h2>
          </div>

          <div className="space-y-2.5 text-xs">
            <div className="p-3 rounded bg-[#080B12] border border-slate-800 flex items-center justify-between gap-4">
              <div>
                <div className="font-mono text-emerald-400 font-semibold">
                  Phase 1 · Explanation-Record Schema v0 (~20h)
                </div>
                <div className="text-slate-300 mt-0.5">
                  Instruction envelope + verified events + Dempster–Shafer evidence grading on the provenance gate.
                </div>
              </div>
              <span className="font-mono text-emerald-400 shrink-0">● Active Here</span>
            </div>

            <div className="p-3 rounded bg-[#080B12] border border-slate-800 flex items-center justify-between gap-4">
              <div>
                <div className="font-mono text-emerald-400 font-semibold">
                  Phase 2 · L3 EU AI Act Art. 12 Completeness (~16h)
                </div>
                <div className="text-slate-300 mt-0.5">
                  Tamper-evident Merkle log, monotonic fencing tokens, authority principal context.
                </div>
              </div>
              <span className="font-mono text-emerald-400 shrink-0">● Active Here</span>
            </div>

            <div className="p-3 rounded bg-[#080B12] border border-slate-800 flex items-center justify-between gap-4">
              <div>
                <div className="font-mono text-emerald-400 font-semibold">
                  Phase 3 · L2 Asymmetric Confession &amp; CoT Stack (~24h)
                </div>
                <div className="text-slate-300 mt-0.5">
                  Theorem 1 non-exoneration enforcement + 74.3% confession channel integration.
                </div>
              </div>
              <span className="font-mono text-emerald-400 shrink-0">● Active Here</span>
            </div>

            <div className="p-3 rounded bg-[#080B12] border border-slate-800 flex items-center justify-between gap-4">
              <div>
                <div className="font-mono text-emerald-400 font-semibold">
                  Phase 4 &amp; 5 · Gemma Scope 2 L1 Probes + L4 Mental Map (~64h)
                </div>
                <div className="text-slate-300 mt-0.5">
                  Open-weights probe suite + Moshkovitz bottleneck decomposition &amp; correspondence audit.
                </div>
              </div>
              <span className="font-mono text-emerald-400 shrink-0">● Active Here</span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};
