"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

type Surface = "genesis" | "otto";
type Card = { label: string; value: string };
type Moment = { title: string; description: string; observedAt: string };
type Projection = {
  surface: Surface; headline: string; introduction: string; observedAt: string;
  sourceRevision: string; facts: Card[]; moments: Moment[];
};
type View = { surface: Surface; status: "observed" | "source_unavailable" | "not_granted"; data?: Projection };
type Room = { schema: "meridian.investor.room.v1"; viewer: string; accessExpiresAt: string;
  readOnly: true; surfaces: View[] };
type FetchState = "checking" | "ready" | "access_required" | "service_unavailable";

const surfaceText = {
  genesis: { name: "Genesis", index: "01 / HOW WORK COMES TOGETHER",
    description: "A closer look at the research behind coordinating complex work—and how we measure what really happened." },
  otto: { name: "OTTO", index: "02 / HOW LEADERS STAY INFORMED",
    description: "A closer look at the experience we're exploring for making progress, questions and decisions easier to manage." },
};

function hoursRemaining(expires: string, now: number) {
  const ms = Date.parse(expires) - now;
  if (!Number.isFinite(ms) || ms <= 0) return "Expired";
  const days = Math.floor(ms / 86_400_000);
  const hours = Math.ceil((ms % 86_400_000) / 3_600_000);
  return days > 0 ? days + (days === 1 ? " day" : " days") : Math.max(1, hours) + (hours === 1 ? " hour" : " hours");
}

