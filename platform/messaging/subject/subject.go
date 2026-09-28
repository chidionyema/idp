// Package subject is decision D1 of ADR 0012 as code: the grammar
// {domain}.{kind}.{aggregate}.{action}.{version}, five lower-case tokens, no
// environment, tenant or region, a new version is a new subject. It is locked
// (reversal cost "very high, treat as an API"), so it lives in one place and
// every publisher, the relay and bin/messaging-subject-gate (CP3) call this.
package subject

import (
	"fmt"
	"regexp"
	"strings"
)

var (
	token   = regexp.MustCompile(`^[a-z][a-z0-9_]*$`)
	version = regexp.MustCompile(`^v[1-9][0-9]*$`)
	kinds   = map[string]bool{"event": true, "command": true, "dlq": true}
	// environments and regions are the words D1 forbids in a subject.
	forbidden = map[string]bool{"prod": true, "production": true, "staging": true, "dev": true, "test": true, "eu": true, "us": true, "uk": true}
)

// Subject is one parsed subject.
type Subject struct {
	Domain, Kind, Aggregate, Action, Version string
}

// String renders the subject back in the grammar.
func (s Subject) String() string {
	return strings.Join([]string{s.Domain, s.Kind, s.Aggregate, s.Action, s.Version}, ".")
}

// Parse grades a subject against D1 and names the rule broken.
func Parse(raw string) (Subject, error) {
	parts := strings.Split(raw, ".")
	if len(parts) != 5 {
		return Subject{}, fmt.Errorf("subject %q: rule D1-shape: five tokens {domain}.{kind}.{aggregate}.{action}.{version}, got %d", raw, len(parts))
	}
	for i, p := range parts[:4] {
		if !token.MatchString(p) {
			return Subject{}, fmt.Errorf("subject %q: rule D1-case: token %d %q must be lower-case [a-z][a-z0-9_]*", raw, i+1, p)
		}
	}
	if forbidden[parts[0]] {
		return Subject{}, fmt.Errorf("subject %q: rule D1-no-environment: %q is an environment or region, never part of a subject", raw, parts[0])
	}
	if !kinds[parts[1]] {
		return Subject{}, fmt.Errorf("subject %q: rule D1-kind: kind %q is not event, command or dlq", raw, parts[1])
	}
	if !strings.HasSuffix(parts[3], "ed") && parts[1] == "event" {
		return Subject{}, fmt.Errorf("subject %q: rule D1-past-tense: an event action is past tense (placed, paid), got %q", raw, parts[3])
	}
	if !version.MatchString(parts[4]) {
		return Subject{}, fmt.Errorf("subject %q: rule D1-version: version %q must be v1, v2, ...", raw, parts[4])
	}
	return Subject{parts[0], parts[1], parts[2], parts[3], parts[4]}, nil
}

// MustParse is Parse for compile-time constants in the estate's own code.
func MustParse(raw string) Subject {
	s, err := Parse(raw)
	if err != nil {
		panic(err)
	}
	return s
}
