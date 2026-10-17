export const site = {
  name: "Meridian Intelligence",
  tagline: "AI infrastructure consulting for companies shipping production LLM systems.",
  email: "hello@meridian.ai",
  nav: [
    { href: "/research", label: "Research" },
    { href: "/case-studies", label: "Case Studies" },
    { href: "/tooling", label: "Tooling" },
    { href: "/consulting", label: "Consulting" },
    { href: "/writing", label: "Writing" },
  ],
  research: [
    {
      title: "Agentic Routing for Enterprise",
      year: "2025",
      kind: "Framework",
      blurb: "Your traffic isn't one shape. Most requests are classification or extraction that a cheap model handles at a fraction of the price. Route on that difference and spend drops by 60–80% with no movement in your quality metric. Here's the architecture, including the two failure modes we hit first.",
    },
    {
      title: "SPIFFE/SPIRE in AI Workload Identity",
      year: "2025",
      kind: "Security",
      blurb: "An inference server might live ninety seconds before it's replaced. You can't hand it a certificate. SPIFFE/SPIRE gives it a cryptographic identity it can prove in that window, and it works with vLLM and LiteLLM without touching your application code.",
    },
    {
      title: "Observability for Agentic Pipelines",
      year: "2025",
      kind: "Observability",
      blurb: "One user request can fan out into three tool calls, two model calls and a synthesis step. When it goes wrong you need to see the whole shape at once, not four dashboards. This is the span structure that makes that possible.",
    },
  ],
  tooling: [
    {
      name: "agentgateway",
      status: "stable",
      desc: "The routing layer we deploy on every engagement. Classifies each request, opens a circuit when a provider degrades, and attributes every dollar to the team that spent it.",
    },
    {
      name: "llm-benchmarking",
      status: "stable",
      desc: "An eval harness that runs your prompts against 40 benchmarks and tests whether a change moved the number. Blocks the merge when it made things worse.",
    },
    {
      name: "spire-agent-ai",
      status: "beta",
      desc: "SPIRE workload API for AI runtimes. Rotates X.509 SVIDs without restarting the inference server, which is the part nobody wants to do at three in the morning.",
    },
  ],
  consulting: [
    {
      title: "AI Platform Architecture",
      desc: "We read what you have, name the failure modes, then design the routing, tracing and identity layers around your real latency and cost ceilings. Not a reference architecture. Yours.",
    },
    {
      title: "Security & Compliance",
      desc: "SOC 2 Type II, HIPAA, data residency. Workload identity for servers that live for ninety seconds. We've had a lot of practice getting a security reviewer to sign off.",
    },
    {
      title: "Evaluation & Fine-tuning",
      desc: "Red-teaming that produces a regression suite instead of a document. Eval pipelines that stop a bad model change before a customer finds it.",
    },
  ],
  posts: [
    {
      slug: "agentic-routing-for-enterprise",
      title: "Agentic Routing for the Enterprise",
      date: "2025-01-15",
      excerpt: "Most routing layers fail the same three ways. We hit all three in our first 12 deployments, and it took us two of them to notice.",
    },
    {
      slug: "llm-red-teaming",
      title: "LLM Red-Teaming at Scale",
      date: "2024-11-20",
      excerpt: "A weekend of jailbreak prompts produces a list. It doesn't produce anything that catches the next regression. Here's the difference.",
    },
    {
      slug: "spiffe-for-ai-workloads",
      title: "SPIFFE for AI Workloads",
      date: "2024-09-05",
      excerpt: "Short-lived inference servers can't hold a certificate. That's why most AI deployments have no workload identity at all.",
    },
  ],
};
