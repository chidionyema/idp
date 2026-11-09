export const site = {
  name: "Merian Intelligence",
  tagline: "An applied AI laboratory developing research-led products for enterprise and personal markets.",
  email: "",
  nav: [
    { href: "/research", label: "Research" },
    { href: "/products", label: "Products" },
    { href: "/consulting", label: "Enterprise" },
    { href: "/writing", label: "Insights" },
  ],
  research: [
    { title: "Agentic routing experiments", year: "2026", kind: "Research", href: "/writing/agentic-routing-for-enterprise",
      blurb: "How can a routing decision improve quality, cost and latency together? Our approach starts with comparable trials and explicit failure cases." },
    { title: "AI workload identity", year: "2026", kind: "Security research", href: "/writing/spiffe-for-ai-workloads",
      blurb: "Exploring trust boundaries and short-lived credentials in AI service infrastructure. Research is not proof of an accredited deployment." },
    { title: "Agent observability and evaluation", year: "2026", kind: "Experimental method",
      blurb: "Reproducible traces, controlled baselines and regression tests for multi-step agent work. Failed experiments become evidence for the next trial." },
  ],
  tooling: [
    { name: "agentgateway", status: "research", desc: "Candidate tools for routing, circuit breaking and model-cost attribution. Commercial readiness is evaluated separately." },
    { name: "llm-benchmarking", status: "research", desc: "Benchmark design and experiments comparing quality, time and cost against a fixed baseline." },
    { name: "spire-agent-ai", status: "research", desc: "Workload identity research for short-lived AI services and agent infrastructure." },
  ],
  consulting: [
    { title: "Research and feasibility", desc: "Investigate the hypothesis and find the evidence that would challenge it before committing to a large build." },
    { title: "Product prototyping", desc: "Turn promising research into working demonstrations with transparent benchmarks and known limitations." },
    { title: "Commercial AI engineering", desc: "Move validated capabilities into reliable enterprise use with independent security, performance and customer-path proof." },
  ],
  posts: [
    { slug: "agentic-routing-for-enterprise", title: "Agentic Routing for the Enterprise", date: "2025-01-15", excerpt: "Routing models by intent is one hypothesis. It needs quality, cost and latency comparisons to earn adoption." },
    { slug: "llm-red-teaming", title: "LLM Red-Teaming at Scale", date: "2024-11-20", excerpt: "Why red-team findings belong in a repeatable regression suite." },
    { slug: "spiffe-for-ai-workloads", title: "SPIFFE for AI Workloads", date: "2024-09-05", excerpt: "Identity trade-offs for short-lived inference services." },
  ],
};
