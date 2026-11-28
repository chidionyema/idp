//! meridian-fitness -- the writer half of the admission gate (idp#3525).
//!
//! `bin/legion-admit --harness auto` refuses every route without a fresh
//! `estate.lane-fitness.v1` record. Nothing in the tree wrote one, so after #8659 merged the gate
//! refused 100% of issue-triggered runs with `NO_FIT_LANE` and the cloud lane was dead.
//!
//! This binary decides, for every route the gate will consider, whether that lane can do the
//! mission its class runs, and writes one record per route:
//!
//! * the route set is `auto_candidates`'s predicate -- OpenAI-compatible bearer providers, a
//!   measured `class` of `free` or `paid`, context >= 65536, a finite catalogue price;
//! * a `paid` route is measured with the launch mission (repair a one-line bug, `golden-patch-1`);
//! * a `free` route is measured with the readiness mission, so a lane that answers a probe and
//!   returns no patch still lands `UNFIT`/`empty-patch` -- the exact failure the gate exists for
//!   (openrouter nemotron-3.5-lightning:free, measured 2026-11-27);
//! * every record carries the launch settings the worker runs (context 32768, max_tokens 4096),
//!   because a record measured under other settings is refused as `measured-under-other-settings`.
//!
//! No crates.io dependency: the record format is schema-pinned JSON, and a registry outage must
//! never decide whether the cloud lane can be admitted. The registry TOML and the provider calls
//! are handled by the bare `python3` the estate already requires (the same interpreter the
//! Greenlane's judge uses to run `tests/legion_fitness_gate.py`).
//!
//! A missing or refused credential is the founder's secret boundary: one line naming the exact
//! secret variable, exit 1, no retry.

use std::collections::BTreeSet;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, ExitCode};
use std::time::{SystemTime, UNIX_EPOCH};

const SCHEMA: &str = "estate.lane-fitness.v1";
const LAUNCH_CONTEXT_CAP: i64 = 32768;
const LAUNCH_MAX_TOKENS: i64 = 4096;
const MIN_CONTEXT: i64 = 65536;
const MISSION_LAUNCH: &str = "golden-patch-1";
/// The free floor proves reachability by answering this tool call.
const READINESS_TOOL: &str = "legion_ready";

/// Reads the provider registry and answers one JSON object per line. Kept here, not in a
/// dependency, so the writer shares the bare-python contract the gate's own measure uses.
const REGISTRY_READER: &str = r##"
import glob, json, os, sys

# The interpreter is not ours to choose: the runner may have 3.9 (no tomllib) or 3.12.
# A writer whose admission depends on the patch version of python3 is the same class of
# fragility as one that depends on a crates.io fetch, so parse the flat provider shape
# ourselves when tomllib is absent. Both paths must agree; a mismatch is a hard error.
try:
    import tomllib
except ImportError:
    tomllib = None

def _scalar(raw):
    raw = raw.strip()
    if not raw:
        return ""
    if raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    if raw.startswith("["):
        inner = raw[1:raw.rindex("]")] if "]" in raw else ""
        return [_scalar(p) for p in inner.split(",") if p.strip()]
    for cast in (int, float):
        try:
            return cast(raw)
        except ValueError:
            pass
    if raw in ("true", "false"):
        return raw == "true"
    return raw

def _fallback_parse(text):
    spec, table, current = {}, None, None
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip() if not line.lstrip().startswith(("\"", "'")) else line.strip()
        if not line:
            continue
        if line == "[[models]]":
            current = {}
            spec.setdefault("models", []).append(current)
            table = current
            continue
        if line.startswith("[") and line.endswith("]"):
            table = spec.setdefault(line[1:-1].strip(), {})
            current = None
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        (current if current is not None else (table if table is not None else spec))[
            key.strip()
        ] = _scalar(value)
    return spec

def load(path):
    raw = open(path, "rb").read()
    if tomllib is not None:
        return tomllib.loads(raw.decode("utf-8"))
    return _fallback_parse(raw.decode("utf-8"))

