import { posts } from "@/content/posts";
import Link from "next/link";
import { Reveal } from "@/components/Reveal";
import type { Metadata } from "next";

// Next.js 15 hands `params` to a page as a Promise, and the generated route types enforce it
// (`Type 'Props' does not satisfy the constraint 'PageProps'`). Await it; do not read it synchronously.
interface Props { params: Promise<{ slug: string }> }
export async function generateStaticParams() { return posts.map((p) => ({ slug: p.slug })); }
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const post = posts.find((p) => p.slug === slug);
  if (!post) return {};
  return { title: post.title, description: post.excerpt, openGraph: { type: "article", publishedTime: post.date, authors: ["Meridian Intelligence"] } };
}

function renderBody(body: string) {
  return body.split("\n\n").map((block, i) => {
    if (block.startsWith("## ")) return <h2 key={i} style={{ fontFamily: "var(--serif)", fontSize: "1.6rem", fontWeight: 500, marginTop: "40px", marginBottom: "16px" }}>{block.slice(3)}</h2>;
    if (block.startsWith("**") && block.includes("**\n")) {
      const [title, ...rest] = block.split("\n");
      return (
        <div key={i} style={{ marginTop: "24px", marginBottom: "8px" }}>
          <p style={{ fontFamily: "var(--mono)", fontSize: "11px", fontWeight: 500, color: "var(--accent)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "12px" }}>{title.replace(/\*\*/g, "")}</p>
          {rest.map((line, j) => <p key={j} style={{ marginBottom: "8px" }}>{line.replace(/\*\*(.*?)\*\*/g, "$1")}</p>)}
        </div>
      );
    }
    return <p key={i} style={{ marginBottom: "16px", lineHeight: 1.8, color: "var(--ink-2)", fontSize: "16px" }}>{block.replace(/\*\*(.*?)\*\*/g, (_, m) => m)}</p>;
  });
}

export default async function PostPage({ params }: Props) {
  const { slug } = await params;
  const post = posts.find((p) => p.slug === slug);
  if (!post) return null;
  return (
    <div className="container section">
      <div style={{ maxWidth: "768px", margin: "0 auto" }}>
        <Reveal>
          <div style={{ marginBottom: "48px" }}>
            <Link href="/writing" style={{ fontFamily: "var(--mono)", fontSize: "12px", color: "var(--ink-3)", textDecoration: "none" }}>← Writing</Link>
          </div>
          <div style={{ display: "flex", gap: "12px", alignItems: "center", marginBottom: "24px", flexWrap: "wrap" }}>
            <span style={{ fontFamily: "var(--mono)", fontSize: "12px", color: "var(--ink-3)" }}>{post.date}</span>
            <span className="tag">{post.readTime}</span>
          </div>
          <h1 style={{ fontFamily: "var(--serif)", fontSize: "clamp(2rem, 4vw, 3rem)", marginBottom: "24px" }}>{post.title}</h1>
          <p style={{ fontSize: "18px", color: "var(--ink-3)", lineHeight: 1.7, marginBottom: "48px", borderBottom: "1px solid var(--rule)", paddingBottom: "48px" }}>{post.excerpt}</p>
        </Reveal>
        <Reveal>
          <div>{renderBody(post.body)}</div>
        </Reveal>
        <div style={{ marginTop: "64px", paddingTop: "32px", borderTop: "1px solid var(--rule)" }}>
          <Link href="/writing" className="btn-secondary">← More essays</Link>
        </div>
      </div>
    </div>
  );
}
