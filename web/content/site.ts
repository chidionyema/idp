export const site = {
  name: "Meridian Intelligence",
  tagline: "AI systems engineering for real operating environments.",
  nav: [
    { href: "/#capabilities", label: "Capabilities" },
    { href: "/#approach", label: "Approach" },
    { href: "/case-studies", label: "Engineering work" },
    { href: "/consulting", label: "Services" },
    { href: "/contact", label: "Contact" },
  ],
  research: [
    {
      title: "Model routing for enterprise systems",
      year: "2025",
      kind: "Architecture",
      href: "/writing/agentic-routing-for-enterprise",
      blurb: "Model selection, fallback behaviour and trade-offs between quality, cost and response time.",
    },
    {
      title: "SPIFFE/SPIRE for AI workload identity",
      year: "2025",
      kind: "Security",
      href: "/writing/spiffe-for-ai-workloads",
      blurb: "Issuing short-lived identities to inference workloads, and where trust boundaries matter.",
    },
    {
      title: "Observability for autonomous workflows",
      year: "2025",
      kind: "Observability",
      blurb: "A trace model that links user instructions to model calls, tools, state changes and outcomes.",
    },
  ],
  tooling: [
    { name: "agentgateway", status: "reference", desc: "A reference pattern for routing, fallback and per-workload cost attribution." },
    { name: "llm-benchmarking", status: "reference", desc: "An evaluation approach for model and prompt changes against repeatable scenarios." },
    { name: "spire-agent-ai", status: "reference", desc: "An identity integration pattern for short-lived AI services." },
  ],
  consulting: [
    { title: "AI systems architecture", desc: "Understand workload requirements, evaluate the existing infrastructure and engineer model routing, retrieval and identity around measurable constraints." },
    { title: "Autonomous operations", desc: "Design durable execution, bounded recovery and explicit human intervention points around the work your business needs done." },
    { title: "Evaluation and assurance", desc: "Build repeatable test cases, connected execution traces and independent verification that survives beyond a demo." },
  ],
  posts: [
    { slug: "agentic-routing-for-enterprise", title: "Agentic Routing for the Enterprise", date: "2025-01-15", excerpt: "Technical notes on model routing, fallback and cost controls." },
    { slug: "llm-red-teaming", title: "LLM Red-Teaming at Scale", date: "2024-11-20", excerpt: "Turning adversarial findings into automated regression tests." },
    { slug: "spiffe-for-ai-workloads", title: "SPIFFE for AI Workloads", date: "2024-09-05", excerpt: "Identity for short-lived inference services." },
  ],
};
