use penny_core::ledger::Ledger;

pub fn render_metrics(l: &Ledger) -> String {
    let s = l.snapshot();
    let hit = l.cache_hit_rate();
    format!(
        r#"# HELP penny_requests_total Requests served
# TYPE penny_requests_total counter
penny_requests_total {req}
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
        hits = s.cache_hits,
        hit = hit,
        tin = s.input_tokens,
        tout = s.output_tokens,
        tsaved = s.input_tokens_saved,
        spend = s.spend_usd,
        saved = s.saved_usd,
    )
}

pub fn dashboard_html(l: &Ledger, floor: f64) -> String {
    let s = l.snapshot();
    let hit = l.cache_hit_rate();
    let alert = s.requests > 50 && hit < floor;
    let (color, note) = if alert {
        (
            "#f87171",
            format!(
                "ALERT: hit rate {:.0}% below floor {:.0}% — a dynamic value is likely in the system prompt",
                hit * 100.0,
                floor * 100.0
            ),
        )
    } else {
        ("#4ade80", "within floor".to_string())
    };
    format!(
        r#"<!doctype html><html><head><meta charset="utf-8"><title>pennyd</title>
<meta http-equiv="refresh" content="5">
<style>body{{font-family:ui-monospace,monospace;background:#0b0f14;color:#d7e0ea;margin:2rem}}
.big{{font-size:2.5rem;color:{color}}}</style></head><body>
<h1>pennyd</h1>
<div class="big">{hitpct:.1}% cache hit</div>
<p>spend ${spend:.4f} · saved ${saved:.4f} · {req} requests · {tin} in / {tout} out tokens · {tsaved} in-tokens from cache</p>
<p>{note}</p>
</body></html>"#,
        color = color,
        hitpct = hit * 100.0,
        spend = s.spend_usd,
        saved = s.saved_usd,
        req = s.requests,
        tin = s.input_tokens,
        tout = s.output_tokens,
        tsaved = s.input_tokens_saved,
        note = note,
    )
}
