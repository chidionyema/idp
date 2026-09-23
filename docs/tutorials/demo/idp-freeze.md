# Demo: the freeze the estate forgot

On 31 August the founder opened a page on the board and wrote, five times in one minute, that
nothing was to be released. The page named eight workflows and said they stayed switched off until
he said otherwise in his own words on that same page.

On 8 September the page was still open. Nobody had written a single comment on it. Five of the
eight workflows had been switched back on, one of them had run forty minutes earlier, and the main
branch had taken one thousand two hundred and ten new commits since the page was written, seven
hundred and nine of them robot image updates — which is the exact thing the fifth row of his own
table barred. Searching the whole repository for any mention of that page turned up nothing: no
check read it, so no check could notice.

This is what that looks like now.

```
$ bin/idp-freeze
FAIL  freeze   chidionyema/crew#739 is open and locks 8 workflow(s), but 5 of them can still
               run: build-multiarch (active), catalog-render (active), image-update-pr (active),
               oke-check (active), vault-seed (active)
               FREEZE: nothing is released (founder, 2026-08-31)
               Either the freeze stands and these go back off, or the founder closes the issue.
               A lock nothing enforces is not a lock.
```

On a day with no lock written, it is quiet and it passes:

```
$ bin/idp-freeze tests/fixtures/freeze/none-open.json
ok    freeze   no freeze is open on the board; nothing is locked
```

The first time this ran against the real board it was wrong, and being wrong against a real input
is the whole point of running it there. The founder's page ends with a sentence listing what was
still allowed to run — the ordinary checks, the drills, the probes. The check read that sentence
as part of the lock and reported two innocent workflows as frozen. It now reads the lock from the
rows of his table and from filenames written out in full, and never from a sentence.