out = []
for path in sorted(glob.glob(os.path.join(sys.argv[1], "*.toml"))):
    try:
        spec = load(path)
    except Exception as exc:
        print(json.dumps({"note": f"{os.path.basename(path)}: unreadable TOML: {exc}"}))
        continue
    stem = os.path.basename(path)[:-5]
    if spec.get("id") != stem:
        print(json.dumps({"note": f"{stem}: provider id {spec.get('id')!r} does not match the file name"}))
        continue
    if spec.get("dialect") != "openai":
        continue
    auth = spec.get("auth") or {}
    key_env = auth.get("key_env", "")
    if auth.get("kind") != "bearer" or not key_env.endswith("_API_KEY"):
        continue
    base_url = (spec.get("base_url") or "").rstrip("/")
    request_path = spec.get("request_path") or ""
    if not request_path.startswith("/") or not request_path.endswith("/chat/completions"):
        continue
    # Plain https only. One exception, for the end-to-end measure: a registry that was
    # explicitly pointed at a loopback harness. Production never sets it, and a loopback
    # host cannot leak a credential to a third party.
    loopback_ok = os.environ.get("MERIDIAN_FITNESS_ALLOW_LOOPBACK") == "1" and (
        base_url.startswith("http://127.0.0.1:") or base_url.startswith("http://localhost:")
    )
    if "@" in base_url or not (base_url.startswith("https://") or loopback_ok):
        continue
    base = base_url + request_path[: -len("/chat/completions")]
    for model in spec.get("models") or []:
        cls = model.get("class")
        if cls not in ("free", "paid"):
            continue
        if int(model.get("context_window") or 0) < 65536:
            continue
        try:
            price_in = float(model.get("price_in_per_mtok", -1))
            price_out = float(model.get("price_out_per_mtok", -1))
        except (TypeError, ValueError):
            continue
        if cls == "free" and (price_in != 0 or price_out != 0):
            continue
        if cls == "paid" and (price_in < 0 or price_out < 0):
            continue
        print(json.dumps({
            "provider": spec["id"], "model": model["id"], "base": base,
            "key_env": key_env, "context": int(model["context_window"]), "class": cls,
        }))
"##;

/// One qualification call. Prints exactly one JSON object; never prints the key.
const QUALIFIER: &str = r##"
import json, os, sys, time, urllib.error, urllib.request
req_spec = json.loads(sys.argv[1])
key = os.environ.get(req_spec["key_env"], "")
payload = req_spec["payload"]
body = json.dumps(payload).encode()
req = urllib.request.Request(
    req_spec["base"] + "/chat/completions", data=body, method="POST",
    headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
)
started = time.time()
def answer(code, reply):
    print(json.dumps({"http": code, "reply": reply, "latency_ms": int((time.time() - started) * 1000)}))
try:
    with urllib.request.urlopen(req, timeout=float(req_spec["timeout"])) as resp:
        answer(resp.status, json.loads(resp.read(1024 * 1024) or b"{}"))
except urllib.error.HTTPError as exc:
    answer(exc.code, None)
except Exception as exc:
    answer(None, {"error": type(exc).__name__})
"##;

#[derive(Debug, Clone)]
struct Route {
    provider: String,
    model: String,
    base: String,
    key_env: String,
    context: i64,
    class: String,
}

impl Route {
    fn mission(&self) -> &'static str {
        if self.class == "paid" {
            MISSION_LAUNCH
        } else {
            "readiness-1"
        }
    }
}

struct Args {
    fitness_dir: PathBuf,
    providers_dir: PathBuf,
    ttl_hours: i64,
    timeout_s: u64,
    secret_template: String,
    now: i64,
}