export function InvestorRoom() {
  const [data, setData] = useState<Room | null>(null);
  const [state, setState] = useState<FetchState>("checking");
  const [selected, setSelected] = useState<Surface>("genesis");
  const [now, setNow] = useState(() => Date.now());
  const [refreshing, setRefreshing] = useState(false);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const response = await fetch("/api/investors/surfaces", {
        credentials: "same-origin", cache: "no-store", headers: { Accept: "application/json" },
        signal: AbortSignal.timeout(8000),
      });
      if (response.status === 401 || response.status === 403) {
        setData(null); setState("access_required"); return;
      }
      if (!response.ok) {
        setData(null); setState("service_unavailable"); return;
      }
      const body: unknown = await response.json();
      if (!body || typeof body !== "object" || !("schema" in body) ||
          body.schema !== "meridian.investor.room.v1" || !("readOnly" in body) ||
          body.readOnly !== true || !("surfaces" in body) || !Array.isArray(body.surfaces) ||
          !("accessExpiresAt" in body) || typeof body.accessExpiresAt !== "string" ||
          Date.parse(body.accessExpiresAt) <= Date.now()) {
        setData(null); setState("service_unavailable"); return;
      }
      setData(body as Room);
      setState("ready"); setNow(Date.now());
    } catch {
      setData(null); setState("service_unavailable");
    } finally { setRefreshing(false); }
  }, []);

  useEffect(() => {
    void refresh();
    const interval = window.setInterval(() => {
      setNow(Date.now());
      if (document.visibilityState === "visible") void refresh();
    }, 20_000);
    const onVisibility = () => { if (document.visibilityState === "visible") void refresh(); };
    document.addEventListener("visibilitychange", onVisibility);
    return () => { window.clearInterval(interval); document.removeEventListener("visibilitychange", onVisibility); };
  }, [refresh]);

  const accessExpired = data ? Date.parse(data.accessExpiresAt) <= now : false;
  const active = state === "ready" && data && !accessExpired ? data : null;
  const view = active?.surfaces.find(item => item.surface === selected);
  const source = surfaceText[selected];

  return <div className="mi-investor-room">
    <section className="mi-investor-room-hero">
      <div className="mi-shell">
        <div className="mi-investor-room-topline"><span>MERIDIAN / PRIVATE INVESTOR ROOM</span><span>READ-ONLY ACCESS</span></div>
        <h1>A closer look at<br/><em>what we&apos;re building.</em></h1>
        <p>This is your private window into selected parts of Meridian&apos;s research. We show what we can support with evidence, and say clearly when something is still in development.</p>
        {active && <div className="mi-investor-access-strip" role="status">
          <span>WELCOME, {active.viewer}</span>
          <span>ACCESS ENDS {new Date(active.accessExpiresAt).toLocaleString("en-GB", { dateStyle:"medium",timeStyle:"short", timeZone:"UTC" })} UTC</span>
          <strong>{hoursRemaining(active.accessExpiresAt, now)} remaining</strong>
        </div>}
      </div>
    </section>
    <div className="mi-shell mi-investor-room-body">
      {!active ? <section className="mi-investor-access-block" role="status">
        <span className="mi-eyebrow">PRIVATE ACCESS</span>
        <h2>{state === "checking" && !accessExpired ? "Checking your invitation." :
          (state === "access_required" || accessExpired) ? "Your access needs to be renewed." :
          "This private briefing is unavailable."}</h2>
        <p>{(state === "access_required" || accessExpired)
          ? "Investor access is granted to named guests for a limited period. A new identity check is required when the session ends. Only an approved, unexpired grant can open these views."
          : "We couldn't confirm an active, approved invitation. No operational information is displayed while access cannot be verified."}</p>
        <div className="mi-investor-room-buttons"><a href="/investors/access" className="mi-button mi-button-gold">Verify investor access <span aria-hidden="true">→</span></a>
          <Link href="/investors" className="mi-button mi-button-dark">Return to our vision <span aria-hidden="true">→</span></Link></div>
        <small>Access is checked on the server on every data request. A link alone never grants permission.</small>
      </section> : <>
        <section aria-labelledby="mi-room-choice" className="mi-investor-choice">
          <div className="mi-investor-choice-head"><div><span className="mi-eyebrow">EXPLORE THE RESEARCH</span>
            <h2 id="mi-room-choice">Two windows into the estate.</h2></div>
            <button type="button" onClick={() => void refresh()} disabled={refreshing} className="mi-investor-refresh">{refreshing ? "Rechecking access…" : "Refresh what we can verify"} <span aria-hidden="true">↻</span></button>
          </div>
          <div className="mi-investor-choices" role="group" aria-label="Choose an approved investor view">
            {(["genesis", "otto"] as const).map(id => <button key={id} type="button"
              className={selected === id ? "mi-investor-choice-active" : ""} aria-pressed={selected === id}
              onClick={() => setSelected(id)}>
              <span>{surfaceText[id].index}</span><strong>{surfaceText[id].name}</strong>
              <small>{surfaceText[id].description}</small>
              <span className="mi-investor-choice-availability">{active.surfaces.find(s=>s.surface===id)?.status === "observed" ? "Approved view available" :
                active.surfaces.find(s=>s.surface===id)?.status === "not_granted" ? "Not included in your invitation" : "Source unavailable"}</span>
            </button>)}
          </div>
        </section>
        <section className="mi-investor-viewport" aria-labelledby="mi-room-surface-heading">
          <div className="mi-investor-viewport-head"><span>{source.index}</span><span>PRIVATE / VIEW ONLY</span></div>
          <h2 id="mi-room-surface-heading">{source.name}<span className="mi-gold-stop">.</span></h2>
          {view?.status !== "observed" || !view.data ? <div className="mi-investor-source-unavailable">
            <strong>{view?.status === "not_granted" ? "This view is not part of your invitation." : "No approved live view is available."}</strong>
            <p>{view?.status === "not_granted"
              ? "Meridian shares each part of its research deliberately. You can ask for a broader briefing."
              : "We don't substitute sample data for real evidence. We will show this view when its source is accessible, current and approved for investors."}</p>
          </div> : <>
            <h3>{view.data.headline}</h3>
            <p className="mi-investor-viewport-intro">{view.data.introduction}</p>
            <div className="mi-investor-facts">{view.data.facts.map((f,i)=><article key={i}>
              <span>{f.label}</span><strong>{f.value}</strong>
            </article>)}</div>
            <div className="mi-investor-moments"><h4>Selected, approved observations</h4>
              {view.data.moments.length ? <ol>{view.data.moments.map((m,i)=><li key={i}>
                <strong>{m.title}</strong><p>{m.description}</p>
                <time>{new Date(m.observedAt).toLocaleString("en-GB",{dateStyle:"medium",timeStyle:"short"})}</time>
              </li>)}</ol> : <p>No approved events were included in this briefing.</p>}</div>
            <p className="mi-investor-source-footer">Source observed {new Date(view.data.observedAt).toLocaleString("en-GB",{dateStyle:"medium",timeStyle:"short"})}. Revision {view.data.sourceRevision.slice(0,12)}. This view shows selected facts only, not unrestricted system access.</p>
          </>}
        </section>
        <section className="mi-investor-room-boundary"><div><span className="mi-eyebrow">WHAT THIS ACCESS MEANS</span>
          <h2>Open about progress.<br/><em>Careful with trust.</em></h2>
          <p>This room is a deliberately limited window into our research, not an operational console. It doesn&apos;t allow you to speak to live agents, change work, see confidential data or approve decisions.</p>
        </div><form action="/investors/leave" method="post"><button type="submit" className="mi-button mi-button-dark">Leave investor room <span aria-hidden="true">→</span></button></form></section>
      </>}
    </div>
  </div>;
}
