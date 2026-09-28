package controller_test

// Contract test: the Go types in api/v1alpha1 MUST stay in sync with the CRD YAML's openAPIV3
// schema. The offline gate (bin/nodesoftware-operator-gate, in PR #2338) grades the YAML side;
// this test grades the Go side. Drift in either direction fails CI before merge.
//
// This test is a no-op on the controller PR's branch (no CRD YAML on origin/main); it activates
// once #2338 lands on origin/main and the controller PR rebases. The contract test is then the
// second line of defence behind the offline gate.

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	nodesoftwarev1alpha1 "github.com/chidionyema/idp/platform/nodesoftware-operator/controller/api/v1alpha1"
)

// TestCRDContract_ClosedRuntimeSet locks the closed runtime set across the YAML and Go sides.
// The CRD YAML (when present) carries a spec.runtime enum; this test refuses drift with the
// runtime-install-gate's python validator. Today the Go side carries {runsc, kata, nvidia}.
// When #2338 lands on origin/main this test reads the YAML and validates equality.
func TestCRDContract_ClosedRuntimeSet(t *testing.T) {
	// Locate the CRD YAML relative to the controller module root.
	crdPath := findCRDYAML(t)
	if crdPath == "" {
		t.Skip("CRD YAML not on this branch (PR #2338 has not landed); skipping contract test")
	}

	yamlRuntimes := parseRuntimeEnumFromCRD(t, crdPath)

	yamlSet := make(map[string]struct{}, len(yamlRuntimes))
	for _, r := range yamlRuntimes {
		yamlSet[r] = struct{}{}
	}

	if len(yamlSet) != len(nodesoftwarev1alpha1.ClosedRuntimes) {
		t.Fatalf("closed runtime set drifted: YAML=%v, Go=%v", yamlRuntimes, closedKeys(nodesoftwarev1alpha1.ClosedRuntimes))
	}
	for r := range nodesoftwarev1alpha1.ClosedRuntimes {
		if _, ok := yamlSet[r]; !ok {
			t.Errorf("runtime %q is in Go's ClosedRuntimes but missing from CRD YAML's spec.runtime enum", r)
		}
	}
	for r := range yamlSet {
		if _, ok := nodesoftwarev1alpha1.ClosedRuntimes[r]; !ok {
			t.Errorf("runtime %q is in CRD YAML's spec.runtime enum but missing from Go's ClosedRuntimes", r)
		}
	}
}

// findCRDYAML walks up from the test's cwd looking for the CRD YAML at the conventional path.
// Returns "" if not found; the test then skips.
func findCRDYAML(t *testing.T) string {
	t.Helper()
	cwd, err := os.Getwd()
	if err != nil {
		t.Fatalf("getwd: %v", err)
	}
	dir := cwd
	for i := 0; i < 6; i++ {
		candidate := filepath.Join(dir, "platform", "nodesoftware-operator", "crds", "runtimeinstall.yaml")
		if _, err := os.Stat(candidate); err == nil {
			return candidate
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}
	return ""
}

// parseRuntimeEnumFromCRD does a substring scan for `runtime:` followed by an `enum:` list.
// This is intentionally cheap (no YAML library) -- the offline gate already validates the schema
// exhaustively, this test only needs the enum list. If the shape of the CRD changes such that
// this heuristic breaks, the offline gate will fail first and surface the change.
//
// Supports two enum shapes:
//   - inline:        enum: [runsc, kata, nvidia]
//   - multi-line:    enum:
//   - runsc
//   - kata
//   - nvidia
func parseRuntimeEnumFromCRD(t *testing.T, path string) []string {
	t.Helper()
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read CRD YAML: %v", err)
	}
	text := string(data)

	// Find the spec.runtime field specifically (NOT status, NOT anywhere else).
	// The CRD has: properties: spec: properties: runtime:
	// Walk the document until we find a "runtime:" key whose parent path is .../properties/spec/properties.
	// Cheap version: find every "runtime:" line and pick the one whose next non-blank line is "type: string"
	// followed by "enum:".
	lines := strings.Split(text, "\n")
	for i, line := range lines {
		trim := strings.TrimSpace(line)
		if trim != "runtime:" {
			continue
		}
		// Look ahead up to 6 lines for type: string + enum:.
		for j := i + 1; j < i+8 && j < len(lines); j++ {
			t2 := strings.TrimSpace(lines[j])
			if t2 == "" || strings.HasPrefix(t2, "#") {
				continue
			}
			if t2 == "type: string" {
				continue
			}
			if strings.HasPrefix(t2, "enum:") {
				return parseEnum(t, lines, j)
			}
			// Some other field appeared; this isn't the right "runtime:".
			break
		}
	}
	t.Fatalf("CRD YAML has no 'runtime:' field with type: string + enum: nearby")
	return nil
}

// parseEnum handles both enum shapes. The block shape matters: the CRD is inline today
// (`enum: [runsc, kata, nvidia]`), but every YAML formatter rewrites an inline sequence into a
// block one, and the previous version returned nil for the block shape. A nil there does not
// read as "could not parse" -- it reads as an empty YAML enum, and the caller reports
// `closed runtime set drifted: YAML=[], Go=[runsc kata nvidia]`. A true-looking failure with a
// false reason is worse than no test, so the block shape is parsed and an unrecognised shape
// fails with its own message.
func parseEnum(t *testing.T, lines []string, at int) []string {
	t.Helper()
	enumLine := strings.TrimSpace(lines[at])
	// Strip the "enum:" prefix.
	rest := strings.TrimSpace(strings.TrimPrefix(enumLine, "enum:"))
	// Strip any trailing inline comment ("# ...") so it doesn't fool the suffix check.
	if idx := strings.Index(rest, "#"); idx >= 0 {
		rest = strings.TrimSpace(rest[:idx])
	}
	// Inline array?
	if strings.HasPrefix(rest, "[") && strings.HasSuffix(rest, "]") {
		inner := rest[1 : len(rest)-1]
		parts := strings.Split(inner, ",")
		out := []string{}
		for _, p := range parts {
			val := strings.TrimSpace(p)
			val = strings.Trim(val, `"'`)
			if val != "" {
				out = append(out, val)
			}
		}
		return out
	}
	// Block shape: `enum:` alone on its line, then one `- value` per line, all indented
	// further than the `enum:` key. Stop at the first line that is not one of those.
	if rest != "" {
		t.Fatalf("enum on line %d is neither an inline array nor a bare `enum:`: %q", at+1, enumLine)
	}
	indent := len(lines[at]) - len(strings.TrimLeft(lines[at], " "))
	out := []string{}
	for k := at + 1; k < len(lines); k++ {
		raw := lines[k]
		trimmed := strings.TrimSpace(raw)
		if trimmed == "" || strings.HasPrefix(trimmed, "#") {
			continue
		}
		if len(raw)-len(strings.TrimLeft(raw, " ")) <= indent || !strings.HasPrefix(trimmed, "- ") {
			break
		}
		val := strings.TrimSpace(strings.TrimPrefix(trimmed, "- "))
		if idx := strings.Index(val, "#"); idx >= 0 {
			val = strings.TrimSpace(val[:idx])
		}
		val = strings.Trim(val, `"'`)
		if val != "" {
			out = append(out, val)
		}
	}
	if len(out) == 0 {
		t.Fatalf("enum on line %d parsed to nothing; the CRD's enum shape is not one this test handles", at+1)
	}
	return out
}

func closedKeys(m map[string]struct{}) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	return out
}
