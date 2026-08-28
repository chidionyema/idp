# 0009. Every requirement is scored on the founder's reference matrix; the founder is asked once, for the weights

- Status: PROPOSED 2026-08-28 (the weights are STAGED for the founder's veto on crew#562; the protocol is built).
- Date: 2026-08-28
- Deciders: founder (weights), sessions (scores)
- Affects: every build-or-buy, tool, vendor and design choice on the estate, in every repository.

## The incident, 2026-08-28 21:xxZ

Screen access from the founder's phone went to him three times in one evening. A session proposed
swapping Sunshine for Guacamole; he asked "but does it have the sunshine features"; the session
reversed; he asked "and what about apple tie in"; the session answered again. His ruling, verbatim
(crew#562 5458023873 and the same thread):

> "we need a matrix for decision making"
> "rather than asking these questions it should be auto"
> "for all requirements"
> "just reference matrix, because we solve once and forever"
> "all the nuances we need to consider" / "why machine scored" / "founder has to have input"
> "because im asking the critical question no one else is thinking about"

The class of mistake: a session chose between mature tools on the criteria it happened to think of,
and the founder had to supply, by hand, the criteria it had not. Each of his questions was a
criterion the estate should already have held.

## The decision

**There is one reference matrix, `docs/decisions/decision-matrix.yaml`. The founder owns its
weights; a session scores candidates against them, in the open, and builds the top score.**

1. **The weights are the founder's input.** He sets them once, in the file, and changes them by one
   message on the crew issue. A session never edits a weight without his word. The first weights
   are his questions from this incident made permanent: first-time user, feature parity,
   ecosystem fit, alongside the laws already in force (maturity, security by default, portability,
   founder experience, operability, cost).
2. **Scores are arithmetic, not judgement.** Each candidate is scored 0–5 per criterion (0 fails the
   bar, 3 meets it, 5 best in class), multiplied by the weight, summed. The decision recorded in
   the file must be the top score; `tests/test_incident_crew562_decision_matrix.py` refuses
   anything else. "Machine scored" means nobody eyeballs a winner — it does not mean the founder
   is out of the loop: the weights are his, every number is visible, and the result is posted
   `STAGED:` with the 60-minute veto window (LAW 49).
3. **A founder question that no criterion answers becomes a criterion, in the same change.** This
   is the "solve once and forever" clause. If the founder has to ask it, the matrix was missing it;
   the fix is a new weighted row, never a one-off answer.
4. **He is asked only on a tie.** When the top two are within `tie_band` on an irreversible choice,
   the session posts the two rows and asks. Otherwise it builds the top score and reports it.
5. **One matrix, not one per decision.** A new requirement is a new entry under `decisions:` in
   the same file, citing the same weights. No new framework, no new template.

## What this replaces

- The habit of asking the founder to choose between options he never asked to compare (headline
  rule 2: "You may not hand the founder a menu").
- Per-session criteria. LAW 43's research still happens; its output is now scores in the file.

## Consequences

- A PR that introduces or replaces a tool, vendor or user-facing flow cites the decision slug in
  its body; the operating-model gate can grow a `Matrix:` rule once the weights are confirmed.
- The first worked decision is `founder-screen-access`: Sunshine + Moonlight 385, Apple Screen
  Sharing 345, Guacamole 340 out of 500. The tool a session had proposed came last once the
  founder's own questions carried weight.
