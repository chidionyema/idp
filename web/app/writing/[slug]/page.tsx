import { posts } from "@/content/posts";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";

interface Props { params: Promise<{ slug: string }> }

const slugify = (value: string) => value.toLowerCase()
  .replace(/[^a-z0-9\s-]/g, "")
  .trim()
  .replace(/\s+/g, "-");

export async function generateStaticParams() {
  return posts.map(post => ({ slug: post.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const post = posts.find(item => item.slug === slug);
  if (!post) return {};
  return {
    title: post.title,
    description: post.excerpt,
    openGraph: { type: "article", publishedTime: post.date, authors: ["Meridian Intelligence"] },
  };
}

function Body({ body }: { body: string }) {
  return (
    <div className="mi-article-body">
      {body.split("\n\n").filter(Boolean).map((block, index) => (
        block.startsWith("## ")
          ? <h2 key={index} id={slugify(block.slice(3))}>{block.slice(3)}</h2>
          : <p key={index}>{block.replace(/\*\*(.*?)\*\*/g, "$1")}</p>
      ))}
    </div>
  );
}

export default async function PostPage({ params }: Props) {
  const { slug } = await params;
  const post = posts.find(item => item.slug === slug);
  if (!post) notFound();

  return (
    <div className="mi-interior">
      <section className="mi-article-hero mi-page-hero" aria-labelledby="mi-article-title">
        <div className="mi-shell">
          <Link className="mi-article-back" href="/writing">← All research notes</Link>
          <div className="mi-article-meta"><span>MERIDIAN / RESEARCH NOTES</span><time dateTime={post.date}>{post.date}</time><span>{post.readTime}</span></div>
          <h1 id="mi-article-title">{post.title}</h1>
          <div className="mi-page-hero-bottom">
            <p>{post.excerpt}</p>
            <span className="mi-article-edition" aria-hidden="true">FIELD NOTE / 001</span>
          </div>
        </div>
      </section>

      <article className="mi-article-shell mi-shell">
        <div className="mi-article-main">
          <p className="mi-article-caveat">TECHNICAL FIELD NOTE · Methods and design hypotheses. Measured results require independently traceable evidence.</p>
          <Body body={post.body} />
          {post.references && post.references.length > 0 && (
            <section className="mi-article-references" aria-labelledby="mi-references-heading">
              <h2 id="mi-references-heading">Primary references</h2>
              <p>Specifications and guidance relevant to the methods discussed. These links are not endorsements or evidence of a deployed implementation.</p>
              <div className="mi-article-reference-list">
                {post.references.map(reference => (
                  <a href={reference.url} key={reference.url} target="_blank" rel="noopener noreferrer">
                    {reference.label}<span aria-hidden="true">↗</span>
                  </a>
                ))}
              </div>
            </section>
          )}
          <div className="mi-article-end">
            <p>Question the assumptions. Test the implementation.</p>
            <Link href="/research" className="mi-button mi-button-dark">Explore the laboratory <span aria-hidden="true">↗</span></Link>
          </div>
        </div>
      </article>
    </div>
  );
}
