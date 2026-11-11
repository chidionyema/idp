import Link from "next/link";
import type { Metadata } from "next";
import { site } from "@/content/site";
import { ResearchQA } from "@/components/ResearchQA";
export const metadata: Metadata = { title:"The laboratory",description:"The Meridian Intelligence applied AI laboratory: research programmes, evaluation, agent systems and experimental intelligence." };
export default function ResearchPage() {
 return <div className="mi-interior">
  <section className="mi-page-hero"><div className="mi-shell"><span className="mi-eyebrow">MERIDIAN / THE LABORATORY</span><h1>STAY<br/><em>UNREASONABLY</em><br/>CURIOUS.</h1><div className="mi-page-hero-bottom"><p>We test the emerging edge of artificial intelligence. Every hypothesis needs a baseline, every result needs evidence, and every failure gives us information for the next experiment.</p><Link href="/consulting" className="mi-button mi-button-gold">Partner with the lab <span aria-hidden="true">↗</span></Link></div></div></section>
  <section className="mi-section mi-service-detail-section"><div className="mi-shell"><div className="mi-section-intro"><span className="mi-eyebrow">ACTIVE RESEARCH THEMES</span><p>QUESTIONS BEFORE CLAIMS</p></div><div className="mi-service-detail-list">{site.research.map((r,i)=><article className="mi-service-detail" key={r.title}><span>0{i+1}</span><div><h2>{r.title}</h2><p>{r.blurb}</p><div className="mi-chip-list"><span>{r.kind}</span><span>EXPERIMENTAL</span></div></div><Link href={r.href||"/contact"} aria-label={"Learn about "+r.title}>↗</Link></article>)}</div></div></section>
  <section className="mi-proof-band"><div className="mi-shell"><span className="mi-eyebrow">OUR SCIENTIFIC METHOD</span><div className="mi-proof-grid"><div><h3>Hypothesise.</h3><p>Make the question and baseline explicit before the first experiment.</p></div><div><h3>Experiment.</h3><p>Capture parameters, controls, measurements and negative findings.</p></div><div><h3>Translate.</h3><p>Turn supported findings into prototypes, customer work or the next research question.</p></div></div></div></section>
  <section className="mi-section mi-research-section"><div className="mi-shell mi-research-qa"><span className="mi-eyebrow">RESEARCH NOTES / QUESTIONS</span><h2>ASK BETTER QUESTIONS.</h2><p>Explore the laboratory&apos;s themes and their supporting research. An answer is a starting point for verification, not a substitute for evidence.</p><ResearchQA /></div></section>
 </div>;
}
