# Onboarding: the Demo Standard (crew#805)

**What it is for.** Every feature ships a demo a person can watch, and the machines record it —
a script in git (`demos/*.tape` for CLI, a Playwright demo spec for UI) replayed by CI on every
relevant push, so a demo can never show what the software no longer does.

**What it costs.** Nothing recurring: VHS (MIT) and Playwright are free; rendering runs on CI,
never on the founder's Mac.

**Where it lives.** Scripts in `demos/`; rendered files in `docs/demos/`; the workflow is
`.github/workflows/demo-render.yml`; the design is `docs/decisions/2026-09-01-demo-standard.md`.

**How to use it.** Add a `.tape` next to your feature; push; CI renders and commits the GIF;
embed it in your `docs/demo/<name>.md` page.

**How to stop it.** Delete the tape and the workflow; nothing else references them.
