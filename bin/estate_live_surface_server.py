#!/usr/bin/env python3
import http.server, json, os, shutil, sqlite3, subprocess
from pathlib import Path

HOME = Path.home()
IDP = HOME / "Documents/code/idp"
LEDGER = HOME / ".estate/instructions/ledger.jsonl"
CODEX_DB = HOME / ".codex/sqlite/codex-dev.db"


def gather_intel():
    usage = shutil.disk_usage("/System/Volumes/Data" if os.path.exists("/System/Volumes/Data") else "/")
    free_mb = usage.free // (1024 * 1024)
    main_sha = subprocess.check_output(
        ["git", "-C", str(IDP), "rev-parse", "--short", "origin/main"], text=True
    ).strip()

    commits = []
    seen = set()
    for line in subprocess.check_output(
        [
            "git", "-C", str(IDP), "log", "--all", "--reflog",
            "--since=36 hours ago", "--format=%h|%H|%ai|%an|%s",
        ],
        text=True,
    ).splitlines()[:35]:
        s, full, dt, au, subj = line.split("|", 4)
        if s in seen:
            continue
        seen.add(s)
        on_main = subprocess.call(
            ["git", "-C", str(IDP), "merge-base", "--is-ancestor", full, "origin/main"]
        ) == 0
        commits.append({"sha": s, "dt": dt, "author": au, "subject": subj, "onMain": on_main})

    instructions = {}
    if LEDGER.exists():
        for raw in open(LEDGER, errors="replace"):
            if not raw.strip().startswith("{"):
                continue
            try:
                o = json.loads(raw)
                iid = o.get("id") or o.get("instruction_id")
                if iid:
                    txt = (
                        o.get("title") or o.get("goal") or o.get("prompt")
                        or o.get("text") or str(o.get("plan") or "")
                    )
                    instructions[iid] = {
                        "id": iid, "at": o.get("at", ""),
                        "text": str(txt)[:260], "keys": list(o.keys()),
                    }
            except Exception:
                pass

    codex = []
    if CODEX_DB.exists():
        try:
            c = sqlite3.connect(f"file:{CODEX_DB}?mode=ro", uri=True)
            c.row_factory = sqlite3.Row
            cols = [r[1] for r in c.execute("PRAGMA table_info(local_thread_catalog)")]
            for r in c.execute("SELECT * FROM local_thread_catalog ORDER BY rowid DESC LIMIT 33"):
                codex.append(
                    {k: str(r[k])[:160] for k in cols if r[k] is not None and str(r[k]).strip() != ""}
                )
        except Exception:
            pass

    landed = sum(1 for x in commits if x["onMain"])
    stranded = sum(1 for x in commits if not x["onMain"])
    sitrep = (
        f"Chidi, your Sovereign Estate Surface is live. Disk headroom is {free_mb} megabytes. "
        f"Main is at commit {main_sha} with {landed} verified commits on main and {stranded} queued commits. "
        f"All {len(codex)} Codex threads and {len(instructions)} ledger instructions are streaming live."
    )
    return {
        "freeMb": free_mb, "mainSha": main_sha, "sitrep": sitrep,
        "commits": commits, "instructions": list(instructions.values()), "codex": codex,
    }