fn main() -> ExitCode {
    let args = match parse_args() {
        Ok(a) => a,
        Err(msg) => {
            eprintln!("lane-fitness: {msg}");
            return ExitCode::from(2);
        }
    };
    let (routes, notes) = match load_routes(&args) {
        Ok(v) => v,
        Err(msg) => {
            eprintln!("lane-fitness: {msg}");
            return ExitCode::from(2);
        }
    };
    for note in &notes {
        eprintln!("lane-fitness: {note}");
    }
    if let Err(e) = fs::create_dir_all(&args.fitness_dir) {
        eprintln!("lane-fitness: cannot create {}: {e}", args.fitness_dir.display());
        return ExitCode::from(2);
    }

    let mut written = 0usize;
    let mut fit = 0usize;
    let mut unfit = 0usize;
    let mut refused: BTreeSet<String> = BTreeSet::new();

    for route in &routes {
        let key = std::env::var(&route.key_env).unwrap_or_default();
        if key.trim().is_empty() {
            refused.insert(args.secret_template.replace("{key_env}", &route.key_env));
            continue;
        }
        let outcome = qualify(route, &key, args.timeout_s);
        if outcome.refused_credential {
            refused.insert(args.secret_template.replace("{key_env}", &route.key_env));
            continue;
        }
        let record = format!(
            "{{\"schema\":\"{schema}\",\"provider\":\"{provider}\",\"model\":\"{model}\",\
             \"context_window\":{ctx},\"max_tokens\":{max_tokens},\"verdict\":\"{verdict}\",\
             \"reason\":\"{reason}\",\"mission\":\"{mission}\",\"checked_at\":\"{checked_at}\",\
             \"expires_at\":\"{expires_at}\",\"latency_ms\":{latency}}}\n",
            schema = SCHEMA,
            provider = json_escape(&route.provider),
            model = json_escape(&route.model),
            ctx = route.context.min(LAUNCH_CONTEXT_CAP),
            max_tokens = LAUNCH_MAX_TOKENS,
            verdict = outcome.verdict,
            reason = json_escape(&outcome.reason),
            mission = route.mission(),
            checked_at = utc_iso(args.now),
            expires_at = utc_iso(args.now + args.ttl_hours * 3600),
            latency = outcome.latency_ms,
        );
        let path = record_path(&args.fitness_dir, route);
        match fs::write(&path, record) {
            Ok(()) => {
                written += 1;
                if outcome.verdict == "FIT" {
                    fit += 1;
                } else {
                    unfit += 1;
                }
                eprintln!(
                    "lane-fitness: {} {} -> {} ({})",
                    route.provider, route.model, outcome.verdict, outcome.reason
                );
            }
            Err(e) => {
                eprintln!("lane-fitness: cannot write {}: {e}", path.display());
                return ExitCode::from(2);
            }
        }
    }

    let missing: Vec<String> = refused.iter().cloned().collect();
    println!(
        "{{\"dir\":\"{}\",\"routes\":{},\"written\":{},\"fit\":{},\"unfit\":{},\"missing_or_refused\":[{}]}}",
        json_escape(&args.fitness_dir.display().to_string()),
        routes.len(),
        written,
        fit,
        unfit,
        missing
            .iter()
            .map(|m| format!("\"{}\"", json_escape(m)))
            .collect::<Vec<_>>()
            .join(",")
    );
    if routes.is_empty() {
        println!("ESCALATE/1 founder secret boundary: missing_or_refused=none; the registry offers no route to measure");
        return ExitCode::from(1);
    }
    if !missing.is_empty() {
        if fit > 0 {
            eprintln!(
                "lane-fitness: notice: optional provider secrets unset/refused ({}); admitting with fit={fit}",
                missing.join(",")
            );
            return ExitCode::SUCCESS;
        }
        println!(
            "ESCALATE/1 founder secret boundary: missing_or_refused={}",
            missing.join(",")
        );
        return ExitCode::from(1);
    }
    ExitCode::SUCCESS
}

fn parse_args() -> Result<Args, String> {
    let mut args = Args {
        fitness_dir: PathBuf::new(),
        providers_dir: PathBuf::from("platform/llm/pennyd/providers"),
        ttl_hours: 26,
        timeout_s: 90,
        secret_template: "{key_env}".to_string(),
        now: 0,
    };
    let mut have_dir = false;
    let mut it = std::env::args().skip(1);
    while let Some(flag) = it.next() {
        let mut value = || it.next().ok_or_else(|| format!("{flag} needs a value"));
        match flag.as_str() {
            "--fitness-dir" => {
                args.fitness_dir = PathBuf::from(value()?);
                have_dir = true;
            }
            "--providers-dir" => args.providers_dir = PathBuf::from(value()?),
            "--ttl-hours" => args.ttl_hours = value()?.parse().map_err(|_| "ttl must be hours")?,
            "--timeout" => args.timeout_s = value()?.parse().map_err(|_| "timeout must be seconds")?,
            "--secret-name-template" => args.secret_template = value()?,
            "--now" => args.now = value()?.parse().map_err(|_| "now must be epoch seconds")?,
            other => return Err(format!("unknown argument {other}")),
        }
    }
    if !have_dir {
        return Err("--fitness-dir is required (the directory bin/legion-admit reads)".to_string());
    }
    if args.now == 0 {
        args.now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs() as i64)
            .unwrap_or(0);
    }
    Ok(args)
}

