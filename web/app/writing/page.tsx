import Link from "next/link";
import { posts } from "@/content/posts";
import { Reveal } from "@/components/Reveal";
import type { Metadata } from "next";
export const metadata: Metadata = { title: "Writing", description: "Essays on agentic routing, LLM red-teaming, and SPIFFE for AI workloads." };

export default function WritingPage() {
  return (
    <div className="container section">
      <Reveal><div style={{ marginBottom: "64px" }}>
        <span className="tag tag-accent" style={{ marginBottom: "16px", display: "inline-flex" }}>Writing</span>
        <h1>Essays</h1>
        <p style={{ marginTop: "16px", color: "var(--ink-3)", fontSize: "18px", maxWidth: "60ch" }}>Long-form writing on production AI infrastructure. Based on what we’ve shipped, not what we’ve theorized.</p>
      </div></Reveal>
      <div style={{ display: "flex", flexDirection: "column", gap: "1px", background: "var(--rule)" }}>
        {posts.map((post) => (
          <Reveal key={post.slug}>
            <div style={{ background: "var(--white)", padding: "32px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "24px", flexWrap: "wrap" }}>
                <div style={{ display: "flex", flexDirection: "column", gap: "12px", flex: 1 }}>
                  <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
                    <span style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)" }}>{post.date}</span>
                    <span className="tag">{post.readTime}</span>
                  </div>
                  <h2 style={{ fontSize: "1.5rem", fontFamily: "var(--serif)", fontWeight: 500 }}>{post.title}</h2>
                  <p style={{ fontSize: "15px", color: "var(--ink-3)", lineHeight: 1.75, maxWidth: "72ch" }}>{post.excerpt}</p>
                </div>
                <Link href={`/writing/${post.slug}`} className="btn-secondary" style={{ flexShrink: 0 }}>Read →</Link>
              </div>
            </div>
          </Reveal>
        ))}
      </div>
    </div>
  );
}
