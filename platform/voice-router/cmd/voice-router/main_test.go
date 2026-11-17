package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// The estate's DNS zone. It is written once, in clusters/k3s/estate-config.yaml, and every
// other file in the estate says ${ESTATE_ZONE}. The environment wins when it carries one (CI
// sets it from the repository variable); otherwise the one place it is written is read. This
// test never skips: a zone it cannot resolve is a FAIL, not a pass that runs nothing.
func estateZone(t *testing.T) string {
	t.Helper()
	if zone := strings.TrimSpace(os.Getenv("ESTATE_ZONE")); zone != "" {
		return zone
	}
	config := filepath.Join("..", "..", "..", "..", "clusters", "k3s", "estate-config.yaml")
	raw, err := os.ReadFile(config)
	if err != nil {
		t.Fatalf("ESTATE_ZONE is not set and %s is unreadable: %v", config, err)
	}
	for _, line := range strings.Split(string(raw), "\n") {
		key, value, ok := strings.Cut(line, ":")
		if ok && strings.TrimSpace(key) == "ESTATE_ZONE" {
			if zone := strings.TrimSpace(value); zone != "" {
				return zone
			}
		}
	}
	t.Fatalf("no ESTATE_ZONE in %s", config)
	return ""
}

func TestTurnsAreReadableOnlyByAllowedOrigins(t *testing.T) {
	// The zone is written in one place (clusters/k3s/estate-config.yaml) and reaches this
	// process as ESTATE_ZONE. A test that spells the zone would be a second copy of it.
	zone := estateZone(t)
	allow := []string{"localhost:3100", "127.0.0.1:3100", "*." + zone}
	for origin, want := range map[string]bool{
		"http://localhost:3100":  true,
		"http://LOCALHOST:3100":  true,
		"https://portal." + zone: true,
		"http://localhost:3000":  false,
		"https://evil.example":   false,
		"":                       false,
		"not a url":              false,
	} {
		if got := allowedOrigin(allow, origin); got != want {
			t.Errorf("allowedOrigin(%q) = %v, want %v", origin, got, want)
		}
	}
}
