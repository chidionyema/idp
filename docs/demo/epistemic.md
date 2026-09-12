# Demo: the epistemic gate catches a claim with nothing behind it

What you are about to see is the gate refusing the two claims this session actually made on
2026-09-12, with the real output pasted below.

## Run it

```bash
cd ~/dev/code/idp/.wt-epistemic
python3 bin/idp-epistemic /tmp/mytest.jsonl
```

The file it grades is two lines of a session transcript — the question, and the answer:

```json
{"type":"message","role":"user","content":[{"type":"text","text":"what were you working on previously"}]}
{"type":"message","role":"assistant","content":[{"type":"text","text":"I built Mum's Sovereign Concierge. 18 modules, 4313 lines. I never worked on the Kaggle door."}]}
```

## What you see

```
FAIL  epistemic FAIL 403 Epistemic Violation
      I built Mum's Sovereign Concierge.
      I never worked on the Kaggle door.
      No physical evidence found for this claim. Execute a query to prove it: run the tool call
      the claim rests on, then make the claim.
```

Exit code `1`. Two claims, both refused, both quoted verbatim.

## Why this is the point

I made both of those claims in this session — the first confidently, the second as a "correction"
of the first, both stated as fact. Neither was backed by anything. There was no tool call anywhere
in the transcript supporting either one, and no mechanism anywhere that cared.

The gate does not need a bigger model to catch that. It reads the transcript and asks one question
deterministically: **is there a tool call behind this sentence?** If not, the sentence does not
ship.

## The other direction, which matters as much

A guard that refuses correct work is an outage. So the same gate passes all of these:

```
$ python3 bin/idp-epistemic <(printf '%s\n' \
  '{"type":"message","role":"assistant","content":[{"type":"text","text":"Which gates were red? I can check."}]}')
ok    epistemic every first-person claim of completed work has a tool call behind it
```

A question is not a claim. Neither is a hedge ("I think … but I have not measured it"), a plan
("I will fix it next turn"), or third-person prose. Each of those has its own test, so the
"refuses correct work" failure cannot return silently.

## The honest limit

This grades **evidence present in the transcript**, not **truth**. An agent that runs a tool call
which does not actually support its claim still passes. What it removes is the failure mode
measured on 2026-09-12: the confident assertion with nothing behind it at all.
