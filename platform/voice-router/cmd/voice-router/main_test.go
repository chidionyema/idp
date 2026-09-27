package main

import "testing"

func TestTurnsAreReadableOnlyByAllowedOrigins(t *testing.T) {
	allow := []string{"localhost:3100", "127.0.0.1:3100", "*.mumchimp.com"}
	for origin, want := range map[string]bool{
		"http://localhost:3100":       true,
		"http://LOCALHOST:3100":       true,
		"https://portal.mumchimp.com": true,
		"http://localhost:3000":       false,
		"https://evil.example":        false,
		"":                            false,
		"not a url":                   false,
	} {
		if got := allowedOrigin(allow, origin); got != want {
			t.Errorf("allowedOrigin(%q) = %v, want %v", origin, got, want)
		}
	}
}
