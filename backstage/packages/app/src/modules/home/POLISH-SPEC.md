# Front page polish (crew#612 / crew#459), founder 2026-08-29 16:5xZ, verbatim

- "why is headers same size colour as subheading? how do u know which is which"
- "I DONT SEE ICONS NOT CHART, NOTHING VISUAL"
- "IT NEEDS TO CAPTURE ATTENTION FIRST, NO CLUSTER INFO, NO CLUSTER HEALTH, ITS A BLACK BOX"
- "6 RED 6 WHAT?"  "ITS TOO CRYPTIC"
- "DON'T ASSUME THE USER KNOWS WHAT YOU KNOW"
- "polish it to perfection, nothing less will do"

## What the page must become (one reading order, top to bottom)

1. **Hero that captures attention.** Big headline (h1, 40px+, primary colour), one plain sentence
   under it that says what this page is: "This is the Bytesync estate: every piece of software we
   run and every door we sign in through, read live from the cluster." Then the live verdict as a
   sentence a stranger understands, e.g. "6 of 31 pieces are failing right now." Never a bare
   number next to a bare word.
2. **The picture.** A donut of all pieces by state (colour + label + number, legend with words),
   and a horizontal stacked bar per system. Pure SVG, no chart library, theme tints from
   `../theme/tokens` (`stateLight`/`stateDark`). Accessible: `role="img"` + `aria-label`
   sentence, and a visually hidden table of the numbers.
3. **Counters** become cards with an icon per state and a sentence: number, word, then a
   13px explanation ("The cluster says these are failing. Click to list them."). The six
   states and the one-line meaning of each:
   - red: "Failing. The cluster reports an error on this piece."
   - needs: "Needs you. A person has to act before it works."
   - stale: "Stale. Nobody has checked it recently, so its word may be old."
   - blind: "Can't check. Nothing is able to read this piece's state."
   - running: "Starting or changing. The cluster is still working on it."
   - good: "Working. The cluster reports it healthy."
4. **Typographic hierarchy that nobody can mistake.** Scale, in px / weight / colour:
   - page title (h1) 40 / 700 / textPrimary, letter-spacing -0.02em
   - section heading (h2) 24 / 700 / textPrimary, with an icon at its left
   - group heading (h3) 17 / 600 / textPrimary
   - card title 15 / 600 / textPrimary
   - description / subheading 14 / 400 / textSecondary
   - meta / small 12 / 500 / textMuted
   A subheading is never the same size, weight AND colour as the heading above it: at least two
   of the three differ, always.
5. **Icons everywhere a stranger needs a hint**: one per state (counters, pills), one per
   section (What we run, Doors, Do), one per system (from `@material-ui/icons`, chosen by
   system name keywords with a fallback), one per door (the padlock/open-door idea).
6. **Every heading says what the section is in one sentence directly under it**, in the
   description style: "What we run: every piece of software the cluster runs, grouped by what
   it is for." "Doors: the places you sign in to." "Do: actions the platform can run for you."
7. **The read-at line** stops being 12px muted at the top; it becomes a small status chip next
   to the verdict: "Live, read 16:52" (good tint) or "Not live: <why>" (red tint) with an icon.

## Constraints
- `@material-ui/core` v4 and `@material-ui/icons` v4 only; no new dependency.
- Keep every existing `data-testid` (login drill contract) and every existing test green.
- No colour alone carries meaning (dot/icon + word always).
- Phone first: donut and bars stack on `phone` breakpoint.
- Files: visuals go in `visuals.tsx` (+ `visuals.test.tsx`); words in `words.ts`; type scale in
  `../theme/index.tsx`; `EstateHome.tsx` is integrated by the lead after both land.
