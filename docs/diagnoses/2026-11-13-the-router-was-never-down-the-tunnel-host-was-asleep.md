# Incident: "the router is down" was a label, not a measurement (2026-11-10 to 2026-11-13)

Status: DIAGNOSED. Debugging pack DBG-038; falsifier `tests/test_ladder_legs_name_their_real_origin.py`
(fails today, as it must until the leg is renamed). Founder, 2026-11-13 08:11: an investor meeting
was cancelled on the strength of "router is down", two words that named no component, no code and no
time, repeated by every agent.

## What happened

All times UTC.

| when | what | source |
|---|---|---|
| 10-28 | The fallback ladder declares four llm-router legs: `cloud (OKE LiteLLM)` at `llm.{zone}`, the lifeboat, groq, the laptop front | `platform/ladder/critical-lanes.json`, 99034e91 |
| 10-29 02:07 | Oracle removes the OKE entitlement; the cluster never returns | `docs/incidents/2026-10-29-the-cluster-lost-its-control-plane.md` |
| 11-08 | "a declared-but-never-provisioned home is not a dead lane": the unbuilt lifeboat stops counting | 9bcd31c3 (#7813) |
| 11-10 | First drill failure of the series | estate-homes-drill run 42799150293 |
| 11-12 | A named Cloudflare tunnel serves `llm.mumchimp.com`; its connector runs on the founder's machine; `/health` 200 | argon `docs/ESTATE_MAP.md` 102-105, `docs/DAILY_LOG_2026-11-12.md` 88 |
| 11-12 22:43 | idp#8022 opens: `[lane] llm-router: a lane is down`; DoF locks every agent to repair-only | idp#8022, `bin/dof-gate --lease` |
| 11-12 23:47 | Oracle has no ACTIVE cluster | otto-parity run 43331643572 |
| 11-13 02:55 | Drill: `MEASURED_FAIL cloud (OKE LiteLLM) HTTP 530`; lifeboat NOT_PROVISIONED; groq 200; laptop front not reachable from the runner | idp#8022 comment |
| 11-13 06:00-08:06 | Agents (Gemini, Claude) repeat "router is down" and "OKE origin"; Gemini rebuilds a router in Python; Claude saves the OKE reading as a fact | founder-supplied transcripts, argon `.genesis/sources/` |
| 11-13 10:25 | The fact is corrected: the leg is a tunnel to the founder's machine, not OKE | argon fb4700f (PR #108) |

## Cause

1. **Stale label became the diagnosis.** The leg serving `llm.{zone}` is still named `cloud (OKE LiteLLM)`,
   provider `oracle-oke`. Cloudflare's 530 means "origin unreachable": the tunnel's connector host was
   offline (the drill ran at 02:55). Agents read the label, not the code.
2. **No cloud leg survives the host sleeping.** The lifeboat was declared on 10-28 and never built; on
   11-08 the ladder stopped counting it rather than building it.
3. **Monitoring did not monitor.** The drill ran 15 of 188 scheduled times (8.0%) on 11-09 to 11-13 and
   exited `success` while the ladder read UNPROVEN (run 43355364025).
4. **Status words without coordinates.** "Router is down" names six possible components; it passed as
   fact because nothing refused it.

## Not established

- Which host runs the tunnel connector today, and what serves behind it (LiteLLM :4000 or pennyd :4200).
- Whether `llm.mumchimp.com` answers 200 now; this workspace cannot reach it (proxy refuses the host).

## Remedy

| # | change | proof | state |
|---|---|---|---|
| R1 | rename the leg to its real origin (tunnel, fate `host:laptop`) | DBG-038 falsifier passes | open (idp writes refused by ruleset 24071703) |
| R2 | build the lifeboat Worker so one cloud leg survives the host sleeping | 2 providers 200 from the edge, 3 spaced | open |
| R3 | drill exit status = ladder state | run conclusion `failure` while UNPROVEN | open |
| R4 | status claims carry component, code, time and 3 sources | argon `.genesis/facts.json` F01-F02; turn gate on argon main | partly done |
