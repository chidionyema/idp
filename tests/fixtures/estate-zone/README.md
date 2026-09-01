Fixtures for `bin/estate-zone-gate`, proved both ways by `bin/idp-ci` (crew#269, crew#796).
`good/` and `bad/` are whole trees; `added-literal.diff` must be refused and `added-substituted.diff`
must pass when the gate grades a pull-request diff (the zone comes from `bad/clusters`).
