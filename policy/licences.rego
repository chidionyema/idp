# What we are allowed to sell, as policy rather than as somebody's memory.
#
# LAW 40 test 3: "Do you know what you are allowed to sell?" A licence is
# discovered cheaply and swapped expensively, so the answer has to be a command
# that runs on every dependency, not a spot check on the ones we thought about.
#
# Input is reports/licences.json, reshaped from the syft SBOM by bin/supply-chain:
#
#   {"packages": [{"name": "...", "version": "...", "licences": ["MIT", ...]}]}
#
# Note the wrapper. conftest splits a top-level JSON array into one document per
# element, so a bare array makes every whole-tree rule fire once per package.
# The object is what keeps `count(input.packages)` meaning what it looks like it
# means.
#
# DENY vs WARN is the whole design here. A rule that refuses correct work is an
# outage (LAW 38), and in an npm tree of a few thousand packages, missing
# licence metadata is common and usually a packaging gap rather than a genuinely
# unlicensed package. So:
#
#   deny  -- a licence is DECLARED and it blocks a sale. Unambiguous, act on it.
#   warn  -- no licence is declared. Worth knowing, never a reason to fail a build.
#
# conftest exits non-zero on deny and zero on warn, which is exactly that split.

package main

import rego.v1

# Licences that reach into what you build on them, or forbid commercial use.
# Each of these would have to be removed or replaced before the platform could
# be sold, which is why they are hard failures and not advice.
sell_blocking := {
	"AGPL-1.0", "AGPL-3.0", "AGPL-3.0-only", "AGPL-3.0-or-later",
	"SSPL-1.0",
	"BUSL-1.1",
	"Elastic-2.0", "ELASTIC-2.0",
	"CC-BY-NC-4.0", "CC-BY-NC-SA-4.0", "CC-BY-NC-ND-4.0",
	"CC-BY-NC-3.0", "CC-BY-NC-SA-3.0",
	"Commons-Clause",
}

# Copyleft that does not block a sale but does constrain how the thing is
# distributed. Reported so nobody is surprised, never fatal.
notable_copyleft := {
	"GPL-2.0", "GPL-3.0", "GPL-2.0-only", "GPL-3.0-only",
	"GPL-2.0-or-later", "GPL-3.0-or-later",
	"LGPL-2.1", "LGPL-3.0", "LGPL-2.1-only", "LGPL-3.0-only",
	"MPL-2.0",
}

normalise(s) := upper(trim_space(s))

blocking_upper contains upper(l) if some l in sell_blocking

copyleft_upper contains upper(l) if some l in notable_copyleft

# --- hard failures ------------------------------------------------------------

deny contains msg if {
	some pkg in input.packages
	some lic in pkg.licences
	normalise(lic) in blocking_upper
	msg := sprintf(
		"%v@%v is %v, which cannot be shipped in something we sell. Replace it or remove it.",
		[pkg.name, pkg.version, lic],
	)
}

deny contains msg if {
	count(input.packages) == 0
	msg := "the SBOM lists no packages -- syft produced nothing, so this proves nothing"
}

# The failure this policy is most likely to be lied to by. A run that scanned
# the wrong thing, or ran the wrong cataloger, produces a full parts list with
# no terms in it -- and every rule above then passes, so the report says
# "licences clean" when nothing was actually checked.
#
# Measured 2026-08-24: scanning backstage/node_modules without
# --select-catalogers "+javascript-package-cataloger" gave 1821 packages and 2
# licences, and this policy passed it. No real npm tree looks like that; a
# correctly scanned one here is 4996 packages and 3081 licences. So a
# non-empty SBOM where almost nothing declares a licence is a broken scan and
# is refused, rather than being reported as a clean bill of health.
deny contains msg if {
	total := count(input.packages)
	total > 0
	declared := count([p | some p in input.packages; count(p.licences) > 0])
	declared * 10 < total
	msg := sprintf(
		"only %v of %v packages carry a licence. That is a broken scan, not a clean tree -- check syft ran javascript-package-cataloger. Passing this would report 'licences clean' having checked nothing.",
		[declared, total],
	)
}

# --- reported, not fatal ------------------------------------------------------

warn contains msg if {
	some pkg in input.packages
	some lic in pkg.licences
	normalise(lic) in copyleft_upper
	msg := sprintf("%v@%v is %v -- copyleft, fine to use, constrains distribution", [pkg.name, pkg.version, lic])
}

warn contains msg if {
	unlicensed := [p | some p in input.packages; count(p.licences) == 0]
	count(unlicensed) > 0
	msg := sprintf(
		"%v of %v packages declare no licence. Usually a metadata gap, but no licence grants nothing -- check any that ship in the product itself.",
		[count(unlicensed), count(input.packages)],
	)
}