fn python() -> String {
    std::env::var("MERIDIAN_FITNESS_PYTHON").unwrap_or_else(|_| "python3".to_string())
}

/// The same selection `auto_candidates` makes, so a record can never describe a route the gate
/// does not consider.
fn load_routes(args: &Args) -> Result<(Vec<Route>, Vec<String>), String> {
    let out = Command::new(python())
        .arg("-c")
        .arg(REGISTRY_READER)
        .arg(&args.providers_dir)
        .output()
        .map_err(|e| format!("cannot read the registry: {e}"))?;
    if !out.status.success() {
        return Err(format!(
            "registry reader failed: {}",
            String::from_utf8_lossy(&out.stderr).trim()
        ));
    }
    let mut routes = Vec::new();
    let mut notes = Vec::new();
    for line in String::from_utf8_lossy(&out.stdout).lines() {
        if line.trim().is_empty() {
            continue;
        }
        if let Some(note) = field(line, "note") {
            notes.push(note);
            continue;
        }
        if let (Some(provider), Some(model), Some(base), Some(key_env), Some(class)) = (
            field(line, "provider"),
            field(line, "model"),
            field(line, "base"),
            field(line, "key_env"),
            field(line, "class"),
        ) {
            routes.push(Route {
                provider,
                model,
                base,
                key_env,
                context: field(line, "context").and_then(|c| c.parse().ok()).unwrap_or(0),
                class,
            });
        }
    }
    routes.sort_by(|a, b| (&a.provider, &a.model).cmp(&(&b.provider, &b.model)));
    Ok((routes, notes))
}

/// One string/number field out of the flat JSON the reader prints. The shape is fixed by our own
/// reader, so this stays a search for `"key":` and its value -- never a general parser.
fn field(line: &str, key: &str) -> Option<String> {
    let needle = format!("\"{key}\":");
    let at = line.find(&needle)? + needle.len();
    let rest = line[at..].trim_start();
    if let Some(stripped) = rest.strip_prefix('"') {
        let mut out = String::new();
        let mut chars = stripped.chars();
        while let Some(c) = chars.next() {
            match c {
                '"' => return Some(out),
                '\\' => match chars.next()? {
                    'n' => out.push('\n'),
                    't' => out.push('\t'),
                    other => out.push(other),
                },
                other => out.push(other),
            }
        }
        None
    } else {
        let end = rest.find(|c| c == ',' || c == '}').unwrap_or(rest.len());
        Some(rest[..end].trim().to_string())
    }
}

struct Outcome {
    verdict: &'static str,
    reason: String,
    latency_ms: u64,
    refused_credential: bool,
}

