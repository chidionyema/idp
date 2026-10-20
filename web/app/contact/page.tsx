"use client";
import { useState } from "react";
import { Reveal } from "@/components/Reveal";

export default function ContactPage() {
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [form, setForm] = useState({ name: "", email: "", company: "", message: "", website: "" });
  const [errors, setErrors] = useState<Partial<typeof form>>({});
  const [failure, setFailure] = useState<string | null>(null);

  function validate() {
    const e: Partial<typeof form> = {};
    if (!form.name.trim()) e.name = "Required";
    if (!form.email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) e.email = "Valid email required";
    if (!form.message.trim() || form.message.length < 20) e.message = "Please describe your project (at least 20 characters)";
    return e;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length > 0) { setErrors(errs); return; }
    setErrors({});
    setFailure(null);
    setState("sending");

    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(form),
      });

      if (res.ok) { setState("sent"); return; }

      const body = await res.json().catch(() => ({}));

      // Field-level problems come back with a per-field map; anything else is a
      // failure the visitor cannot fix by editing the form.
      if (body?.errors) {
        setErrors(body.errors);
        setState("idle");
        return;
      }

      setFailure(
        res.status === 429
          ? `Too many messages from this network. Try again in ${Math.ceil(Number(res.headers.get("retry-after") || 60) / 60)} minutes.`
          : "We could not send that. Email us directly and we will pick it up."
      );
      setState("error");
    } catch {
      setFailure("That did not reach us — check your connection, or email us directly.");
      setState("error");
    }
  }

  return (
    <div className="container section">
      <div style={{ maxWidth: "640px", margin: "0 auto" }}>
        <Reveal><div style={{ marginBottom: "48px" }}>
          <span className="tag tag-accent" style={{ marginBottom: "16px", display: "inline-flex" }}>Contact</span>
          <h1>Talk to us</h1>
          <p style={{ marginTop: "16px", color: "var(--ink-3)", fontSize: "17px" }}>We take on a small number of projects each quarter. Tell us what you’re building and we’ll be in touch within two business days.</p>
        </div></Reveal>
        <Reveal>
          {state === "sent" ? (
            <div style={{ border: "1px solid var(--ok)", background: "rgba(5,150,105,0.05)", padding: "32px", textAlign: "center" }}>
              <p style={{ fontFamily: "var(--serif)", fontSize: "1.3rem", color: "var(--ok-text)", maxWidth: "none" }}>Message received.</p>
              <p style={{ color: "var(--ink-3)", marginTop: "8px", maxWidth: "none" }}>A person reads every one of these. Expect a reply within two business days. If it is urgent, <a href="mailto:hello@meridian.ai" style={{ color: "var(--accent)" }}>email us directly</a>.</p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} noValidate style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
              <fieldset style={{ border: "none", display: "flex", flexDirection: "column", gap: "20px" }}>
                <div>
                  <label htmlFor="name" style={{ display: "block", fontFamily: "var(--mono)", fontSize: "11px", fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--ink-3)", marginBottom: "8px" }}>Name</label>
                  <input id="name" type="text" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} autoComplete="name"
                    style={{ width: "100%", border: `1px solid ${errors.name ? "#DC2626" : "var(--rule)"}`, background: "var(--white)", padding: "12px 16px", fontSize: "14px", color: "var(--ink)", outline: "none", fontFamily: "inherit" }}
                    onFocus={(e) => { e.target.style.borderColor = "var(--accent)"; e.target.style.outline = "none"; }}
                    onBlur={(e) => e.target.style.borderColor = errors.name ? "#DC2626" : "var(--rule)"} />
                  {errors.name && <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "#DC2626", marginTop: "4px" }}>{errors.name}</p>}
                </div>
                <div>
                  <label htmlFor="email" style={{ display: "block", fontFamily: "var(--mono)", fontSize: "11px", fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--ink-3)", marginBottom: "8px" }}>Work email</label>
                  <input id="email" type="email" value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} autoComplete="email"
                    style={{ width: "100%", border: `1px solid ${errors.email ? "#DC2626" : "var(--rule)"}`, background: "var(--white)", padding: "12px 16px", fontSize: "14px", color: "var(--ink)", outline: "none", fontFamily: "inherit" }}
                    onFocus={(e) => e.target.style.borderColor = "var(--accent)"}
                    onBlur={(e) => e.target.style.borderColor = errors.email ? "#DC2626" : "var(--rule)"} />
                  {errors.email && <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "#DC2626", marginTop: "4px" }}>{errors.email}</p>}
                </div>
                <div>
                  <label htmlFor="company" style={{ display: "block", fontFamily: "var(--mono)", fontSize: "11px", fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--ink-3)", marginBottom: "8px" }}>Company <span style={{ color: "var(--ink-3)", fontWeight: 400 }}>(optional)</span></label>
                  <input id="company" type="text" value={form.company} onChange={(e) => setForm((f) => ({ ...f, company: e.target.value }))} autoComplete="organization"
                    style={{ width: "100%", border: "1px solid var(--rule)", background: "var(--white)", padding: "12px 16px", fontSize: "14px", color: "var(--ink)", outline: "none", fontFamily: "inherit" }}
                    onFocus={(e) => e.target.style.borderColor = "var(--accent)"}
                    onBlur={(e) => e.target.style.borderColor = "var(--rule)"} />
                </div>
                <div>
                  <label htmlFor="message" style={{ display: "block", fontFamily: "var(--mono)", fontSize: "11px", fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--ink-3)", marginBottom: "8px" }}>What are you building?</label>
                  <textarea id="message" value={form.message} onChange={(e) => setForm((f) => ({ ...f, message: e.target.value }))} rows={6}
                    style={{ width: "100%", border: `1px solid ${errors.message ? "#DC2626" : "var(--rule)"}`, background: "var(--white)", padding: "12px 16px", fontSize: "14px", color: "var(--ink)", outline: "none", fontFamily: "inherit", resize: "vertical" }}
                    onFocus={(e) => e.target.style.borderColor = "var(--accent)"}
                    onBlur={(e) => e.target.style.borderColor = errors.message ? "#DC2626" : "var(--rule)"} />
                  {errors.message && <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "#DC2626", marginTop: "4px" }}>{errors.message}</p>}
                </div>
              {/* Honeypot: positioned off-screen rather than display:none, so the
                  automated fillers that skip hidden inputs still trip it. */}
              <div aria-hidden="true" style={{ position: "absolute", left: "-9999px", width: "1px", height: "1px", overflow: "hidden" }}>
                <label htmlFor="website">Website</label>
                <input id="website" name="website" type="text" tabIndex={-1} autoComplete="off" value={form.website}
                  onChange={(e) => setForm((f) => ({ ...f, website: e.target.value }))} />
              </div>
              </fieldset>
              <p role="status" aria-live="polite" style={{ maxWidth: "none", minHeight: "1.2em", fontFamily: "var(--mono)", fontSize: "12px", color: state === "error" ? "#B91C1C" : "var(--ink-3)" }}>
                {failure ?? (state === "sending" ? "Sending…" : "")}
              </p>
              <button type="submit" disabled={state === "sending"} className="btn-primary" style={{ alignSelf: "flex-start" }}>
                {state === "sending" ? <><span className="pulse-dot" />Sending…</> : "Send message →"}
              </button>
            </form>
          )}
        </Reveal>
      </div>
    </div>
  );
}
