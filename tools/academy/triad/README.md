# TRIAD / Meridian Academy — adaptive transfer laboratory v1

**Research-only prototype.** Actual Node tests, Chrome screenshots and offline learner-interface execution are independently checked in CI; human learning improvement and commercial operational yield remain **UNKNOWN**. Not a blinded evaluation or deployed public service.

## The experience

The canonical concept is **conditional reconstruction**: trusted checkpoint + versioned rules + complete ordered history + necessary external inputs + appropriate authority + independently checked effects. Lessons retain explicit limits of biological and orchestral metaphors.

Three teaching variants: precise explanation, precise+one analogy, TRIAD (precise+two analogies). Each learner sees two baseline diagnostic questions, the selected explanation, three distinct transfer questions, and—if an error occurs—a misconception-specific corrective analogy followed by a new retest. Confidence calibration is descriptive only. Learner free-text reflections are deliberately **not machine-graded**.

Keyboard-accessible semantic controls, responsive layout and a no-tracking progress indicator. There is no login, cookies, remote telemetry, server submission or persistence. An explicitly requested local export contains anonymous descriptive results only.

## Launch

**One-file offline studio:** download the GitHub Actions artifact named triad-research-prototype, extract triad-standalone.html, and open it directly in a current browser. The research workflow checks the portable file in a real Chrome browser.

**Developer preview from repo root:**

~~~sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory tools/academy/triad
# open http://127.0.0.1:8765/studio.html
~~~

**Reproduce automated falsifiers and CLI:**

~~~sh
node tools/academy/triad/run.mjs --lesson
node tools/academy/triad/run.mjs --assessment
printf '{"t1":"A","t2":"A","t3":"A"}' | node tools/academy/triad/run.mjs --score
node --test tools/academy/triad/evaluate.test.mjs tools/academy/triad/adaptive.test.mjs
node tools/academy/triad/build-standalone.mjs triad-standalone.html
~~~

No npm install, paid provider or secret needed.

## Evidence boundary

Offline keys can be inspected with developer tools, so this is **not** a secure high-stakes assessment. There is no authenticated learner, blinded external evaluator, randomly allocated study, measured uplift or independent production effect witness. A local 100% is not proof of mastery, causal improvement or product yield.

The isolated workflow at .github/workflows/triad-research-pilot.yml checks 10 original plus 15 adaptive tests, refuses malformed/forged cases, executes the modular and offline learner UIs in real headless Chrome, tests intentionally wrong CLI answers, and exports screenshot and private prototype artifact. These are real **engineering** tests only.

## Goal and subgoals

**Goal:** the learner solves an unseen causal-reconstruction case without relying on the teaching metaphor.

G0: Independently review target relations, assumptions and analogy limits (SOURCE PRESENT, EXPERT VALIDATION OPEN).
G1: Let a real learner complete novel transfer and articulate why (OPEN; interactive interface exists).
G2: Independently evaluate reflection and error classes under a pre-registered blind rubric (OPEN).
G3: Run matched canonical/one-analogy/two-analogy randomised comparison with timing, cost, fairness, retention, held-out items and confidence intervals (OPEN).
G4: Signed Greenlane admission and measured Academy/Genesis readback (OPEN; not authorised simply by CI).

Reuse HELM #7908, FLOW, KARMA, Optimus and Genesis. Never create a second learning-governance database, award self-grades as verified yield, or present this as commercial efficacy.

Full mathematical science: docs/training/2026-11-16-triad-mathematical-analogical-transfer.md.
