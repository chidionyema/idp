use penny_core::ledger::Ledger;
use penny_core::providers::Registry;
use serde_json::Value;

pub fn render_metrics(l: &Ledger) -> String {
    let s = l.snapshot();
    let hit = l.cache_hit_rate();
    format!(
        r#"# HELP penny_requests_total Requests served
# TYPE penny_requests_total counter
penny_requests_total {req}
# HELP penny_cache_eligible_requests_total Requests eligible for the exact-response cache
# TYPE penny_cache_eligible_requests_total counter
penny_cache_eligible_requests_total {eligible}
# HELP penny_cache_hits_total Exact-cache hits
# TYPE penny_cache_hits_total counter
penny_cache_hits_total {hits}
# HELP penny_cache_hit_rate Cache hit ratio
# TYPE penny_cache_hit_rate gauge
penny_cache_hit_rate {hit:.6}
# HELP penny_input_tokens_total Input tokens billed
# TYPE penny_input_tokens_total counter
penny_input_tokens_total {tin}
# HELP penny_output_tokens_total Output tokens billed
# TYPE penny_output_tokens_total counter
penny_output_tokens_total {tout}
# HELP penny_input_tokens_saved_total Input tokens served from cache
# TYPE penny_input_tokens_saved_total counter
penny_input_tokens_saved_total {tsaved}
# HELP penny_spend_usd_total Upstream spend
# TYPE penny_spend_usd_total counter
penny_spend_usd {spend:.6}
# HELP penny_saved_usd_total Avoided spend (conservative)
# TYPE penny_saved_usd_total counter
penny_saved_usd {saved:.6}
"#,
        req = s.requests,
        eligible = s.cache_eligible_requests,
        hits = s.cache_hits,
        hit = hit,
        tin = s.input_tokens,
        tout = s.output_tokens,
        tsaved = s.input_tokens_saved,
        spend = s.spend_usd,
        saved = s.saved_usd,
    )
}

fn html_escape(value: &str) -> String {
    value
        .replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
        .replace('\'', "&#39;")
}

pub fn dashboard_html(l: &Ledger, floor: f64, registry: &Registry) -> String {
    dashboard_html_with_traces(l, floor, registry, &[])
}

