# 0050 - The laptop is a thin client: the router lives in the estate, Cloudflare first

Date: 2026-11-05
Status: accepted (founder ruling 2026-11-04)
Related: 0034 (workloads are placed by the free tier), 0040 (the director runs on the laptop
until the loop is proven), `docs/specs/2026-10-24-estate-cloud-migration-plan.md` (the thin-client
plan that was interrupted by the cluster loss), `docs/incidents/2026-10-29-the-cluster-lost-its-control-plane.md`

---

## Context

The estate's LLM router ended up running on the MacBook three ways at once: the LiteLLM front
(:4000), the LiteLLM slot (:4002), and the Rust sovereign router (:4102). Every agent session on
the box - seven pi processes, opencode, Claude Code, Kimi Code, Codex - depends on that stack,
and every hour it runs on an 8 GB machine under simultaneous heavy sessions it drives the box
into the saturation signature measured on 2026-10-24 and re-measured tonight
(load 300-522, swap 5.4/6.1 GB full, pages free on the floor). The founder has now ruled it:

> the router should not be running on this machine - on the macbook, cloudflare first

## Decision

**The MacBook is a client of the router, never its home.**

1. **The router's home is the estate's own free-tier node** - the single-node k3s on one A1 VM
   (#7393, approved as the OKE replacement while the OKE control plane is gone, #7387). The
   router stack (LiteLLM + lane registry) runs there, once, behind the estate's Cloudflare edge
   (`llm.mumchimp.com`, tunnel `d77a438e`).
2. **Cloudflare first.** On the MacBook, every caller points at `llm.mumchimp.com` first. When
   the edge is unreachable, callers fall back to **direct provider lanes with vault keys**
   (`scripts/secret-load env name KEY`), not to another local router.
3. **The tunnel connector never runs on the MacBook.** The only valid edge in transit to
   `llm.mumchimp.com` originates on the node. The MacBook publishes nothing: `~/.cloudflared/config.yml`
   stays the catch-all 404. An edge terminating on the laptop would also **loop** through the
   laptop router's own cloud-first chain (front's `User-Agent: estate-router-front/1.0` is the
   one signature the edge allows, so a recursor would build one hop per request forever).
4. **The local stack is the fallback of last resort, for the interregnum only.** The front/slot
   door at 127.0.0.1 stays up while the replacement node does not exist, because it is the only
   working voice the fleet has. The moment the node's router answers `llm.mumchimp.com` with a
   real completion, the laptop stack is uninstalled (`bin/litellm-local uninstall`) and the
   `com.estate.sovereign-router` launchd label is bootstrapped out. **Done = that uninstall has
   happened and the founder can see the fleet's voice arrive from the edge.**

## Consequences

**Positive.** The router stops competing with the fleet for 8 GB and stops being the reason
sessions die; one router, one edge, one voice to watch; the free-tier ladder's rung (always-on
node) matches the router's load profile; a connector on the node means the MacBook's own
router-outage failures stop taking every session with them.

**Negative, accepted.**

1. **One hop more for every lane call from this laptop** while it lives in the estate's node.
   Agent calls get slightly slower; accepted.
2. **During the interregnum, "Cloudflare first" degrades to "Cloudflare never."** Until the node
   exists, the edge answers 530/1033, so the workable paths tonight are the laptop-local
   fallback (what the fleet is on) and provider lanes direct from the vault. Documented - not
   hidden.
3. **The laptop-local stack still degrades the box under saturation** until the uninstall door
   opens. The front's load gate (refuse above 32) is the honest guard meanwhile.

## Enforcement

- The decision carries into the runbook: `docs/runbooks/llm-router-failure-modes.md` names the
  loop rule (no tunnel connector -> no laptop ingress) and the uninstall door.
- `/fleet` shows the router's voice source (edge vs laptop fallback). When the edge is live, the
  laptop stack must not be reachable on any public name.
- A chase-lane whose `paths` include `docs/decisions/0050*` may add this file only with the two
  trailers `Claim:` and `Agent:` in the commit.
