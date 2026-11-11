import Link from "next/link";
import type { Metadata } from "next";
import { posts } from "@/content/posts";

export const metadata: Metadata = {
  title: "Insights",
  description: "Research notes and technical thinking from Meridian Intelligence on agent systems, AI evaluation and secure engineering.",
};

export default function WritingPage() {
  return <div className="mi-interior">
    <section className="mi-page-hero" aria-labelledby="insights-heading">
      <div className="mi-shell">
        <span className="mi-eyebrow">MERIDIAN / INSIGHTS</span>
        <h1 id="insights-heading">IDEAS NEED<br/><em>EVIDENCE.</em></h1>
        <div className="mi-page-hero-bottom"><p>Notes from the laboratory. Methods, trade-offs and technical arguments. A written hypothesis is a starting point for testing.</p><Link href="/research" className="mi-button mi-button-gold">Explore the laboratory <span aria-hidden="true">↗</span></Link></div>
      </div>
    </section>
    <section className="mi-section mi-insights-section" aria-labelledby="insights-list-heading">
      <div className="mi-shell">
        <div className="mi-section-intro"><span className="mi-eyebrow" id="insights-list-heading">FIELD NOTES / THE ARCHIVE</span><p>QUESTIONS, METHODS, EVIDENCE</p></div>
        <div className="mi-insights-list">
          {posts.map((post, index) => <article className="mi-insights-row" key={post.slug}>
            <span className="mi-portfolio-number">{String(index + 1).padStart(2, "0")} / NOTE</span>
            <div>
              <p className="mi-insights-meta"><time dateTime={post.date}>{post.date}</time><span>{post.readTime}</span></p>
              <h2><Link href={`/writing/${post.slug}`}>{post.title}</Link></h2>
              <p>{post.excerpt}</p>
            </div>
            <Link className="mi-insights-action" href={`/writing/${post.slug}`} aria-label={`Read ${post.title}`}>Read note <span aria-hidden="true">↗</span></Link>
          </article>)}
        </div>
      </div>
    </section>
  </div>;
}