fn qualify(route: &Route, key: &str, timeout_s: u64) -> Outcome {
    let payload = if route.class == "paid" {
        format!(
            "{{\"model\":\"{}\",\"messages\":[{{\"role\":\"user\",\"content\":\"{}\"}}],\
             \"max_tokens\":{},\"temperature\":0}}",
            json_escape(&route.model),
            json_escape(GOLDEN_PROMPT),
            LAUNCH_MAX_TOKENS
        )
    } else {
        format!(
            "{{\"model\":\"{}\",\"messages\":[{{\"role\":\"user\",\"content\":\"Call legion_ready \
             with {{\\\"ready\\\":true}}.\"}}],\"tools\":[{{\"type\":\"function\",\"function\":\
             {{\"name\":\"legion_ready\",\"description\":\"Readiness proof\",\"parameters\":\
             {{\"type\":\"object\",\"properties\":{{\"ready\":{{\"type\":\"boolean\"}}}},\
             \"required\":[\"ready\"]}}}}}}],\"tool_choice\":\"required\",\"max_tokens\":256,\
             \"temperature\":0}}",
            json_escape(&route.model)
        )
    };
    let spec = format!(
        "{{\"base\":\"{}\",\"key_env\":\"{}\",\"payload\":{},\"timeout\":{}}}",
        json_escape(&route.base),
        json_escape(&route.key_env),
        payload,
        timeout_s
    );
    let out = Command::new(python())
        .arg("-c")
        .arg(QUALIFIER)
        .arg(spec)
        .env(&route.key_env, key)
        .output();
    let out = match out {
        Ok(o) => o,
        Err(e) => {
            return Outcome {
                verdict: "UNFIT",
                reason: format!("transport:{e}"),
                latency_ms: 0,
                refused_credential: false,
            }
        }
    };
    let line = String::from_utf8_lossy(&out.stdout);
    let latency_ms: u64 = field(line.trim(), "latency_ms")
        .and_then(|v| v.parse().ok())
        .unwrap_or(0);
    let http: Option<u16> = field(line.trim(), "http").and_then(|v| v.parse().ok());
    match http {
        None if field(line.trim(), "http").is_some() => Outcome {
            verdict: "UNFIT",
            reason: "transport".to_string(),
            latency_ms,
            refused_credential: false,
        },
        None => Outcome {
            verdict: "UNFIT",
            reason: "transport".to_string(),
            latency_ms,
            refused_credential: false,
        },
        Some(code) if code == 401 || code == 403 => Outcome {
            verdict: "UNFIT",
            reason: "authentication".to_string(),
            latency_ms,
            refused_credential: true,
        },
        Some(code) if code == 402 => Outcome {
            verdict: "UNFIT",
            reason: "funding".to_string(),
            latency_ms,
            refused_credential: false,
        },
        Some(code) if code == 429 => Outcome {
            verdict: "UNFIT",
            reason: "rate-limited".to_string(),
            latency_ms,
            refused_credential: false,
        },
        Some(code) if !(200..300).contains(&code) => Outcome {
            verdict: "UNFIT",
            reason: format!("http-{code}"),
            latency_ms,
            refused_credential: false,
        },
        Some(_) => {
            let reply = line.trim();
            if field(reply, "error").is_some() {
                return Outcome {
                    verdict: "UNFIT",
                    reason: "invalid-response".to_string(),
                    latency_ms,
                    refused_credential: false,
                };
            }
            let content = reply_content(reply);
            let passed = if route.class == "paid" {
                content.contains(GOLDEN_EXPECT)
            } else {
                readiness_call(reply)
            };
            if passed {
                Outcome {
                    verdict: "FIT",
                    reason: route.mission().to_string(),
                    latency_ms,
                    refused_credential: false,
                }
            } else if content.trim().is_empty() {
                Outcome {
                    verdict: "UNFIT",
                    reason: "empty-patch".to_string(),
                    latency_ms,
                    refused_credential: false,
                }
            } else {
                Outcome {
                    verdict: "UNFIT",
                    reason: "wrong-patch".to_string(),
                    latency_ms,
                    refused_credential: false,
                }
            }
        }
    }
}

const GOLDEN_PROMPT: &str = "You are qualifying a coding lane.\\n\\nHere is a Python file with one \
bug:\\n\\ndef greet(name):\\n    return \\\"hello \\\" + nam\\n\\nReply with ONLY the corrected \
return line. No prose, no explanation.";
const GOLDEN_EXPECT: &str = "\"hello \" + name";

/// The assistant text of an OpenAI-shaped reply, unescaped.
fn reply_content(reply: &str) -> String {
    match field(reply, "content") {
        Some(c) if c != "null" => c,
        _ => String::new(),
    }
}

/// The free floor answers a tool call whose `legion_ready` argument is `{"ready": true}`.
fn readiness_call(reply: &str) -> bool {
    // Structural, not a substring hunt: a JSON encoder is free to put spaces around
    // `:` and to reorder keys, so a scan for `"name":"legion_ready"` decides the
    // verdict based on which encoder the provider used. Read the argument instead.
    let at = match reply.find("\"tool_calls\"") {
        Some(i) => i,
        None => return false,
    };
    let tail = &reply[at..];
    let mut rest = tail;
    while let Some(pos) = rest.find("\"function\"") {
        let f = &rest[pos..];
        let name_ok = field(f, "name").as_deref() == Some(READINESS_TOOL);
        if name_ok {
            let args = field(f, "arguments").unwrap_or_default();
            let ready = field(&args, "ready").as_deref() == Some("true");
            if ready {
                return true;
            }
        }
        rest = &f["\"function\"".len()..];
    }
    false
}

