"use client";
import { useCallback, useEffect, useState } from "react";
import { LIMITS, validateContact, type ContactErrors } from "@/lib/contact";

type ContactFields = { name: string; email: string; company: string; message: string; website: string };
const initialForm: ContactFields = { name: "", email: "", company: "", message: "", website: "" };

export default function ContactPage() {
  const [form, setForm] = useState<ContactFields>(initialForm);
  const [errors, setErrors] = useState<ContactErrors>({});
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [failure, setFailure] = useState<string | null>(null);
  const [availability, setAvailability] = useState<"checking" | "available" | "unavailable" | "unknown">("checking");

  // Read-only readiness probe; no customer details are sent. If it fails, we
  // don't guess: keep the form available and let POST report delivery failure.
  const checkAvailability = useCallback(async () => {
    setAvailability("checking");
    try {
      const response = await fetch("/api/contact", { method: "GET", cache: "no-store" });
      const data: unknown = await response.json();
      if (!response.ok || !data || typeof data !== "object" ||
          !("acceptingEnquiries" in data) || typeof data.acceptingEnquiries !== "boolean") {
        setAvailability("unknown");
        return;
      }
      setAvailability(data.acceptingEnquiries ? "available" : "unavailable");
    } catch {
      setAvailability("unknown");
    }
  }, []);

  useEffect(() => { void checkAvailability(); }, [checkAvailability]);

  function update(field: keyof ContactFields, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
    if (status === "error") { setFailure(null); setStatus("idle"); }
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (status === "sending") return;
    const validation = validateContact(form);
    if (!validation.ok) { setErrors(validation.errors); setStatus("idle"); return; }

    setErrors({});
    setFailure(null);
    setStatus("sending");
    try {
      const response = await fetch("/api/contact", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(form),
      });
      if (response.ok) { setStatus("sent"); return; }
      const body = (await response.json().catch(() => ({}))) as { errors?: ContactErrors };
      if (body.errors && Object.keys(body.errors).length > 0) {
        setErrors(body.errors);
        setStatus("idle");
        return;
      }
      const retry = Math.max(1, Math.ceil(Number(response.headers.get("retry-after") || "60") / 60));
      if (response.status === 503) setAvailability("unavailable");
      setFailure(response.status === 429
        ? `Too many attempts from this network. Please try again in ${retry} minute${retry === 1 ? "" : "s"}.`
        : "The enquiry service is unavailable at the moment. Your message has not been sent. Please try again later.");
      setStatus("error");
    } catch {
      setFailure("We couldn't connect to the enquiry service. Your message has not been sent. Please try again later.");
      setStatus("error");
    }
  }

  return (
    <div className="mi-interior">
      <section className="mi-page-hero mi-contact-hero" aria-labelledby="contact-heading">
        <div className="mi-shell">
          <span className="mi-eyebrow">MERIDIAN / START A CONVERSATION</span>
          <h1 id="contact-heading">LET&apos;S BUILD<br/><em>SOMETHING REAL.</em></h1>
          <div className="mi-page-hero-bottom">
            <p>Bring the challenge. An architecture decision, an AI system to build, or a research question worth testing. We&apos;ll start with what matters.</p>
            <span className="mi-contact-hero-mark" aria-hidden="true">M / 004 ↗</span>
          </div>
        </div>
      </section>

      <section className="mi-contact-section" aria-labelledby="enquiry-heading">
        <div className="mi-shell mi-contact-grid">
          <aside className="mi-contact-aside">
            <span className="mi-eyebrow">01 / TELL US THE CHALLENGE</span>
            <h2>Good work starts with a clear problem.</h2>
            <p>What exists today? What needs to change? What would make the investment worthwhile?</p>
            <div className="mi-contact-aside-rule" />
            <span className="mi-contact-small-label">AREAS OF INTEREST</span>
            <p className="mi-contact-topics">AI strategy <span>/</span> Engineering <span>/</span> Autonomous systems <span>/</span> Research partnerships <span>/</span> Ventures</p>
            <p className="mi-contact-discretion">Please don&apos;t include passwords, customer records or sensitive credentials in your enquiry.</p>
          </aside>

          <div className="mi-contact-form-card">
            {status === "sent" ? (
              <div className="mi-contact-success" role="status" aria-live="polite">
                <span className="mi-eyebrow">ENQUIRY RECEIVED</span>
                <h2>Thank you for reaching out.</h2>
                <p>Your message was accepted by our enquiry service. We&apos;ll review the details before taking the next step.</p>
              </div>
            ) : availability === "unavailable" ? (
              <div className="mi-contact-success" role="status" aria-live="polite">
                <span className="mi-eyebrow">ENQUIRY SERVICE / TEMPORARILY UNAVAILABLE</span>
                <h2>Online enquiries are paused.</h2>
                <p>We cannot accept a message while the delivery service is unavailable. Nothing has been sent. Please check again shortly.</p>
                <button type="button" className="mi-button mi-button-dark" onClick={() => void checkAvailability()}>
                  Check again <span aria-hidden="true">↗</span>
                </button>
              </div>
            ) : availability === "checking" ? (
              <div className="mi-contact-success" role="status" aria-live="polite">
                <span className="mi-eyebrow">ENQUIRY SERVICE</span>
                <h2>Checking availability.</h2>
                <p>Confirming the enquiry destination before collecting your details.</p>
              </div>
            ) : (
              <>
                <div className="mi-contact-form-intro">
                  <span className="mi-eyebrow">PROJECT ENQUIRY / 001</span>
                  <h2 id="enquiry-heading">Tell us what you&apos;re building.</h2>
                  <p>Share enough context to make the first conversation useful.</p>
                </div>
                <form onSubmit={submit} noValidate aria-busy={status === "sending"} className="mi-contact-form">
                  <fieldset disabled={status === "sending"} className="mi-contact-fields">
                    <legend className="mi-visually-hidden">Project enquiry details</legend>
                    <div className="mi-contact-field-row">
                      <div className="mi-contact-field">
                        <label htmlFor="contact-name">Your name <span aria-hidden="true">*</span></label>
                        <input id="contact-name" name="name" type="text" autoComplete="name" required maxLength={LIMITS.name.max}
                          value={form.name} onChange={(e) => update("name", e.target.value)}
                          aria-invalid={Boolean(errors.name)} aria-describedby={errors.name ? "contact-name-error" : undefined} />
                        {errors.name && <p id="contact-name-error" className="mi-contact-error">{errors.name}</p>}
                      </div>
                      <div className="mi-contact-field">
                        <label htmlFor="contact-email">Work email <span aria-hidden="true">*</span></label>
                        <input id="contact-email" name="email" type="email" autoComplete="email" inputMode="email" required maxLength={LIMITS.email.max}
                          value={form.email} onChange={(e) => update("email", e.target.value)}
                          aria-invalid={Boolean(errors.email)} aria-describedby={errors.email ? "contact-email-error" : undefined} />
                        {errors.email && <p id="contact-email-error" className="mi-contact-error">{errors.email}</p>}
                      </div>
                    </div>
                    <div className="mi-contact-field">
                      <label htmlFor="contact-company">Company <span className="mi-contact-optional">(optional)</span></label>
                      <input id="contact-company" name="company" type="text" autoComplete="organization" maxLength={LIMITS.company.max}
                        value={form.company} onChange={(e) => update("company", e.target.value)}
                        aria-invalid={Boolean(errors.company)} aria-describedby={errors.company ? "contact-company-error" : undefined} />
                      {errors.company && <p id="contact-company-error" className="mi-contact-error">{errors.company}</p>}
                    </div>
                    <div className="mi-contact-field">
                      <label htmlFor="contact-message">What are you trying to achieve? <span aria-hidden="true">*</span></label>
                      <textarea id="contact-message" name="message" rows={6} required minLength={LIMITS.message.min}
                        maxLength={LIMITS.message.max} value={form.message} onChange={(e) => update("message", e.target.value)}
                        aria-invalid={Boolean(errors.message)} aria-describedby={errors.message ? "contact-message-error" : "contact-message-help"} />
                      <p id="contact-message-help" className="mi-contact-field-hint">At least 20 characters. A few sentences are enough to begin.</p>
                      {errors.message && <p id="contact-message-error" className="mi-contact-error">{errors.message}</p>}
                    </div>
                    <div className="mi-contact-honeypot" aria-hidden="true">
                      <label htmlFor="contact-website">Website</label>
                      <input id="contact-website" name="website" type="text" tabIndex={-1} autoComplete="off"
                        value={form.website} onChange={(e) => update("website", e.target.value)} />
                    </div>
                  </fieldset>
                  <p className="mi-contact-notice" role={failure ? "alert" : "status"} aria-live="polite">{failure ?? (status === "sending" ? "Sending your enquiry…" : "")}</p>
                  <div className="mi-contact-form-footer">
                    <button className="mi-button mi-button-gold mi-contact-submit" type="submit" disabled={status === "sending"}>
                      {status === "sending" ? "Sending…" : "Send enquiry"} <span aria-hidden="true">↗</span>
                    </button>
                    <span className="mi-contact-required-note">* REQUIRED FIELDS</span>
                  </div>
                </form>
              </>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
