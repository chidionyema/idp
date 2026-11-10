"use client";

import { useRef, useState } from "react";

type ResearchSource = { id: string; section: string; relevance: number; url: string };
type ResearchAnswer = { answer: string; sources: ResearchSource[]; mode: string; disclaimer?: string };

const SUGGESTIONS = [
  "How does SPIFFE work with ephemeral AI containers?",
  "What is the minimum infrastructure for a production LLM proxy?",
  "How do you measure latency in an agentic pipeline?",
  "What does a circuit breaker look like for LLM routing?",
  "How do you red-team an LLM pipeline?",
];

const THEMES = [
  { tag: "Routing", description: "Fallbacks, model selection and circuit breakers" },
  { tag: "Identity", description: "Workload identity for short-lived AI systems" },
  { tag: "Observability", description: "Tracing, latency budgets and evaluation" },
  { tag: "Security", description: "Prompt injection, red-teaming and safeguards" },
];

export function ResearchQA() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ResearchAnswer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<{ question: string; answer: ResearchAnswer }[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleAsk(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const question = query.trim();
    if (!question || loading) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch("/api/research/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: question }),
      });
      const payload: unknown = await response.json().catch(() => null);
      if (!response.ok) {
        const serverError =
          payload && typeof payload === "object" && "error" in payload && typeof payload.error === "string"
            ? payload.error
            : "The research service could not answer that question. Please try again.";
        throw new Error(serverError);
      }
      if (!payload || typeof payload !== "object" || !("answer" in payload) || typeof payload.answer !== "string" ||
          !("sources" in payload) || !Array.isArray(payload.sources)) {
        throw new Error("The research service returned an unexpected response.");
      }
      const answer = payload as ResearchAnswer;
      setResult(answer);
      setHistory((previous) => [{ question, answer }, ...previous.filter((item) => item.question !== question).slice(0, 3)]);
      setQuery("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The research service is unavailable. Please retry.");
    } finally {
      setLoading(false);
    }
  }

  function selectSuggestion(question: string, answer?: ResearchAnswer) {
    setQuery(question);
    if (answer) {
      setResult(answer);
      setError(null);
    }
    inputRef.current?.focus();
  }

  return (
    <div className="mi-qa-workspace">
      <div className="mi-qa-sidebar">
        <form className="mi-qa-form" onSubmit={handleAsk}>
          <label className="mi-qa-label" htmlFor="mi-research-question">ASK THE LABORATORY</label>
          <div className="mi-qa-input-row">
            <input
              id="mi-research-question"
              ref={inputRef}
              name="question"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="What would you like to investigate?"
              autoComplete="off"
              maxLength={1000}
              required
            />
            <button type="submit" disabled={loading || !query.trim()} aria-label="Ask this question">
              <span>Ask</span><span aria-hidden="true">↗</span>
            </button>
          </div>
          <p className="mi-qa-hint">Search the published notes. Results quote the articles; they do not verify their claims.</p>
        </form>
        <div className="mi-qa-prompts">
          <p className="mi-qa-label">EXPLORE A QUESTION</p>
          <div className="mi-qa-suggestion-list">
            {SUGGESTIONS.map((question) => (
              <button type="button" className="mi-qa-suggestion" key={question} onClick={() => selectSuggestion(question)}>
                <span>{question}</span><span aria-hidden="true">↗</span>
              </button>
            ))}
          </div>
        </div>
        {history.length > 0 && (
          <div className="mi-qa-prompts">
            <p className="mi-qa-label">RECENT QUESTIONS</p>
            <div className="mi-qa-suggestion-list">
              {history.map(({ question, answer }) => (
                <button type="button" key={question} className="mi-qa-suggestion mi-qa-history" onClick={() => selectSuggestion(question, answer)}>
                  <span>{question}</span><span aria-hidden="true">↗</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="mi-qa-panel" role="region" aria-label="Research answer" aria-live="polite" aria-busy={loading}>
        {!result && !loading && !error && (
          <div className="mi-qa-empty">
            <div className="mi-qa-panel-kicker">THE RESEARCH DESK <span>001 / ARTICLE SEARCH</span></div>
            <h3>Start with a question.</h3>
            <p>Explore our written technical methods, design choices and open questions. Follow every result to its article.</p>
            <div className="mi-qa-themes">
              {THEMES.map(({ tag, description }) => (
                <div className="mi-qa-theme" key={tag}>
                  <h4>{tag}</h4><p>{description}</p>
                </div>
              ))}
            </div>
          </div>
        )}
        {loading && (
          <div className="mi-qa-feedback" role="status" aria-live="polite">
            <span className="mi-qa-progress" aria-hidden="true" />
            <p>Searching published research notes…</p>
          </div>
        )}
        {error && (
          <div className="mi-qa-feedback mi-qa-error" role="alert">
            <h3>We couldn&apos;t retrieve an answer.</h3>
            <p>{error}</p>
            <button type="button" onClick={() => inputRef.current?.focus()}>Edit your question ↗</button>
          </div>
        )}
        {result && (
          <div className="mi-qa-answer">
            <div className="mi-qa-panel-kicker">
              <span>MATCHED RESEARCH NOTE</span>
              <span>{result.mode === "published-excerpts" ? "EXCERPT FROM PUBLISHED ARTICLE" : "ARTICLE SEARCH"}</span>
            </div>
            <div className="mi-qa-answer-copy">
              {result.answer.split("\n\n").filter(Boolean).map((paragraph, index) => <p key={index}>{paragraph}</p>)}
            </div>
            {result.disclaimer && <p className="mi-qa-disclaimer">{result.disclaimer}</p>}
            {result.sources.length > 0 && (
              <div className="mi-qa-sources">
                <h4>Source sections</h4>
                <p>Read the article sections. Editorial notes do not establish independent experimental proof.</p>
                <div className="mi-qa-sources-list">
                  {result.sources.map((source, index) => (
                    <a className="mi-qa-source" key={source.id + "-" + index} href={source.url.startsWith("/writing/") ? source.url : "/writing"}>
                      <strong>{source.section}</strong><span>Read source ↗</span>
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