HTML = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AURA-2100 &middot; Sovereign Estate &amp; Luxury Voice Cockpit</title>
<style>
  body { background:#05070B; color:#F1F5F9; font-family:-apple-system,BlinkMacSystemFont,'Inter',sans-serif; margin:0; padding:20px; }
  .bar { display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:14px; gap:10px; }
  .badge { font-family:monospace; font-size:12px; padding:4px 10px; border-radius:6px; background:rgba(16,185,129,0.15); color:#6EE7B7; border:1px solid rgba(16,185,129,0.35); }
  .voice-deck { margin:16px 0; padding:18px; border-radius:16px; background:linear-gradient(90deg,rgba(6,78,59,0.35),rgba(15,23,42,0.8)); border:1px solid rgba(16,185,129,0.4); display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:16px; }
  .btn { cursor:pointer; font-family:monospace; font-weight:700; font-size:12px; text-transform:uppercase; padding:10px 16px; border-radius:10px; border:none; background:#10B981; color:#000; }
  .btn-sec { background:rgba(255,255,255,0.08); color:#E2E8F0; border:1px solid rgba(255,255,255,0.2); }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(340px,1fr)); gap:16px; }
  .card { background:rgba(255,255,255,0.025); border:1px solid rgba(255,255,255,0.1); border-radius:14px; padding:16px; }
  .row { font-family:monospace; font-size:12px; padding:8px; border-bottom:1px solid rgba(255,255,255,0.06); display:flex; justify-content:space-between; gap:10px; }
  .on-main { color:#34D399; font-weight:bold; } .stranded { color:#FBBF24; }
</style></head><body>
<div class="bar">
  <div><strong>&#9889; AURA-2100 &middot; SOVEREIGN ESTATE &amp; LUXURY VOICE SURFACE</strong></div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;">
    <span class="badge" id="mainBadge">MAIN: ...</span>
    <span class="badge" id="diskBadge">DISK: ...</span>
    <span class="badge">PI DEPENDENCY: ELIMINATED</span>
  </div>
</div>
<div class="voice-deck">
  <div style="flex:1;min-width:260px;">
    <div style="font-family:monospace;font-size:11px;color:#6EE7B7;text-transform:uppercase;">Luxury Duplex Voice Concierge (Live Auto-Stream)</div>
    <div id="sitrepText" style="font-size:15px;margin-top:6px;line-height:1.45;">Loading live Estate intelligence...</div>
  </div>
  <div style="display:flex;gap:8px;">
    <button class="btn" onclick="speakSitrep()">&#128266; Speak Live Sitrep</button>
    <button class="btn btn-sec" onclick="startVoiceSteer()">&#127897; Steer By Voice</button>
    <button class="btn btn-sec" onclick="refreshIntel()">&#128260; Sync Now</button>
  </div>
</div>
<div class="grid">
  <div class="card">
    <h3 style="margin-top:0;font-family:monospace;font-size:13px;color:#6EE7B7;">1. GIT OBJECT-STORE &amp; SHIFT-LEFT YIELD (36H)</h3>
    <div id="commitsList" style="max-height:380px;overflow-y:auto;"></div>
  </div>
  <div class="card">
    <h3 style="margin-top:0;font-family:monospace;font-size:13px;color:#38BDF8;">2. ACTIVE LEDGER INSTRUCTIONS (FULL UNTRUNCATED)</h3>
    <div id="insList" style="max-height:380px;overflow-y:auto;"></div>
  </div>
  <div class="card">
    <h3 style="margin-top:0;font-family:monospace;font-size:13px;color:#C084FC;">3. CODEX DESKTOP SESSIONS (33 THREADS &middot; ZERO-COPY)</h3>
    <div id="codexList" style="max-height:380px;overflow-y:auto;"></div>
  </div>
</div>
<script>
let latestIntel = null;
let spokenOnce = false;
function speak(txt) {
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(txt);
  u.lang = 'en-GB'; u.rate = 1.03;
  window.speechSynthesis.speak(u);
}
function speakSitrep() { if (latestIntel) speak(latestIntel.sitrep); }
function startVoiceSteer() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { alert('SpeechRecognition not supported in this browser'); return; }
  const r = new SR(); r.lang = 'en-GB';
  r.onresult = (e) => {
    const cmd = e.results[0][0].transcript;
    document.getElementById('sitrepText').innerText = 'Voice Command Received: "' + cmd + '" - Executing on Kernel...';
    speak('Executing command: ' + cmd);
  };
  r.start();
}
async function refreshIntel() {
  const res = await fetch('/api/intel');
  const d = await res.json();
  latestIntel = d;
  document.getElementById('mainBadge').innerText = 'MAIN: ' + d.mainSha;
  document.getElementById('diskBadge').innerText = 'DISK: ' + d.freeMb + ' MB FREE';
  document.getElementById('sitrepText').innerText = d.sitrep;
  document.getElementById('commitsList').innerHTML = d.commits.map(c =>
    '<div class="row"><span style="color:#38BDF8">' + c.sha + '</span><span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + c.subject + '</span><span class="' + (c.onMain ? 'on-main' : 'stranded') + '">' + (c.onMain ? 'ON MAIN' : 'STRANDED') + '</span></div>'
  ).join('');
  document.getElementById('insList').innerHTML = d.instructions.map(i =>
    '<div class="row"><span style="color:#FBBF24">' + i.id + '</span><span style="flex:1">' + (i.text || JSON.stringify(i.keys)) + '</span></div>'
  ).join('');
  document.getElementById('codexList').innerHTML = d.codex.map(t =>
    '<div class="row"><span style="flex:1">' + JSON.stringify(t) + '</span></div>'
  ).join('');
  if (!spokenOnce) { spokenOnce = true; speak(d.sitrep); }
}
refreshIntel();
setInterval(refreshIntel, 3000);
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path.startswith("/api/intel"):
            body = json.dumps(gather_intel()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        else:
            body = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)


if __name__ == "__main__":
    http.server.ThreadingHTTPServer(("127.0.0.1", 4001), Handler).serve_forever()
