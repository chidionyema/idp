# Count the static secrets the estate still holds

Demo: `bin/static-secret-gate`

Every line is one credential that a person could copy, and the identity that replaces it.
The last line is the count. The policy target is 0 (docs/reference/security-policy.md,
crew#227). Run it on any host; it reads only under HOME and the vault.
