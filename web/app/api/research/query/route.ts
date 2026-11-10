import { NextRequest, NextResponse } from "next/server";
import { posts, type Post } from "@/content/posts";

type Section = {
  post: Post;
  title: string;
  text: string;
  href: string;
  id: string;
};

const STOP_WORDS = new Set([
  "the", "and", "for", "with", "that", "this", "what", "when", "where", "which",
  "does", "from", "into", "are", "was", "how", "you", "your", "about", "our",
  "can", "should", "would", "minimum", "look", "like", "work", "works", "have"
]);

const slugify = (value: string) => value.toLowerCase()
  .replace(/[^a-z0-9\s-]/g, "")
  .trim()
  .replace(/\s+/g, "-");

function keywords(value: string): string[] {
  return [...new Set(value.toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .split(/\s+/)
    .filter(word => word.length >= 3 && !STOP_WORDS.has(word)))];
}

function sectionsFor(post: Post): Section[] {
  const result: Section[] = [];
  let title = "Overview";
  let paragraphs: string[] = [];
  const flush = () => {
    if (!paragraphs.length) return;
    const suffix = title === "Overview" ? "" : "#" + slugify(title);
    result.push({
      post,
      title,
      text: paragraphs.join("\n\n"),
      href: "/writing/" + post.slug + suffix,
      id: post.slug + suffix,
    });
    paragraphs = [];
  };
  for (const block of post.body.split(/\n\n+/)) {
    if (block.startsWith("## ")) {
      flush();
      title = block.slice(3).trim();
    } else if (block.trim()) {
      paragraphs.push(block.trim());
    }
  }
  flush();
  return result;
}

// This index is compiled from the very same published articles used by /writing/[slug].
// No separate, unreviewed answer catalogue. No claims of LLM synthesis or external verification.
const SECTIONS = posts.flatMap(sectionsFor);

function relevance(section: Section, terms: string[]): number {
  const title = (section.post.title + " " + section.title).toLowerCase();
  const excerpt = section.post.excerpt.toLowerCase();
  const body = section.text.toLowerCase();
  let score = 0;
  for (const term of terms) {
    if (title.includes(term)) score += 5;
    if (excerpt.includes(term)) score += 2;
    if (body.includes(term)) score += 1;
  }
  return score;
}

export async function POST(request: NextRequest) {
  if (!(request.headers.get("content-type") ?? "").includes("application/json")) {
    return NextResponse.json({ error: "expected_application_json" }, { status: 415 });
  }

  const raw = await request.text();
  if (raw.length > 4500) {
    return NextResponse.json({ error: "payload_too_large" }, { status: 413 });
  }

  let query: unknown;
  try {
    const data: unknown = JSON.parse(raw);
    query = data && typeof data === "object" && "query" in data ? data.query : undefined;
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }
  if (typeof query !== "string" || !query.trim() || query.length > 1000) {
    return NextResponse.json({ error: "query must be between 1 and 1000 characters" }, { status: 400 });
  }

  const terms = keywords(query);
  if (terms.length === 0) {
    return NextResponse.json({
      answer: "Try a more specific technical question. Search currently covers our published notes.",
      sources: [],
      mode: "published-excerpts",
    });
  }

  const matches = SECTIONS
    .map(section => ({ section, score: relevance(section, terms) }))
    .filter(match => match.score > 0)
    .sort((a, b) => b.score - a.score || a.section.id.localeCompare(b.section.id))
    .slice(0, 3);

  if (matches.length === 0) {
    return NextResponse.json({
      answer: "We have no published note matching that question. Browse the research archive or ask a different question.",
      sources: [],
      mode: "published-excerpts",
    });
  }

  const best = matches[0].section;
  const passage = best.text.split("\n\n").slice(0, 2).join("\n\n").slice(0, 1200);
  return NextResponse.json({
    answer: "From our published note \"" + best.post.title + "\", section \"" + best.title + "\":\n\n" + passage,
    sources: matches.map(({ section, score }) => ({
      id: section.id,
      section: section.post.title + " / " + section.title,
      relevance: score,
      url: section.href,
    })),
    mode: "published-excerpts",
    disclaimer: "Published research notes are not independent validation of experimental or production performance.",
  }, { headers: { "Cache-Control": "no-store" } });
}
