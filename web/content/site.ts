export const site = {
  name: "Meridian Intelligence",
  tagline: "Independent AI laboratory, technology consultancy and venture builder.",
  email: "",
  nav: [
    { href: "/consulting", label: "Consultancy" },
    { href: "/research", label: "Laboratory" },
    { href: "/products", label: "Ventures" },
    { href: "/writing", label: "Insights" },
  ],
  research: [
    { title: "Agentic routing experiments", year: "2026", kind: "Research", href: "/writing/agentic-routing-for-enterprise", blurb: "How can routing decisions improve quality, cost and latency? We use repeatable comparisons and explicit failure cases." },
    { title: "AI workload identity", year: "2026", kind: "Security research", href: "/writing/spiffe-for-ai-workloads", blurb: "Exploring trust boundaries and short-lived credentials for AI services. Research is not proof of an accredited deployment." },
    { title: "Agent observability and evaluation", year: "2026", kind: "Experimental method", blurb: "Reproducible traces, baselines and regression tests for multi-step agent work. Failed experiments feed the next trial." },
  ],
  tooling: [
    { name: "agentgateway", status: "research", desc: "Candidate tools for routing, circuit breaking and cost attribution. Readiness is evaluated separately." },
    { name: "llm-benchmarking", status: "research", desc: "Benchmark design comparing model quality, time and cost against a fixed baseline." },
    { name: "spire-agent-ai", status: "research", desc: "Workload identity methods for short-lived AI services and agent infrastructure." },
  ],
  consulting: [
    { title: "AI strategy and architecture", desc: "Technical advisory, feasibility, platform decisions and investment roadmaps." },
    { title: "Applied AI engineering", desc: "Intelligent applications, integrations, automation and operational AI platforms." },
    { title: "Autonomous systems", desc: "Agent orchestration and workflow automation designed for real-world operations." },
    { title: "Research partnerships", desc: "Controlled AI experimentation, benchmarking and proof of feasibility." },
  ],
  posts: [
    { slug: "agentic-routing-for-enterprise", title: "Agentic Routing for the Enterprise", date: "2025-01-15", excerpt: "Routing models by intent is a hypothesis, tested against quality, cost and latency." },
    { slug: "llm-red-teaming", title: "LLM Red-Teaming at Scale", date: "2024-11-20", excerpt: "Why red-team findings belong in a repeatable regression suite." },
    { slug: "spiffe-for-ai-workloads", title: "SPIFFE for AI Workloads", date: "2024-09-05", excerpt: "Identity trade-offs for short-lived inference services." },
  ],
};
