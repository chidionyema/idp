export interface Post { slug: string; title: string; date: string; excerpt: string; body: string; readTime: string; }

export const posts: Post[] = [
  {
    "slug": "agentic-routing-for-enterprise",
    "title": "Routing AI requests under real constraints",
    "date": "2026-11-09",
    "readTime": "6 min read",
    "excerpt": "Model routing needs an explicit contract for quality, cost, fallback and evidence.",
    "body": "A router makes a consequential decision before any model answers: it decides where the work goes. That decision needs an explicit contract. Start with the task, not with the vendor.\n\n## Define the task contract\n\nEach request class should specify the required output, allowed data destinations, quality threshold, latency budget and cost ceiling. Record why a route was selected. A small model can produce a fluent answer that fails the task. Confidence is not proof.\n\n## Evaluate the classification step\n\nTest the router against a held-out corpus that represents real workload diversity. Measure classification errors independently from model errors. Short prompts can require complex reasoning, so length alone is a poor proxy for difficulty.\n\n## Make fallback predictable\n\nDefine which conditions allow fallback. A timeout before output is different from a failure after a tool has performed a side effect. Carry an idempotency key through retries and cap both the number of attempts and the overall deadline.\n\n## Keep a decision record\n\nRetain the task class, selected route, policy version, attempt sequence, latency and error outcome. Measure end-to-end performance rather than model response time alone. Reconcile recorded token use with billing evidence.\n\nA routing change is ready when tests show the expected behavior on both successful and failing requests. This is an architecture note, not a report of client deployments or measured savings."
  },
  {
    "slug": "llm-red-teaming",
    "title": "Turn agent red-teaming into release evidence",
    "date": "2026-11-09",
    "readTime": "6 min read",
    "excerpt": "An adversarial test is useful when it names a boundary, reproduces a failure and verifies the repair.",
    "body": "An adversarial prompt is a specimen. The engineering value comes from proving which trust boundary it crossed and ensuring the same class of failure cannot recur.\n\n## Enumerate authority\n\nList every resource an agent can read and every action it can take. Mark which inputs come from external users, retrieved documents and tools. Content from those sources is evidence for the task. It is not authority to change the task.\n\n## Test legitimate work alongside attacks\n\nBuild cases covering hostile instructions in documents, role spoofing, exfiltration attempts and malicious tool responses. Include a benign version of each workflow. Refusing all work is not a successful security control.\n\n## Preserve the specimen\n\nKeep the minimal reproducer, tool schema, model version, policy revision and execution trace. After a repair, rerun the original attack and variations that exercise the same mechanism.\n\n## Put authorization outside the model\n\nA model can propose sending a message or changing a record. The application should determine whether the action is authorized. Sensitive actions need their own permission checks and audit records.\n\nA single score may help compare releases. Raw traces and dispositions are needed for an independent review. This note describes a testing method, not a compliance certification."
  },
  {
    "slug": "spiffe-for-ai-workloads",
    "title": "Workload identity for short-lived inference services",
    "date": "2026-11-09",
    "readTime": "6 min read",
    "excerpt": "A workload needs a verifiable identity without embedding a long-lived secret in its container.",
    "body": "An inference worker might be created and destroyed many times during a working day. Permanent credentials are a poor fit for that lifecycle.\n\n## Separate identity from permission\n\nSPIFFE defines workload identities; SPIRE can issue them after attestation. The application still needs to decide what each workload is allowed to do. An inference worker might read a model registry, but it should not acquire permission to change billing records by holding a certificate.\n\n## Review the attestation boundary\n\nIdentity issuance depends on the trustworthiness of the scheduler, node and workload attestation path. A compromised host that can claim arbitrary identities defeats much of the benefit of short certificate lifetimes.\n\n## Plan rotation and failure\n\nWorkloads should renew credentials without interrupting permitted requests. Peers need current trust bundles. Document the behavior when the identity service fails; a fallback should never silently disable authentication.\n\n## Collect operational evidence\n\nRecord the presented workload identity, target service, policy revision and authorization outcome, while excluding secrets from the trace. Test replacement, rotation and rejection paths on the actual deployment boundary.\n\nA local demonstration only proves that two processes can authenticate. Production readiness requires observing how the whole system behaves under replacement and failure. Verify the implementation against current SPIFFE and SPIRE documentation."
  }
];
