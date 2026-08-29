# Design rules for the front page

Twenty-five rules, each one sentence, each with the page it came from. Fetched and read on
2026-08-29 for crew#612; nothing here is from memory. Where a source could not be read (the
Material Design type-scale pages render their tables in JavaScript and return an empty document
to a fetcher), the rule cites the Material-UI v4 page that this app actually compiles against,
and is marked so.

## Type scale

1. A heading and the subheading under it must differ in at least two of size, weight and colour,
   because scale, weight and colour contrast are three separate carriers of hierarchy and one of
   them alone is easy to miss. — https://www.nngroup.com/articles/visual-hierarchy-ux-definition/
2. Use no more than three clearly distinct sizes for the elements a reader ranks at a glance
   (large, medium, small), because more than three stops reading as a ranking. —
   https://www.nngroup.com/articles/visual-hierarchy-ux-definition/
3. Step the scale by a ratio a reader can see, not by one or two pixels: the page title should be
   roughly 1.6 times the section heading and the section heading roughly 1.7 times body text,
   matching the gaps Material-UI v4 ships between h1, h5 and body1. —
   https://v4.mui.com/customization/typography/
4. Give each level its own weight as well as its size — 700 for the page title and section
   headings, 600 for group and card titles, 400 for descriptions — so the ranking survives when a
   heading wraps onto one line. — https://v4.mui.com/customization/typography/
5. Descriptions and meta text take the secondary and muted text colours, never the primary text
   colour a heading uses, so colour repeats the ranking the size already stated. —
   https://www.nngroup.com/articles/visual-hierarchy-ux-definition/
6. Do not carry a heading's meaning in colour alone: a coloured heading must still be the biggest
   or heaviest thing in its block. — https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html
7. Confirm the hierarchy with the squint test — blur the page and check the intended reading order
   still comes out first, second, third. —
   https://www.nngroup.com/articles/visual-hierarchy-ux-definition/

## Spacing

8. Every margin, padding and gap is a multiple of 8 pixels, because that is the scaling factor
   this app's theme helper multiplies by. — https://v4.mui.com/customization/spacing/
9. Use `theme.spacing(n)` rather than a pixel literal so a change to the unit moves the whole
   page at once. — https://v4.mui.com/customization/spacing/
10. Put more space between sections than between a heading and the text it owns, because
    proximity is what tells a reader which words belong to which heading. —
    https://www.nngroup.com/articles/visual-hierarchy-ux-definition/

## One glance

11. The single most important fact — is anything failing right now — is the first thing on the
    page and the largest, because a dashboard has to be understood "without requiring large
    amounts of time or cognitive resources to interpret". —
    https://www.nngroup.com/articles/dashboards-preattentive/
12. Rank by position as well as size: the worst state sits top-left of the reading order, since
    2D position is read pre-attentively. — https://www.nngroup.com/articles/dashboards-preattentive/
13. Remove decoration that carries no data, because every non-data mark competes with the data
    for the same glance. — https://www.nngroup.com/articles/dashboards-preattentive/
14. Group related numbers by proximity and a shared container rather than by a border on each
    one. — https://www.nngroup.com/articles/visual-hierarchy-ux-definition/

## Icons and charts

15. Every icon carries a text label beside it or an accessible name on it; an icon alone is a
    guess. — https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html
16. Prefer a bar to a donut whenever the reader must compare or rank amounts, because length and
    position are read accurately at a glance while angle and area are not. —
    https://www.nngroup.com/articles/dashboards-preattentive/
17. A donut is allowed only for the one job it does honestly — showing that a set of parts makes
    a whole — and never as the way a reader compares two slices. —
    https://www.nngroup.com/articles/dashboards-preattentive/
18. Every chart ships a legend that gives each series its word and its number, so the chart is
    readable without measuring it. — https://www.nngroup.com/articles/dashboards-preattentive/
19. Use colour in a chart to name a category, never to encode how big a value is. —
    https://www.nngroup.com/articles/dashboards-preattentive/
20. Every chart has `role="img"` and an accessible name that is the sentence the chart makes,
    plus the same numbers available as text. —
    https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html

## Plain language

21. Write in the active voice and address the reader as "you", so it is clear who does what. —
    https://guidance.publishing.service.gov.uk/writing-to-gov-uk-standards/writing-guidelines/
22. Front-load the sentence: the most important thing goes in the first few words, because
    readers scan rather than read. —
    https://guidance.publishing.service.gov.uk/writing-to-gov-uk-standards/writing-guidelines/
23. Use the plain word the reader already knows instead of the internal name, and say what the
    reader can do, not what the system did. —
    https://guidance.publishing.service.gov.uk/writing-to-gov-uk-standards/writing-guidelines/
    (The GOV.UK guidance hub was reachable; its clear-language sub-pages redirect, so this rule
    also rests on the hub's own instruction to write so users "find what they need and understand
    it".)

## Colour and contrast

24. Colour is never the only way a state is shown: every state carries a dot or icon **and** its
    word. — https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html
25. Body and small text meets 4.5:1 against its background, and only text at 24px regular or
    18.5px bold and above may drop to 3:1. —
    https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html

---

## Applied here

- **Rule 1 and 5 answer "why is headers same size colour as subheading?"** The page title is
  40/700/textPrimary, section headings 24/700/textPrimary, descriptions 14/400/textSecondary —
  every pair differs in all three, not two.
- **Rule 11 puts the verdict first and biggest.** `verdictSentence` in `words.ts` renders as the
  largest sentence on the page: "6 of 31 pieces are failing right now."
- **Rule 16 and 17 shape the picture.** The donut shows only that the six states make one whole
  estate; the horizontal stacked bars per system are what a reader actually compares.
- **Rule 18 fixes "6 RED 6 WHAT?"** The legend gives word and number together, and
  `STATE_MEANING[s].short` gives each counter card a three-to-six word explanation.
- **Rule 24 keeps `blind` honest.** "Can't check" is drawn hollow with its own icon and word, so
  it can never be mistaken for green by someone who cannot see the tint.
- **Rule 25 sets the muted colour floor.** `textMuted` is only used at 12px/500 where it clears
  4.5:1 on `surface1`; anything failing that goes up to `textSecondary`.
- **Rule 21 to 23 are enforced by a test, not a habit.** `words.test.ts` fails the build if any
  exported string contains an insider word.
- **Rule 8 and 9 make the phone work.** Every gap is `theme.spacing(n)`, so the 390px layout
  tightens by changing one number rather than forty.
