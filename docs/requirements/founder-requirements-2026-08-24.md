# Founder requirements sweep, 2026-08-24 to 08-25
Every founder ask, ruling and directive extracted from the crew-agent transcripts covering 2026-08-24 15:42Z through 2026-08-25 03:05Z, merged from ten background-agent extraction passes into one table.

| time | requirement | verbatim quote | topic tag | status |
|---|---|---|---|---|
| (pre-00:20Z) | Kubernetes cluster must be stable and self-healing without unexpected downtime. (said 4x) | resilience, self healing | k8s/oke/fly | OPEN |
| (pre-00:20Z) | Maintain a staging environment alongside production. | and we need staging also | k8s/oke/fly | OPEN |
| (pre-00:20Z) | Estate migration to Kubernetes isn't done until it's fully automated, repeatable, chaos-tested and production-ready with deployments. (said 2x) | we are dnoe done until estate is nigrated to kuberests, fully autonated and repetable with ehaustive chaos testing | k8s/oke/fly | OPEN |
| (pre-00:20Z) | Add automation tooling so the cluster is totally self-healing and production ready. | ad tooling for autination, total self healing prod ready | k8s/oke/fly | OPEN |
| 00:20Z | Remove Fly.io entirely, use survival-stack as reference, and deliver genuine seamless vendor-agnostic stack portability. (said 5x) | look at the survivial project and derliver | k8s/oke/fly | OPEN |
| 06:33Z | Unstick the session that is stuck on the Kubernetes work. | "session working on kubernnetes is stucck]" | k8s/oke/fly | OPEN |
| 08:24Z | Stop running both Colima and Docker Desktop redundantly; consolidate. | "why are we runnoing both colina and docker desktop" | k8s/oke/fly | OPEN |
| 08:31Z | Use only Colima; drop Docker Desktop. | "so why cant we use just coline? why w=do we nneed both?" | k8s/oke/fly | DONE |
| 12:52Z | Mandate: do the k8s/infra work on the Macbook with best practices from day 0 before deploying to real infra; not optional. | "we need best practices fron day0, trusing these cowboys to deploy to real infra withut knwing exctly how everything wor | k8s/oke/fly | OPEN |
| 2026-08-24 20:10Z | Stand up the k3d/Kubernetes cluster on the Mac again, carefully, despite machine slowness | "You told me twice today the machine is too slow, an lets try agaib but careful" | k8s/oke/fly | OPEN |
| 2026-08-24 21:28Z | Sync up and collaborate with peer sessions; get the cluster running | "cann you sync up and collbort with perrs we need this cluster running" | k8s/oke/fly | OPEN |
| 2026-08-24 22:26Z | ports.yaml is absolute law for every port binding; no FOREIGN-process exemption from the ledger check | "Port Ledger Is Absolute Law... If a process holds a port, it gets checked against the ledger. No exceptions" | k8s/oke/fly | OPEN |
| 2026-08-24 22:26Z | Keep shared code environment-agnostic; local infra fixes stay in local config only | "No Colima-specific flags, no DNS workarounds, no macOS conditionals... never in the shared repo" | k8s/oke/fly | OPEN |
| 2026-08-24 22:26Z (FOUNDER DIRECTIVE: ENVIRONMENT PARITY — FINAL) | Make the Mac replicate prod exactly; set colima network.hostAddresses true but do not restart colima until a maintenance window | "This laptop is a dev substrate. It must replicate prod (k3s on Oracle Free Tier)... Any deviation is drift; drift is a | k8s/oke/fly | OPEN |
| 2026-08-24 23:21 | Deliver a deep analysis of the hermes-v2 / Fly branch's actual impact/content. | "Deep Analysis: hermes-v2 / Fly Branch Impact" | k8s/oke/fly | OPEN |
| 2026-08-24 ~21:xx | Harden the single k8s cluster once ready: draft default-deny NetworkPolicy and resource quotas per namespace | "our whole platforn is in a single cluster, is this risy? ... Draft the Default Deny NetworkPolicy and Resource once clu | k8s/oke/fly | OPEN |
| 2026-08-24 ~21:xx | Get the k3s cluster fully operational | "your goal is to get the k3 cluster opertinoal" | k8s/oke/fly | OPEN |
| 2026-08-24 ~21:xx (pasted k3s checklist) | Build k3s cluster with namespaced quotas, default-deny network policies, Traefik ingress on 80/443, and ArgoCD GitOps before handoff | "Create the platform and data-ops namespaces... Apply a Default Deny All NetworkPolicy... Configure Traefik to bind 80/4 | k8s/oke/fly | OPEN |
| 2026-08-24 ~22:15Z (FOUNDER DIRECTIVE: OBEY THE PORT POLICY) | Before binding k3d to host ports 80/443, consult ports.yaml, register Traefik as owner, evict conflicts, then fix Docker | "k3d is failing to start because you are trying to bind host ports 80 and 443 without consulting the ledger... register | k8s/oke/fly | OPEN |
| 2026-08-24 ~22:45Z (R23) | Oracle OKE is the k8s migration target; verify local green first, then prepare, then move — nobody provisions Oracle before that | Oracle Always Free tenancy named destination for crew#78 | k8s/oke/fly | OPEN |
| 2026-08-24 ~22:45Z (R24, relayed) | Every container image tag must ship both amd64 and arm64 | every tag amd64+arm64 | k8s/oke/fly | OPEN |
| 2026-08-24 ~23:20Z | Produce a real, measured cost estimate for running the cluster as cheaply as possible | "while we are at it lets get a real cost estinate of what we need to run a cluster, cheapest possible lets be shrewd and | k8s/oke/fly | OPEN |
| 2026-08-25 ~00:00Z | Research broadly across managed vs self-provisioned k8s providers for cost | "research wide cheapest provider nanaged vs self provisioing" | k8s/oke/fly | OPEN |
| 2026-08-25 ~00:00Z | Size the cost estimate for growth, not just today, and stay tight on cost | "and not just for today because w are explanding but need to be tight with coses" | k8s/oke/fly | OPEN |
| [02:47Z] | Understand what is possible on Kubernetes as a mature platform without reinventing existing solutions. (said 2x) | sicne we are on k, we should underdtnd what is possobe, it is nature platfron, never reinvent the wheel | k8s/oke/fly | OPEN |
| [02:49Z] | Staging and production clusters must both exist with identical configuration. (said 2x) | staging and prod cluster | k8s/oke/fly | OPEN |
| [~10:25Z] | Uncomment the image blocks in staging/prod overlays and pin each to a real commit SHA. | Move 2 uncomments those blocks and gives each overlay a real SHA | k8s/oke/fly | OPEN |
| [~10:35Z] | Apply the --disable=traefik,servicelb flag fix and boot the rehearsal cluster. | apply the --disable=traefik,servicelb fix and boot the cluster | k8s/oke/fly | OPEN |
| (pre-00:20Z) | Track the cost risk of the infrastructure work. | this is a cost riska dneeds tracjing | machine-load | OPEN |
| 08:38Z | Ruling that colima is the standard, already in use. | "we have colina" | machine-load | OPEN |
| 08:38Z | Docker Desktop is retired; do not use it. | "docker desktop is retired" | machine-load | DONE |
| 13:06Z | Kill what's currently running on the machine; do not start anything new until the load problem is diagnosed. | "thats a terrible call, the achine is nearly on its knees, we need to kill whats running not run nre until we figure thi | machine-load | OPEN |
| 13:28Z | Deploy Netdata real-time monitoring on Mac to detect CPU throttling, RAM pressure, and per-process resource burn for permanent optimization. (said 2x) | The Ops Sentinel — Netdata | machine-load | OPEN |
| 15:04Z | Fix machine performance/resource contention so he can work. (said 2x) | "the nacine i too slow, i cant do any work" | machine-load | OPEN |
| 2026-08-24 15:42Z | Investigate what background processes are launching on the machine and why | "who is launching backgorund itens and why?" | machine-load | OPEN |
| 2026-08-24 22:06 | Fix the Colima network/DNS issue only in the local macOS host config, never in app code. | "Modify the local machine's Colima configuration directly to set network: vz and add reliable DNS fallbacks" | machine-load | OPEN |
| 2026-08-24 22:51 | Prove the full compose + k3d + Dagster + 40-schedule estate reconciles on the current Mac before arguing Oracle is needed — the case for Oracle is scale, not brokenness. | "Local green does not mean add more to the Mac. It means prove the compose estate reconciles" | machine-load | OPEN |
| 2026-08-24 ~15:00Z (pre-transcript, standing) | Stop and investigate immediately what is launching Chrome helper processes that nearly crashed the laptop | "it nearly destroyed ny laptio, i see a lot of google cchrone helpe r processes who is lauching ? stop asap and investig | machine-load | OPEN |
| 2026-08-24 ~22:30Z (R22) | Cancel the colima drill; do not stop/restart/reconfigure colima or edit colima.yaml; leave registry-egress broken on purpose | "forgetthe drilfor noww, too risky" | machine-load | OPEN |
| 2026-08-25 03:05Z | Diagnose and fix why he keeps being prompted for his laptop password | "why do i keephving to enter ny laptop password" | machine-load | OPEN |
| 00:22Z | Identify every metadata gap: what the estate should be recording that it currently misses. | "2what of netadata, what have we nissed" | other | OPEN |
| 00:22Z | Produce a complete map of every data point collected and every one not collected, each with a stated reason. | "nnap alldatapoints we collect, all data dapints we dont collect and why" | other | OPEN |
| 00:22Z | Automate data collection and plumbing into a real pipeline (not hand-rolled scripts), researching open-source tools before building. | "data collection and plunbing shoulld be autonated, we need propr pipeline, resech online source tools" | other | OPEN |
| 01:01Z | Re-check whether the estate actually competes with the hosted service in question; correct the license verdict if wrong. | "which forbids a competing hosted service. are e conpeting? i dont think s" | other | OPEN |
| 02:58Z | Unify the fragmented data pipeline (currently 77 non-joining record locations and 6 scheduling roots) into one model. | "but ... this is data sciences proble , we need unification of dta pipeline ,work is recorded in 77 places that do not j | other | OPEN |
| 03:16Z | The data-science function must be mature enough to survive investor/buyer scrutiny; it currently is not. | "if a investor wanted to buy us to norrow, do you think they will be inpressd with our datasciece funcion or ... i think | other | OPEN |
| 03:18Z | Fix the broken accept/keyboard interaction in the approval UI. | "i treid to accept bt the keuboarddid nt work" | other | OPEN |
| 08:59Z | Get Aiden (the watchdog/notification system) operational. | "why is aden not operaional s." | other | OPEN |
| 2026-08-25 02:11 | Give the founder an easy way to save/persist a doc he pastes — he currently doesn't know how. | "id want to save this doc but dont know how to, fiuder not happy" | other | OPEN |
| (carried forward) | Every platform/portal must support both human and machine access, built as if a buyer is diligencing it tomorrow — add as a standing law. (said 2x) | Every portal in this brief assumes a human at a laptop... think s if an investor is going to buy the platforn tonorrow, | platform/idp | OPEN |
| (pre-00:20Z) | Full control and visibility over platform and operations required. (said 2x) | i need to have full control and viciblity | platform/idp | OPEN |
| 00:04Z | Stop using bespoke scripts for platform engineering; deploy real, mature tooling instead. | "if you think basy scripts are going to get s to elite pe you are hallciating" | platform/idp | OPEN |
| 00:07Z | Every platform layer must carry a fallback/backdoor switchable within 10 seconds or 0 seconds. | "we nust always have options switachble in10 seconds na 0 seconds" | platform/idp | OPEN |
| 00:32Z | Prioritize fixing the reinvented-wheel platform gaps over other work; pick the first OSS replacement item and prove it operational. | "i think fiing the, reinventing four wheels is nore urgent, get id one and prove it" | platform/idp | OPEN |
| 01:34Z | Sort out and get the Langfuse/observability tooling working. | "actually sort it out" | platform/idp | OPEN |
| 01:46Z | Produce architecture documentation, persist docs properly, and fix documentation management — current standards are very poor. | "i need to se archtecture docunetaion, and add docs persisted and we need better dos nanagent, our docunentaion standard | platform/idp | OPEN |
| 02:07Z | Give a detailed summary of the PE improvements to expect. | "i want deatailed sunnary of te ninpprovnents to epecxt" | platform/idp | OPEN |
| 03:11Z | Make the crew board give him real visibility and fully integrate with GitHub issues. | "do i bave visibility to this? how can i truet you is the board fully integrated with giyhub ossuers" | platform/idp | OPEN |
| 07:07Z | The whole platform must be provider-agnostic, not dependent on one AI provider, and "Ninina" must be a fully autonomous team member. (said 2x) | "our whole platfornn cant be dependent on one provider, ninina needs to be part of the tean" | platform/idp | OPEN |
| 07:07Z | Directive to execute the provider-agnostic plan immediately. | "get it done" | platform/idp | OPEN |
| 07:07Z | Build a single unified agent framework. | "and we need unified agent frannewprk" | platform/idp | OPEN |
| 07:07Z | Eliminate Claude-specific folders and files across the estate. | "no nnore claude folders ad files" | platform/idp | OPEN |
| 07:07Z | Retire the old single-provider (Claude-only) operating model. | "that old nodel needs to retitre" | platform/idp | OPEN |
| 07:07Z | Research and map the risks before building the new framework. | "frist reserchh and nap risks" | platform/idp | OPEN |
| 07:10Z | Remove claude.md and claude-folder artifacts from the estate entirely. | "i dont wan tot see claude.nnd, claude folder etc" | platform/idp | OPEN |
| 07:10Z | Rebrand the framework/product away from Claude-specific naming. | "we need a rebrand" | platform/idp | OPEN |
| 07:10Z | The unified framework must support onboarding new providers and stay provider-agnostic. | "one unified franework that can obord new providers and is agnistic" | platform/idp | OPEN |
| 07:23Z | Add the listed provider-swap risks (tool schema diffs, thinking-block stripping, prompt-caching tuning) to the risk doc and make sure the whole team sees it. | "add to risks and ensure evryoe sees this" | platform/idp | OPEN |
| 07:31Z | Your job is to overhaul and migrate the platform, not firefight. | "but that is you r oe job to overhul our platforn and nigrate it" | platform/idp | OPEN |
| 08:26Z | Confirms/directs completing migration to the hosted monitoring service and deleting the custom monitoring implementation. | "ok have w efully nigrated and deleted hthe custoe inpelentaions" | platform/idp | OPEN |
| 08:27Z | Figure out how to run the monitoring service without paying (stay on a free tier). | "we nee dto figure out how we get away with outpayin" | platform/idp | OPEN |
| 11:12Z | Stop firefighting; research exhaustively online and adopt a mature open-source framework/platform for governance and coordination instead of hand-rolled patches. | "we nned the blleding edge resac h and franeworks adpoping then open source" | platform/idp | OPEN |
| 14:42Z | Clarifies scope: only platform layers must unify in idp; products like prospector can live outside idp and are not deleted. (said 2x) | careful, A component that is not in idp and not on standards page | platform/idp | OPEN |
| 14:45Z | Replace custom operator.py model routing code with standard open-source LiteLLM proxy for 100+ provider support and zero maintenance. (said 2x) | replace operator.py with a lightweight LiteLLM container | platform/idp | DONE |
| 14:45Z | Configure LiteLLM to emit OpenTelemetry traces directly to idp observability collector at 127.0.0.1:4318 without redundant databases. (said 2x) | Route LiteLLM logging directly into idp observability pipeline 127.0.0.1:4318 | platform/idp | DONE |
| 14:45Z | Set global and per-agent LLM spend limits at LiteLLM proxy configuration level without custom Python code. (said 2x) | Enforce Hard Budget Caps at the proxy config level | platform/idp | OPEN |
| 2026-08-24 15:48 | Investigate and quickly adopt the pasted "fortress-stack" zero-host-port platform (Traefik-only ingress, DB/credentials isolated on an encrypted Docker network) instead of building bespoke. | "// investigate we need to adopt quickly" | platform/idp | OPEN |
| 2026-08-24 15:48 | Route models through LiteLLM with automatic frontier fallback, a hard $5/day budget cap, and Langfuse telemetry on every call. | "Configures primary open-source models with automatic frontier model fallbacks, hard budget caps ($5/day)" | platform/idp | OPEN |
| 2026-08-24 15:48 | Gate all MCP/A2A tool traffic through agentgateway with CEL authorization policies and OpenTelemetry trace propagation. | "Standardizes Model Context Protocol (MCP) tool access and Agent-to-Agent (A2A) communications under AAIF guidelines, en | platform/idp | OPEN |
| 2026-08-24 17:17 | Stop pushing back on platform improvements with "we already use X"; adopt an open mind and standardize as one crew — founder overrides prior pushback. | "any tine i ty to inprove the platfor i get push back and we say we ar alreeeady using this" | platform/idp | OPEN |
| 2026-08-24 17:33 | Land/commit the scratchpad mature-platform-gate doc now that the branch-blocking sessions have ended. | "sort it sout, those sessions are gone" | platform/idp | OPEN |
| 2026-08-24 17:56 | Fix Langfuse — it is still down. | "angfuse is genuinely still down. why?" | platform/idp | OPEN |
| 2026-08-24 18:22 | Address the founder's outstanding friction complaint — it has not yet been resolved. | "i think the founders conern hs nit been addressed, still too nuch friction" | platform/idp | OPEN |
| 2026-08-24 18:45 | Eliminate login-screen friction; treat seamless security as a serious priority. | "in seeing a login scren, too nuch friction, we shoukld take seless security seriously" | platform/idp | OPEN |
| 2026-08-24 20:49 | Configure all environments identically/consistently. | "we want all envs configureed the sne" | platform/idp | OPEN |
| 2026-08-24 21:07 | Do not build from scratch; reuse/adopt existing mature tools instead. | "we are not buildig frons scratch eiter" | platform/idp | OPEN |
| 2026-08-24 21:43 | There must be exactly one port ledger — confirm ports.yaml is it; no second drifting ledger. | "ports.yaml is this the backkdoor port ledger we agreed? cant have 2 ledgers driftin" | platform/idp | DONE |
| 2026-08-24 22:06 | Never add DNS/network/OS-specific workarounds to Dockerfile, compose, or k8s manifests — app code stays environment-agnostic. | "strictly forbidden from adding DNS workarounds, network flags, or OS-specific hacks to the Dockerfile" | platform/idp | OPEN |
| 2026-08-24 ~15:00Z | Stop firefighting; research deeply online and build one governance/coordination framework instead of more partial patches | "lets solve this prolen once, reseach seeply and exhaustively onlne, we need franework or platfor, not nore partial patc | platform/idp | OPEN |
| 2026-08-24 ~21:xx (pasted Bridge Architecture) | Run Backstage via local Docker container now (Phase 1); hand off to ArgoCD once k8s is finalized (Phase 2); tickets stay on the free GitHub board | "Instead of yarn start, the agents will spin up Backstage using its official Docker container locally... ArgoCD is point | platform/idp | OPEN |
| 2026-08-25 01:56 | Prove that the platform engineering (PE) work is genuinely "elite grade." | "sorry prove that our pe is elite grade" | platform/idp | OPEN |
| 2026-08-25 ~00:42Z | The platform must run reliably enough that he never has to worry and has full confidence in it | "i should not need to woryy about anythhing" / "i need full confidence in platofrn" | platform/idp | OPEN |
| 2026-08-25 ~01:16Z | He needs an actual UI; a localhost HTML page alone is not sufficient | "i dot have a ui so i ant see anything" | platform/idp | OPEN |
| 2026-08-25 ~01:16Z | Use GitHub Projects as the agreed UI/tracking surface, not another ad hoc board | "whst is this? i thoght we deided to use github projects" | platform/idp | OPEN |
| 2026-08-25 ~01:16Z | Make the GitHub Projects board usable, not an undifferentiated 178-item list | "i cant do aythin withis" / "nit user firenly" | platform/idp | OPEN |
| 2026-08-25 ~01:16Z | Give every scheduled job a real description visible in Dagster | "nodescriotion of docs describing what they do in dagster" | platform/idp | OPEN |
| 2026-08-25 ~01:16Z | Set up Dagster properly | "we have not setup dagster [eoperly" | platform/idp | OPEN |
| [14:17Z] | Adopt MCP SDKs/Agentgateway for agent-tool protocol instead of proprietary board schemas. (said 4x) | (pasted "fortress stack" spec) | platform/idp | OPEN |
| [~08:xx-09:00Z] | Build an automatic spend guard that refuses paid-infra commands rather than relying on agents remembering the rule. | Make it self-enforcing with a spend guard | platform/idp | OPEN |
| (carried forward) | Research methodology and findings must be used to justify all decisions. (said 2x) | thissi why i asked for rsarc | process/laws | OPEN |
| (pre-00:20Z) | Unblock yourself and coordinate with peer sessions instead of stalling. | youneed to unblcok yourself, talk to you r peerrs | process/laws | OPEN |
| (pre-00:20Z) | Define clear, command-provable criteria for done before starting work. | what is the definition of done? | process/laws | OPEN |
| (pre-00:20Z) | Work proactively without waiting for explicit founder direction. | i should not have to ask | process/laws | OPEN |
| (pre-00:20Z) | Mark this work as high priority in tracking. | your work needs to be labbed high pririty | process/laws | OPEN |
| 00:00Z | Ensure the recovery drills are fully automated and self-registering. | "are the drills fully autonated and registerd, self registerd" | process/laws | OPEN |
| 00:04Z | Final warning: deliver mature tooling or be replaced. | "one last chance befoe i sack you" | process/laws | OPEN |
| 00:09Z | Continue executing item-one OSS-replacement work while avoiding the estate's known recurring mistakes (proxy grading, exit-code masking, duplicates). | "can you get id one and aboid the traps we have been fallig into?" | process/laws | OPEN |
| 00:27Z | Research deliverables must be plain-English with a concrete decided way forward, not a cryptic summary. | "you wasted resarch toekns to give ne a cryptic sunnry with no way forward, try doig proper reseeach epoc fail" | process/laws | OPEN |
| 01:22Z | Communicate clearly — stop giving confusing explanations. | "surry sounds interesting but i need clear connunication" | process/laws | OPEN |
| 01:25Z | Enforce standard best practices from day 0 for the new data-science function; stop making excuses and do the requested research. (said 3x) | we dont eforce stadard adbest practices, this is a new funxtion, we need to be ready fron day 0, stop naking ecuses | process/laws | OPEN |
| 01:54Z | Verify that current work is actively progressing (implicit request for status) | sorry is this runing? | process/laws | OPEN |
| 01:58Z | Only the most capable/expensive agent works on the highest-value tasks, measured with data/metric/proof or exponential-impact items. | "sorry i need you to only work on the highest vakue tasks , you are the nost capable and epensive aget" | process/laws | OPEN |
| 02:00Z | Delegate any task that does not meet the highest-value/measurable/exponential-impact bar. | "delegte anythig not natching that criteria" | process/laws | OPEN |
| 02:14Z | Confirm capture of requirements and ensure they are tracked on crew board (said 2x) | ok back to k3 ddi you note the requrenents are they o the board | process/laws | OPEN |
| 02:17Z | Ensure another session can seamlessly take over the work with full context if this session dies. | "ensure anoter session can take over your work seanlessnl wwith full contest if ur sesson dies" | process/laws | OPEN |
| 02:17Z | Prove all the claimed improvements immediately. | "i need all thos inprovenent proven" ... "now" | process/laws | OPEN |
| 02:23Z | Listen in on agent sessions to find how to produce a multiplier effect and extraordinary outcomes. | "you eed to listen in on agent sesesion to work out how to have a nultiplier effct adnd product etraordinary outccones" | process/laws | OPEN |
| 02:34Z | Manage the change-management process for this work and ensure it goes smoothly. | "you need to nanage the chage nengenent process also and ensure tit goes snoothly" | process/laws | OPEN |
| 02:35Z | Map the single highest-value thing that moves the estate forward exponentially. | "have you napped the highest vales htig that expnentially nives the estate fprwrad" | process/laws | OPEN |
| 02:39Z | Reasserts: listen in on all agent sessions (standing, not optional). (said 3x) | i told you tplisten in to all agent sessionf for a reason | process/laws | OPEN |
| 02:39Z | Treat the delivery pipeline's productivity/cost-drain problem as equally critical work. | "how about productivity? its a cost drain not delivering, i think the delivery pilelne is as critical" | process/laws | OPEN |
| 02:39Z | Standing rule: pursue exponential solutions, not incremental ones. | "i need exponential solutions" | process/laws | OPEN |
| 02:39Z | Build durable, compounding solutions rather than one-off fixes. | "i need a gift that keeps on giving" | process/laws | OPEN |
| 02:51Z | Fix issues as you find them, or delegate to a subagent with clear instructions, then return to the main objective. | "you need tobe addresig these issues as you fin then or delegate to subagebt with clear inturctins" | process/laws | OPEN |
| 03:16Z | Stop fixating on cost and daily spend — stay on the stated objective. | "you are obsesed with cost and daily sped, and dirftedf fron yur ojection" | process/laws | OPEN |
| 03:17Z | Stay in scope — do not act as if you were the finance function. | "you re not finnance, so fuckig stay inyour ane lane" | process/laws | OPEN |
| 03:23Z | Never reinvent something a mature tool already does, and worse. | "never reinvet the wheel and do a worse job" | process/laws | OPEN |
| 03:23Z | Show evidence of autonomous online research happening without him having to ask for it each time. | "also not seein evidence of autonouse online research without ne asking" | process/laws | OPEN |
| 03:23Z | Instructions must be auditable and enforceable, not repeated prose. | "in tired of repearting, instructino that are fucking autibantabkle and enforcable" | process/laws | OPEN |
| 03:23Z | Rules aren't enough — need protocols that every agent actually follows. | "we dotjustneed lways we need prootccols that all agebnt folow" | process/laws | OPEN |
| 03:23Z | Stop claiming infrastructure (e.g. "we have a board") is real/working when it isn't — this is hallucination. | "you are all hallucaniatig claining we have a baord, thsi si a fucking jike, a sick joke" | process/laws | OPEN |
| 06:52Z | Add a law: any mistake must be fixed so no agent session can ever repeat it, proven exhaustively. | "add a law if you ake a istake, you need to ensure no agent sessionn can ever nnake that nistake again" | process/laws | OPEN |
| 07:29Z | Standing rule: the founder using profanity signals red-zone/high-alert status for the crew. | "if founder uses profanity that eans its red zone and high aalert for crew" | process/laws | OPEN |
| 07:31Z | Broadcast this red-zone/firefighting situation to the team. | "botrdacast to tean" | process/laws | OPEN |
| 07:32Z | Stop writing bespoke Python scripts and firefighting; eliminate this pattern once and for all. | "and you are fucking writing pyhtug svcripts and firefighting sonethibg we want to elininate once and for all" | process/laws | OPEN |
| 07:52Z | Track and follow the specific goals already given, not improvised ones. | "i gve you dpecigfic goels" | process/laws | OPEN |
| 08:03Z | Stop writing custom, fragile code that causes fires; use mature platform tools instead. | "thats becse we re wrtog custoe code" / "and using frlgine nd gfaleky approach" | process/laws | OPEN |
| 08:03Z | Standing rule: no more firefighting. | "no nore fireffghting" | process/laws | OPEN |
| 08:05Z | Pause all work immediately. | "you need to pause ll worl" | process/laws | OPEN |
| 08:11Z | Crew agents work only on project work or work that eliminates firefighting, not ad hoc firefighting itself. | "crew should only be wprking on project work, wpork that elininate firefighting" | process/laws | OPEN |
| 08:11Z | Broadcast and enforce the "project work / eliminate firefighting" rule across sessions. | "this need to be broadcat and ecforced" | process/laws | OPEN |
| 08:19Z | Ensure today's goals are met across k8s, platform engineering, and data science, and eliminate firefighting. | "ok so i need now to ensure we re going to neet our goals tody/ k8s, pe, datascience, eliniate forefighting" | process/laws | OPEN |
| 08:22Z | Surface PE roadmap progress proactively; he should not have to ask what's next. | "ok, what what next on the the pe roadnap i shpuld not need to ask" | process/laws | OPEN |
| 08:24Z | Standing rule: always verify current state before reporting progress. | "you nneed to always verify current stare" | process/laws | OPEN |
| 08:37Z | Broadcast the decision to the team and confirm everyone is properly onboarded. | "broadcst to tean annd ensure we are ll onboarded properly" | process/laws | OPEN |
| 09:46Z | Broadcast the status/decisions in the report above to the team. | "broadcast" | process/laws | OPEN |
| 10:14Z | Standing instruction: decide quickly, don't linger on the secrets architecture choice. | "decide quickly" | process/laws | OPEN |
| 10:24Z | Push all 62 local commits on crew to origin immediately and unpause session/agent d1. | "Push 62 commits to origin and unpause d1 now" | process/laws | OPEN |
| 13:26Z | Do not run background pytest suites simultaneously with infrastructure operations on resource-constrained machines. (said 2x) | running backround pytests at the sane tine as runing infra is idiotic | process/laws | OPEN |
| 13:28Z | Implement MkDocs with Material theme as centralized source of truth for rituals, ADRs, and procedures in Markdown version control. (said 2x) | ok lets add that nd look ngo these also The Runbook Writer | process/laws | OPEN |
| 13:28Z | Adopt Logseq as local-first tool to capture decision thinking before policy codification, then promote approved ADRs to MkDocs. (said 2x) | The ADR Secretary — Logseq | process/laws | OPEN |
| 13:43Z | Establish explicit engineering standards and review gates to catch obvious issues before PR approval. (said 2x) | well who apprived the pull request, do we have engineering standards | process/laws | DONE |
| 14:38Z | Buy a mature platform, do not stitch half-built solutions together that break daily; single platform approach required. (said 2x) | FOR THE LAST TINE WE NEED A NATURE, PLATFRON WE HAVE A POTENTIL BUYER | process/laws | OPEN |
| 15:06Z | Troubleshoot the current incident now, and put a permanent guard in place so it cannot recur. | "i need this trolbeshooted no and we dont want this wto ever happen again" | process/laws | OPEN |
| 2026-08-24 15:42Z | Ensure all estate work is committed and pushed to git (enforce LAW 24 everywhere) | "i need you to ensure all work on the estaate is in git" | process/laws | OPEN |
| 2026-08-24 15:42Z | Scope the git audit to every surface touched in the last 48 hours, not just declared repos | "all surface areas worked on in lasst 2 days" | process/laws | OPEN |
| 2026-08-24 15:48 | Require human approval for DB writes, external deployments, and token creation; only read-only/local ops may be fully automated (EU AI Act Art. 14). | "Human-in-the-Loop Required: Database writes, external deployment executions, token creation" | process/laws | OPEN |
| 2026-08-24 15:48 | Adopt pytest-bdd/behave plus Promptfoo/DeepEval as CI gates enforcing AGENTS.md governance rules. | "pairing standard Gherkin-syntax tools with LLM evaluation assertion frameworks provides an enterprise-standard, mainten | process/laws | OPEN |
| 2026-08-24 15:53 | Identify who is adding background items/tasks and why, and bring their creation under control. | "who is adding background itens and why" | process/laws | OPEN |
| 2026-08-24 17:19 | Produce a requirements doc, and standardize/migrate documentation before further platform work. | "i nneed to see a requirenents doc and before we do tht we need to stabdardise our doceunetation" | process/laws | OPEN |
| 2026-08-24 17:19 | Every claim must be proven; the founder will not accept unproven assertions. | "in not listeing to your hllucincations, proof or die" | process/laws | OPEN |
| 2026-08-24 18:17Z | Merge everything to main as long as each change passes its PR | "as ong as they pss pr" | process/laws | OPEN |
| 2026-08-24 18:17Z | Every feature merged must ship with a demo and onboarding | "deno and onboarding" | process/laws | OPEN |
| 2026-08-24 19:02 | Always research the current state of the world before choosing any tool, standard, protocol or version (said 2x) | "ok good job but alway research, it pays off all the tine" | process/laws | OPEN |
| 2026-08-24 21:07 | Every ticket must be visible on GitHub Issues, and there must be a real UI surface for the board. | "not seeing any issues on github, wherw are all the tickets going? secindy where i y ui surface?" | process/laws | OPEN |
| 2026-08-24 22:26Z | Verify every binding-security claim with live kernel probes, not a tool's self-reported state; audit the ledger after every infra change | "Every claim of 'localhost-only' or 'secure binding' must be independently verified with live kernel probes (lsof, ss)" | process/laws | OPEN |
| 2026-08-24 22:26Z | Document every dev/prod substrate asymmetry so it is never rediscovered from zero | "Record every substrate property that creates environment asymmetry... the next session starts from your standing point, | process/laws | OPEN |
| 2026-08-24 23:45 | Close the keytar build-warning loop properly — convert the permanent false alarm into a real hard-fail instrument so it's never revisited. | "Tbut it prevents is fron ever having to revisit and fals arns so close the loop properyl" | process/laws | OPEN |
| 2026-08-24 ~18:20Z | Get everything currently on branches merged into main | "everything need ti be in nin" / "nain" | process/laws | OPEN |
| 2026-08-24 ~21:xx | Add the cluster-hardening item to the tracking board | "add to bord" | process/laws | OPEN |
| 2026-08-24 ~21:xx | Collaborate with peer sessions and don't duplicate work | "collborte , dont duplicate woek" | process/laws | OPEN |
| 2026-08-24 ~21:xx | Track every goal on one ticket and post progress notes as work proceeds | "track all you goal and update the ticket as you proceed" / "withprogress notes" | process/laws | OPEN |
| 2026-08-24 ~22:00Z (FOUNDER DIRECTIVE: UNBLOCK AND FIX THE GUARDS) | Fix the anti-loop guard to diff the exact command string (not flag changes) rather than weaken it blindly, then resume work | "the anti-loop guard is firing falsely... Fix the guard, transition to your ephemeral desks, and resume your inflight ta | process/laws | OPEN |
| 2026-08-24 ~22:30Z (R21-broadcast) | Broadcast to every live peer before any drill/restart/teardown touching shared local infrastructure | "if u are drilling you need to broadcast to perrs" | process/laws | OPEN |
| 2026-08-25 ~00:42Z | Define and enforce a document policy: every research pass must deliver a persisted, findable asset | "is this docuenntesd? whats our document polocy, we need strong goveracne, every reseach needs assets delivered, nothing | process/laws | OPEN |
| 2026-08-25 ~00:42Z | Share findings with the peer team and keep them updated | "sgare with tean annd update" | process/laws | OPEN |
| 2026-08-25 ~00:42Z | Make policies operational, standardized, and automated | "sorry we need th epolocoes to be operatioal, standardsied autonated" | process/laws | OPEN |
| 2026-08-25 ~00:42Z | A document nobody reads is useless | "a dcunet no one reads is useless" | process/laws | OPEN |
| 2026-08-25 ~00:42Z | Stop needing reminders; document things properly the first time | "i have to renind all the tine]docuent this" | process/laws | OPEN |
| 2026-08-25 ~00:42Z | Documents must stay visible/accessible to him, not disappear after being written | "and i never see the docs again" | process/laws | OPEN |
| 2026-08-25 ~01:16Z | Nothing counts as done until he can see and use it himself | "util i do it is not done" | process/laws | OPEN |
| 2026-08-25 ~01:16Z | Maximise use of tools already owned instead of running them half-configured | "we need to nainise our tools" | process/laws | OPEN |
| 2026-08-25 ~01:42Z | Fix open items directly instead of reporting them back as a list | "arrrhhhggghhhhsort it out" | process/laws | OPEN |
| 2026-08-25 ~02:00Z | Before the session ends, hand work over to the durable board and alert the crew | "you are about to be terniated, hand over you r work to the board and alert crew" | process/laws | OPEN |
| [02:47Z] | Kubernetes standards must be followed. (said 2x) | we eed to follow stadrds | process/laws | OPEN |
| [02:48Z] | No custom scripts shall be written for production Kubernetes operations. (said 2x) | not write custon scripts for production cluster | process/laws | OPEN |
| [02:48Z] | Research proven, stable approaches instead of building novel solutions. (said 2x) | reserch what always works | process/laws | OPEN |
| [02:48Z] | Establish defined processes and ways of working that are enforced, not documented. (said 2x) | we need prope r standrds / defined processes and ways of woking | process/laws | OPEN |
| [~08:xx-09:00Z] | Founder Ruling R14: Mac is the prove-and-build substrate, zero-cost only, no paid infra without sign-off, proof precedes any real cluster spend. | NO paid infra without explicit founder sign-off. Free tier only | process/laws | OPEN |
| [~08:xx-09:00Z] | Broadcast R14 as a binding founder ruling injected at every session startup. | Broadcast as a Founder Ruling, pin it where agents check at startup | process/laws | OPEN |
| [~08:xx-09:00Z] | Close tickets asking for paid infra, citing R14, so the ask stops recurring. | Close open tickets so they stop regenerating the ask | process/laws | OPEN |
| [~10:35Z] | Merge PR #702 once CI builds pass. | If the builds pass, merge it | process/laws | OPEN |
| [~10:35Z] | Non-blocking work goes in a follow-up PR and must not block production. | Everything else can ride along in a follow-up PR, doesn't block prod | process/laws | OPEN |
| 09:12Z | Confirm proper secrets management exists for MINIMAX_API_KEY; coordinate with k8s and platform-engineering. | "MINIMAX_API_KEY, do w have proper secrest nanagent? , tlk to k8 and pe tean" | secrets | OPEN |
| 09:16Z | Finish the secrets implementation and make it operational and the single sanctioned way to handle secrets. | "lets getthe inplenentaion donne and opertinal and the only way to work with secrets" | secrets | OPEN |
| 09:47Z | Decision: the SOPS directory-vault design is the final secrets architecture. | "Directory vault (my sops proposal) is finnal" | secrets | DONE |
| 09:47Z | Broadcast the final secrets-vault decision to the other agent sessions. | "broadcast" | secrets | OPEN |
| 10:14Z | Approve the SOPS + External Secrets Operator platform architecture as presented. | "i think this is the best opton" | secrets | OPEN |
| 10:17Z | Compare the secrets-tooling options and decide quickly with a summary. | "conpare" ... "deccide quicky, need sunnary of conparins" | secrets | OPEN |
| 10:19Z | Stop deliberating and execute the secrets migration now. | "lets stop wasting tine and get it done" | secrets | OPEN |
| 10:21Z | Confirms the final decision on the secrets vault's home (private repo estate-secrets). | "final decision" | secrets | DONE |
| 14:45Z | Inject API credentials into LiteLLM using existing sops+age secret pipeline at startup rather than hardcoded environment variables. (said 2x) | Feed API keys into LiteLLM using existing sops+age pipeline | secrets | DONE |
| — | KINI.AI Sovereign Control Plane spec requirements (7 rows: Ghost/Haptic/Spatial/Converse presence model, Merkle DAG checkpointing, Secure Enclave signing, 2/3 model-consensus governance, Langfuse-halt policy, 5 named implementation files, BDD acceptance tests) — tracked on crew#219, not duplicated here. | pasted 2026-08-25 02:11Z: "The system may NEVER push a notification that causes a state transition from Ghost to Converse" (and 6 more) | kini-spec | OPEN (see crew#219) |

## Row counts

Total rows: 203 (including the kini-spec pointer row).

By topic tag:
- process/laws: 94
- platform/idp: 50
- k8s/oke/fly: 28
- machine-load: 12
- other: 9
- secrets: 9
- kini-spec (pointer only): 1

By status:
- DONE: 9
- OPEN: 194 (includes the kini-spec pointer row)

No-Issue: this is the tracking index; each OPEN row becomes its own issue when picked up.