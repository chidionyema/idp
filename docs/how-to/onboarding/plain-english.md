# How to keep a page in plain English

Every page a person reads is graded by Vale, the prose linter that GitLab, Microsoft and Red Hat
run on their own documentation. The boundary is in `.vale.ini` and `styles/Estate/`.

## The three things the boundary refuses

| Class | Example | Say instead |
|---|---|---|
| A ticket code, a checkpoint, a hash or a run id | `crew#631`, `CP9`, `LAW 50`, `7e913abd` | Say what it is in words; put the code in a link |
| A layer label from the engineering plan | `L1`, `L2`, `BLIND` | Say what is checked: it answers; it answers the key; it refuses without the key; a signed-in person reaches it |
| Dev speak | `prover`, `nonce`, `OIDC`, `HelmRelease`, `namespace`, `PR` | `the checker`, `request code`, `single sign-on`, `the chart release`, `the area of the cluster`, `pull request` |

The full word list is `styles/Estate/DevSpeak.yml`. To add a word, add a row there; the change is
graded like any other.

## Where the line runs

- `docs/` and the README: graded by the `prose` check on every pull request. Every line you touch
  must be clean; the README must be clean whole.
- Founder buttons: generated from the first two lines of each workflow under `.github/workflows/`,
  which must read `# button: <title>` and `# founder: <one plain sentence>`. The generator refuses
  a workflow without them, so the words are written once, at the source.
- The Backstage founder catalogue and the drill catalogue: the fields a person reads are extracted
  and graded by `tests/test_incident_crew612_cp8_dev_speak_never_crosses_the_boundary.py`.

## Adding a new page or field

A new page under `docs/` is graded on arrival. A new field a person reads in a YAML file is added
to the extractor in that test, or it is not graded; the test file is the list of what counts as a
page a person reads.

## Product names

`styles/config/vocabularies/Estate/accept.txt` holds the product names (Backstage, Flux, SigNoz,
Langfuse and the rest). A product name is never dev speak.
