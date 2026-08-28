# The no-toil gate. An agent may not merge a manual human step (crew#66).
#
# Founder, 2026-08-28, verbatim: "the moment the agent was left to design a workflow, it
# defaulted to the lowest-common-denominator, amateur-hour playbook: 'Go click around a UI,
# mint a token, and paste it manually.' ... To ensure you never see a manual setup step
# proposed or executed again enterprise-wide, we must make it mathematically impossible for
# an agent to merge one."
#
# The rejected sentence that opened this incident (crew#66, comment 5451623095) asked the
# founder to mint a Tailscale OAuth client in a console and hand the value to a vault secret.
# A playbook is not a guard (LAW 44). This file is the guard: it fails the pull request in CI
# before a reviewer ever reads the sentence.
#
# TWO INPUT SHAPES, ONE POLICY, because the estate already runs conftest twice on a PR and a
# second copy of these phrases would be the stitching the headline refuses:
#
#   1. one document per file      {"file_path": "docs/x.md", "content": ["line", ...]}
#      written by bin/idp-no-toil for every README*.md, docs/**/*.md and platform/** file the
#      pull request changes, so the conftest FAIL line names the offending file.
#   2. reports/pr.json            {"pr": {"body": "<pull request body>", ...}}
#      written by bin/pr-report, so the operating-model gate judges the PR body with the same
#      rule and no second job is needed for it.
#
# Deliberately NOT scanned: the whole diff (input.pr.added). The phrases have to be writable in
# the policy, its tests and its own commit message, or the guard could never be committed --
# and a guard that refuses correct work is an outage (LAW 38).

package main

import rego.v1

# The message the founder specified, to the character. It is the whole of every deny in this
# file: bin/idp-no-toil prints the file and the line beside it, so nothing is lost by keeping
# the sentence exact.
toil_message := "Policy Violation: Instructions contain manual human toil steps. Automate the bootstrapping sequence."

# The founder's four phrases, plus "paste it into" (the verb in the rejected sentence) and
# "log into the web interface" (the UI round trip they all bottom out in). Case-insensitive.
toil_phrases := `(?i)(manually create|paste this|paste it into|click here|log into the web interface|founder must)`

# LAW 47: the one human step the estate allows is a FOUNDER ACTION line that names a URL or a
# single word -- a tap, not a transcription. Its verb may never be paste, copy or type.
founder_action_prefix := `^[-*>\s]*FOUNDER ACTION:`

hand_verbs := `(?i)\b(paste|pastes|pasted|pasting|copy|copies|copied|copying|type|types|typed|typing)\b`

# --- shape 1: one changed file, fed by bin/idp-no-toil -----------------------------------

deny contains toil_message if {
	scanned(input.file_path)
	some line in input.content
	offending(trim_space(line))
}

# --- shape 2: the pull request body, fed by bin/pr-report through reports/pr.json ---------

deny contains toil_message if {
	some line in split(input.pr.body, "\n")
	offending(trim_space(line))
}

# --- what counts ---------------------------------------------------------------------------

# A line that is not a FOUNDER ACTION line and carries one of the phrases.
offending(line) if {
	not founder_action(line)
	regex.match(toil_phrases, line)
}

# A FOUNDER ACTION line that asks for a hand rather than a tap. A line naming a URL and a verb
# like "open" or "approve" passes; one whose verb is paste, copy or type does not.
offending(line) if {
	founder_action(line)
	not founder_action_allowed(line)
}

founder_action(line) if regex.match(founder_action_prefix, line)

founder_action_allowed(line) if {
	body := founder_action_body(line)
	not regex.match(hand_verbs, body)
	names_url_or_single_word(body)
}

founder_action_body(line) := trim_space(regex.replace(line, founder_action_prefix, ""))

names_url_or_single_word(body) if regex.match(`https?://\S+`, body)

names_url_or_single_word(body) if regex.match(`^\S+$`, body)

# --- scope -----------------------------------------------------------------------------------
# README*.md anywhere, docs/**/*.md, and platform/** manifests. The policy carries its own
# scope so a caller cannot widen it by feeding a file the founder never agreed to gate.

scanned(path) if regex.match(`(^|/)README[^/]*\.md$`, path)

scanned(path) if regex.match(`(^|/)docs/.*\.md$`, path)

scanned(path) if regex.match(`(^|/)platform/`, path)
