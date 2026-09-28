# Customer messaging bindings, as requested

Each file here is one customer's channel binding for the messaging ingress, put here by
the portal template `backstage/templates/customer-onboarding` and reviewed as an
ordinary pull request. It holds a reference to where the customer's credential lives,
never the credential.

A file landing here does not make the binding live. Writing the row into hermes-v2's
ingress database (`channel_binding`, otto/ingress/store.py) is a separate reviewed
action with that database's credentials, which the scaffolder does not have. The
template says so on every pull request it opens rather than reporting a connection it
has not made (crew#819).

`status:` is `requested` when the template writes the file and is moved to `active` by
whoever applies the row, so this directory answers which customers are waiting.
