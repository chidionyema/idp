# Voice

The house voice is a person who has done this work, talking to another engineer. Not a company
addressing a market.

This file is not aspirational. `scripts/voice-lint.mjs` measures every rule below against the copy
in this repo and fails the build when one breaks. If a rule cannot be measured it is not in here.

## The one test

Read a sentence out loud. If you would not say it to a colleague across a table, cut it.

## Rules that are checked

**1. No AI tells.** A fixed list of words and constructions that only appear in machine-written
marketing copy. `delve`, `leverage`, `robust`, `seamless`, `cutting-edge`, `ever-evolving`,
`landscape`, `tapestry`, `testament to`, `unlock`, `empower`, `elevate`, `unparalleled`,
`game-changer`, `supercharge`, `harness the power`, `dive into`, `best-in-class`, `world-class`,
`next-generation`, `state-of-the-art`, `holistic`, `synergy`, `streamline`, `revolutionize`,
`in today's`, `gone are the days`, `whether you're`, `more than just`, `it's not just`,
`at the end of the day`, `the future of`.

The list is the check. Adding a word here makes it fail everywhere at once.

**2. Em dashes: at most 1.0 per 100 words.** The single most reliable 2025 tell. A human writer
reaches for an em dash once a page. A model reaches for one every other sentence, because it is the
cheapest way to make a flat clause feel like it has a second half. Use a full stop instead.

**3. Short sentences: at least 15% of sentences under 10 words.** Model prose holds a metronome
between 15 and 25 words. People do not. We write a long qualified sentence, then a three-word
one. That variance is the signal, and it is invisible to a reader but obvious to a measure.

**4. Sentence-length deviation: at least 5.0 words.** The standard deviation of sentence length
across the site. Below that and the rhythm is a machine's.

**5. Adverbs: at most 4 `-ly` words per 100 words.** `significantly`, `seamlessly`, `dramatically`
are how a model adds emphasis without adding information. The verb should already carry it.

**6. Hedges: at most 2 per 100 words.** `very`, `quite`, `really`, `simply`, `actually`, `just`,
`arguably`, `somewhat`. They weaken a claim. Make the claim or drop it.

**7. List constructions: at most 1.2 per 100 words.** Two or three nouns joined as `X, Y and Z`.
One of these in a paragraph is fine. The tell is that every single sentence resolves into one,
because a list is the easiest way to look comprehensive without saying anything specific.

**8. `not just` / `not only`: zero.** The construction exists to imply depth it has not earned.
"Works in production, not just in demos" is a claim about a demo. Say what it does under load.

**9. Word tics: no word above 8 per 1000 words.** Counted over all prose, with English function
words and the site's own subject nouns excluded. A tic is a word the copy reaches for when it has
nothing to add. On this site the two that showed up were `actually` and `production`.

## The gate bites

`node scripts/voice-lint.mjs --self-test` scores a known-bad sample through the same rules and
exits non-zero. It exists so the linter cannot quietly pass everything: change a threshold or break
an extractor and the self-test fails first. A gate that cannot fail is not a gate.

## Rules that are not checked, and why

- **Numbers are real or absent.** Every figure on this site came from an engagement. A number you
  cannot source is deleted, not softened. No linter can prove this; a reviewer has to.
- **No sentence starts with "We" twice in a row.** Rhythm. Read it aloud.
- **Say what broke.** The most credible sentence in a case study is the one about the thing that
  did not work. A case study with no failure in it reads as fabricated, because it is. The lint
  cannot see it; `content/case-studies.ts` carries a required `friction` field and the page renders
  it, so the structure forces the question even though no rule scores the answer.

## Register

- Second person for the reader's situation, first person plural for our work. "Your eval suite",
  "we shipped".
- Contractions everywhere except where the emphasis needs the full form.
- Specific nouns over category nouns. `LiteLLM` not `the routing layer`. `$297K` not `significant
  savings`.
- British spelling is not the house style; pick one and stay on it. It is US spelling.
- Never explain what a term means to someone who already knows it. Never assume the reader does
  not.
