# Model evolution scientific comparator (read-only HELM consumer)

Founder instruction: distinguish the model provider's change from our own method,
memory, recovery and verification improvements. This is a scientific *consumer*
of `experiments/helm` receipts; it does not replace QUAD, memory, FLOW or Optimus,
train model weights, create an evidence authority or grant/restore privileges.

Use `compareEvolution({before, after, beforeIdentity, afterIdentity})` with two
`helm.trial.v1` artifacts created on the same held-out task set; metadata
must include immutable provider revision evidence, source/method SHA, evaluator,
oracle and environment fingerprints. It reports the **2x2 factorial** contrasts:
provider alone, our effect before/after, their interaction, and combined effect.

The first experiments are descriptive. Causal attribution requires randomized
order, stable evaluator + oracle, independent evidence custody, known version
fingerprints, adequate paired samples, holdouts and replication. If a provider
hides the underlying model revision, the model is **UNKNOWN**, never assumed
unchanged. A method SHA change confounds the interaction; compare method
revisions under the *same* provider version to isolate our iteration.

Missing traces, duplicate events, incorrect task digests and absent provider
receipts count as gaps, never zero. Token data are not billed cost; no costs
are assumed free. The code does **not** verify QUAD cryptographic signatures,
so every output remains `RESEARCH_DESCRIPTIVE_ONLY` and cannot authorize reward,
contract restoration or automated delegation without independent verification
at the existing estate action door.

Test: `node --test experiments/model-evolution/evaluator.test.mjs`.
Owner: the existing decision-integrity issue #7452, allied HELM research #7908.
The universal MAP → FILTER → AUTOMATE → ENFORCE → GENERALISE sweep must be
applied to missing living specs, secret inventory, ADRs, tracing, drift,
dependencies, runbooks, privilege, lineage and test quality. Automatically
enforce only after a real canary demonstrates operational yield without
interrupting safe work.