fn record_path(dir: &Path, route: &Route) -> PathBuf {
    let slug = |s: &str| {
        s.chars()
            .map(|c| if c.is_ascii_alphanumeric() { c.to_ascii_lowercase() } else { '-' })
            .collect::<String>()
    };
    dir.join(format!("{}__{}.json", slug(&route.provider), slug(&route.model)))
}

fn json_escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out
}

fn utc_iso(epoch: i64) -> String {
    let days = epoch.div_euclid(86_400);
    let secs = epoch.rem_euclid(86_400);
    let (y, m, d) = civil_from_days(days);
    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}Z",
        y,
        m,
        d,
        secs / 3600,
        (secs % 3600) / 60,
        secs % 60
    )
}

fn civil_from_days(z: i64) -> (i64, u32, u32) {
    let z = z + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let m = if mp < 10 { mp + 3 } else { mp - 9 } as u32;
    (if m <= 2 { y + 1 } else { y }, m, d)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn utc_iso_is_the_shape_admission_parses() {
        // Expected strings are derived from python's own UTC conversion, not hand-written.
        assert_eq!(utc_iso(1_795_833_600), "2026-11-28T02:40:00Z");
        assert_eq!(utc_iso(0), "1970-01-01T00:00:00Z");
        assert_eq!(utc_iso(1_795_833_600 + 3600 * 26), "2026-11-29T04:40:00Z");
        // A leap-free year boundary, so the civil-date arithmetic is exercised away from 2026.
        assert_eq!(utc_iso(1_704_067_199), "2023-12-31T23:59:59Z");
    }

    #[test]
    fn record_names_are_stable() {
        let r = Route {
            provider: "openrouter".into(),
            model: "nvidia/nemotron-3.5-lightning:free".into(),
            base: String::new(),
            key_env: String::new(),
            context: 1_000_000,
            class: "free".into(),
        };
        assert_eq!(
            record_path(Path::new("/tmp/x"), &r).file_name().unwrap().to_str().unwrap(),
            "openrouter__nvidia-nemotron-3-5-lightning-free.json"
        );
    }

    #[test]
    fn a_paid_record_names_the_launch_mission_and_a_free_one_its_readiness() {
        let mut r = Route {
            provider: "deepseek".into(),
            model: "deepseek-flash".into(),
            base: String::new(),
            key_env: "DEEPSEEK_API_KEY".into(),
            context: 1_000_000,
            class: "paid".into(),
        };
        assert_eq!(r.mission(), MISSION_LAUNCH);
        r.class = "free".into();
        assert_eq!(r.mission(), "readiness-1");
    }

    #[test]
    fn json_escapes_never_break_the_record() {
        assert_eq!(json_escape("a\"b\\c\nd"), "a\\\"b\\\\c\\nd");
        assert_eq!(
            json_escape("nvidia/nemotron-3.5-lightning:free"),
            "nvidia/nemotron-3.5-lightning:free"
        );
    }

    #[test]
    fn flat_fields_are_read_back_the_way_the_reader_writes_them() {
        let line = r#"{"provider":"groq","model":"qwen/qwen3.8-27b","context":131072,"class":"free"}"#;
        assert_eq!(field(line, "provider").as_deref(), Some("groq"));
        assert_eq!(field(line, "context").as_deref(), Some("131072"));
        assert_eq!(field(line, "missing"), None);
    }

    #[test]
    fn readiness_needs_the_named_tool_call() {
        assert!(readiness_call(
            r#"{"choices":[{"message":{"tool_calls":[{"function":{"name":"legion_ready","arguments":"{\"ready\":true}"}}]}}]}"#
        ));
        assert!(!readiness_call(r#"{"choices":[{"message":{"content":""}}]}"#));
    }
}
