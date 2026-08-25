# Count the providers that one person can lock the estate out of

Demo: `bin/owner-account-gate`

Every line is one provider whose login has no second owner, or whose recovery route is the same
identity as its login. The last line is the count; the policy target is 0
(docs/reference/security-policy.md, crew#227 CP7). The inventory it reads is
`docs/reference/owner-accounts.yaml`: identities are labels (`founder-gmail`), never addresses.
Adding a second owner at a provider is a change to that file in the same pull request as the
provider's own audit log entry.
