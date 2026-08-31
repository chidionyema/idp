# Demo: A page a person reads refuses dev speak

The founder's rule, 2026-08-31: every page a person meets is in plain English. Engineering words,
ticket codes and layer labels stay on the engineering side of the line.

## What you see

1. Open a pull request that adds the sentence `The prover checks crew#631 at L1` to any page under
   `docs/`, to the README, to a founder button or to the drill catalogue.
2. The `prose` check on the pull request goes red and leaves a review comment on that exact line,
   saying which word to use instead.
3. Change the line to `The checker confirms the dashboard answers and refuses a caller without a
   key` and push. The check goes green.

## Try it locally

```sh
vale sync                      # once; downloads the Microsoft style
vale --minAlertLevel=error README.md
python3 -m pytest -q tests/test_incident_crew612_cp8_dev_speak_never_crosses_the_boundary.py
```

The first command grades the README whole. The test grades the fields a person reads in the
Backstage catalogue, the founder buttons and the drill catalogue, with the same configuration.

## What is left

The run summary of every `prose` check prints how many dev-speak errors remain on the docs tree.
That number only goes down: a pull request cannot add to it, because every line it touches must
be clean.
