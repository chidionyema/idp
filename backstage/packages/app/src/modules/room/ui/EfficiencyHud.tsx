// TOKEN EFFICIENCY, LIVE, on the Reactor (/fleet renders FleetReactorApp, not home/Fleet.tsx).
// Every number is a poll of the backend's ledger. Before the first frame the HUD draws NOTHING
// rather than a card that says it has nothing (idp#6794: empty cards were the clutter). A failed
// feed is still news, so it is said in one line -- never a figure it did not receive.
import { useEfficiencyFrame } from '../../home/EfficiencyPanel';

export default function EfficiencyHud() {
  const { frame, error } = useEfficiencyFrame();
  if (!frame) {
    return error ? (
      <div data-testid="efficiency-hud" className="self-end px-2 py-0.5 rounded-full bg-black/55 border border-white/10 text-[12px] font-mono text-white/60 select-none pointer-events-none">
        token efficiency · {error}
      </div>
    ) : null;
  }
  const broken = frame.prefix_checked ? Math.round((frame.prefix_broken / frame.prefix_checked) * 100) : 0;
  return (
    <div
      data-testid="efficiency-hud"
      className="w-full rounded-xl bg-black/55 border border-white/10 backdrop-blur-md p-2 select-none pointer-events-none"
    >
      <div className="flex items-baseline gap-2 px-1 pb-1">
        <span className="text-[12px] font-mono uppercase tracking-widest text-white/60 flex-1">token efficiency · live</span>
        <span className="text-[12px] font-mono text-white/60">last {frame.since}</span>
      </div>
      <div className="px-1 flex flex-col gap-0.5 text-[12px] font-mono text-white/70">
        <div>{frame.calls_billed} calls · <span className="text-emerald-300/90">{frame.cache_hit_pct.toFixed(1)}% cache hit</span></div>
        <div>router cut {frame.router_bytes_saved} B · prefix broken {broken}% ({frame.prefix_broken}/{frame.prefix_checked})</div>
      </div>
    </div>
  );
}