pub fn dashboard_html_with_traces(
    l: &Ledger,
    floor: f64,
    registry: &Registry,
    traces: &[Value],
) -> String {
    let s = l.snapshot();
    let hit = l.cache_hit_rate();
    let ineligible = s.requests.saturating_sub(s.cache_eligible_requests);
    let alert = s.cache_eligible_requests > 50 && hit < floor;
    let (color, note) = if alert {
        (
            "#f87171",
            format!(
                "ALERT: hit rate {:.0}% below floor {:.0}% — a dynamic value is likely in the system prompt",
                hit * 100.0,
                floor * 100.0
            ),
        )
    } else if s.cache_eligible_requests == 0 {
        (
            "#facc15",
            format!(
                "No exact-cache eligible requests yet — {ineligible} requests are streaming and stream-response caching is not enabled"
            ),
        )
    } else {
        ("#4ade80", "within floor".to_string())
    };
    let mut routes = String::new();
    for entry in &registry.models {
        let aliases = if entry.model.aliases.is_empty() {
            "—".to_string()
        } else {
            entry.model.aliases.join(", ")
        };
        let fallbacks = if entry.model.fallbacks.is_empty() {
            "none".to_string()
        } else {
            entry.model.fallbacks.join(" → ")
        };
        routes.push_str(&format!(
            "<tr><td>{aliases}</td><td>{lane}</td><td>{context}</td><td>{fallbacks}</td></tr>",
            aliases = html_escape(&aliases),
            lane = html_escape(&entry.canonical_name()),
            context = entry.model.context_window,
            fallbacks = html_escape(&fallbacks),
        ));
    }
    let trace_count = traces.len();
    format!(
        r#"<!doctype html><html><head><meta charset="utf-8"><title>pennyd</title>
<style>body{{font-family:ui-monospace,monospace;background:#0b0f14;color:#d7e0ea;margin:2rem}}
.big{{font-size:2.5rem;color:{color}}}table{{border-collapse:collapse;width:100%}}
th,td{{text-align:left;padding:.45rem;border-bottom:1px solid #263241;white-space:nowrap}}th{{color:#8ea3b8}}
.scroll{{overflow-x:auto}}small{{color:#8ea3b8}}</style></head><body>
<h1>pennyd</h1>
<div class="big">{hitpct:.1}% exact-cache hit</div>
<p>{hits} / {eligible} exact-cache eligible · {ineligible} requests not eligible</p>
<p>spend ${spend:.4} · saved ${saved:.4} · {req} requests · {tin} in / {tout} out tokens · {tsaved} in-tokens from cache</p>
<p>{note}</p>
<h2>Live request ledger <small>({trace_count} rows; refreshes every second)</small></h2>
<div class="scroll"><table>
<thead><tr><th>time</th><th>surface</th><th>status</th><th>edge</th><th>requested</th><th>lane</th>
<th>input</th><th>output</th><th>cache read</th><th>cost</th><th>latency</th><th>request</th><th>error</th></tr></thead>
<tbody id="requestRows"><tr><td colspan="13">loading…</td></tr></tbody></table></div>
<h2>Model routes</h2>
<table><thead><tr><th>Client name</th><th>Resolved lane</th><th>Context</th><th>Declared fallbacks</th></tr></thead>
<tbody>{routes}</tbody></table>
<script>
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}})[c]);
const money = (v) => '$' + Number(v || 0).toFixed(6);
async function refreshLedger() {{
  try {{
    const response = await fetch('/api/requests?limit=200', {{cache: 'no-store'}});
    const payload = await response.json();
    const rows = payload.requests || [];
    document.getElementById('requestRows').innerHTML = rows.length ? rows.map((r) =>
      '<tr><td>' + esc(new Date(Number(r.started_unix) * 1000).toLocaleTimeString()) +
      '</td><td>' + esc(r.surface) + '</td><td>' + esc(r.status) +
      '</td><td>' + esc(r.edge) + '</td><td>' + esc(r.requested_model) +
      '</td><td>' + esc(r.lane || r.canonical_model || '') +
      '</td><td>' + esc(r.in_tokens) + (r.estimated ? ' est' : '') +
      '</td><td>' + esc(r.out_tokens) + (r.estimated ? ' est' : '') +
      '</td><td>' + esc(r.cache_read_tokens) + '</td><td>' + esc(money(r.cost_usd)) +
      '</td><td>' + esc(r.latency_ms) + 'ms</td><td>' + esc(r.req) +
      '</td><td>' + esc(r.error_kind || '') + '</td></tr>'
    ).join('') : '<tr><td colspan="13">no requests yet</td></tr>';
  }} catch (error) {{
    document.getElementById('requestRows').innerHTML =
      '<tr><td colspan="13">ledger unavailable: ' + esc(error.message) + '</td></tr>';
  }}
}}
refreshLedger();
setInterval(refreshLedger, 1000);
</script>
</body></html>"#,
        color = color,
        hitpct = hit * 100.0,
        hits = s.cache_hits,
        eligible = s.cache_eligible_requests,
        ineligible = ineligible,
        spend = s.spend_usd,
        saved = s.saved_usd,
        req = s.requests,
        tin = s.input_tokens,
        tout = s.output_tokens,
        tsaved = s.input_tokens_saved,
        note = note,
        routes = routes,
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn streaming_only_traffic_does_not_raise_exact_cache_alert() {
        let ledger = Ledger::default();
        for _ in 0..201 {
            ledger.charge(45_000, 6, 0.06);
        }

        let html = dashboard_html(&ledger, 0.5, &Registry::default());

        assert!(!html.contains("ALERT"));
        assert!(html.contains("0 / 0 exact-cache eligible"));
        assert!(html.contains("201 requests not eligible"));
    }
}
