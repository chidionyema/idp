# Onboarding: idp-freeze

Nothing to install. It needs the GitHub command line signed in, which every session already has.

## What it is for

The founder sometimes stops the world. When he does, he writes it on the board in his own words
and names what has to stop. Before this existed, that page was the whole of the enforcement: a
human had to remember it. Eight days of measurement showed that nobody did.

This turns the page into a measurement. It reads every issue on the board carrying the `freeze`
label that is still open, works out which workflows the issue names, and asks GitHub what state
each of those is in right now. If the lock is open and something it named can still run, it
refuses.

## Running it

```
bin/idp-freeze                    measure the live estate and grade it
bin/idp-freeze SNAPSHOT.json      grade a recorded snapshot instead
bin/idp-freeze --snapshot PATH    measure, save the snapshot there, and grade it
```

It exits zero when the lock is honoured or no lock is open, and non-zero otherwise. It reads only,
and it never switches anything on or off.

## Writing a freeze it can read

Give the issue the `freeze` label and name the workflows either in the first column of a table or
as full filenames ending in `.yml`. Both are how the founder already writes them. Do not rely on
naming them in a sentence: a sentence is also how a page says what is still *allowed* to run, and
the two cannot be told apart. A freeze this check cannot read is refused rather than passed, so a
lock never goes quiet on a formatting mistake.

## Lifting a freeze

The founder closes the issue, in his own words, on his own page. Then the workflows are switched
back on by hand and this check goes quiet on its own. No session lifts a freeze, and this file
gives nobody the power to.
