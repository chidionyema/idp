"use client";

import { useState } from "react";

const scenes = [
  {
    label: "Start the week",
    time: "MONDAY / 09:00",
    heading: "Everyone knows what matters.",
    story: "A team begins the week with a shared picture of the priorities, the owners and the decisions waiting to be made.",
    human: "People focus on the important work instead of rebuilding the plan from messages.",
    example: "The product launch is this week's priority. Design and engineering know their next steps. One decision needs the director.",
  },
  {
    label: "Keep things moving",
    time: "WEDNESDAY / 14:00",
    heading: "The work doesn't get lost between teams.",
    story: "When a handover is due, the right person can see what needs attention and what is holding the next step back.",
    human: "Less chasing. Fewer meetings just to ask for an update.",
    example: "The design review is complete. The launch checklist moves to engineering. A slipping deadline is visible before it becomes a surprise.",
  },
  {
    label: "End with clarity",
    time: "FRIDAY / 16:00",
    heading: "Progress is clear. People stay accountable.",
    story: "The week closes with a simple account of what moved forward, what still needs a decision and what comes next.",
    human: "Leaders can make informed decisions without making everyone write another status report.",
    example: "Three commitments are complete. One decision remains open with a named owner. Monday's first priority is clear.",
  },
] as const;

export function ChronosWalkthrough() {
  const [active, setActive] = useState(0);
  const scene = scenes[active];
  return (
    <section className="mi-chronos-walkthrough" aria-labelledby="chronos-walkthrough-title">
      <div className="mi-chronos-walkthrough-heading">
        <div><span className="mi-eyebrow">CHRONOS / ILLUSTRATIVE EXPERIENCE</span>
          <h2 id="chronos-walkthrough-title">A calmer working week.</h2>
          <p>Explore the experience we want to build. These are fictional examples of the product direction, not a live demonstration or customer results.</p>
        </div>
        <span className="mi-chronos-concept-badge">CONCEPT WALKTHROUGH</span>
      </div>
      <div className="mi-chronos-steps" role="group" aria-label="Choose a stage of the working week">
        {scenes.map((item, index) => (
          <button type="button" key={item.label} onClick={() => setActive(index)}
            aria-pressed={active === index}
            className={"mi-chronos-step" + (active === index ? " mi-chronos-step-active" : "")}>
            <span>0{index+1}</span>{item.label}
          </button>
        ))}
      </div>
      <div className="mi-chronos-scene" aria-live="polite" aria-atomic="true">
        <div className="mi-chronos-scene-story">
          <span className="mi-eyebrow">{scene.time}</span>
          <h3>{scene.heading}</h3>
          <p>{scene.story}</p>
          <strong>What changes for people</strong>
          <p>{scene.human}</p>
        </div>
        <div className="mi-chronos-scene-example">
          <span>AN EXAMPLE, NOT LIVE COMPANY DATA</span>
          <p>{scene.example}</p>
          <small>The goal is a clearer rhythm of work, with people making the important decisions.</small>
        </div>
      </div>
    </section>
  );
}
