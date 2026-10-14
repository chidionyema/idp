package brain

import (
	"os"
	"path/filepath"
	"testing"
)

// Narration must never share the founder's interactive lane: on 2026-09-30 it did, and 78% of
// voice calls came back 429 with first token at 7.6 s p50.
func TestNarrateFromEnvUsesItsOwnLane(t *testing.T) {
	t.Setenv("LLM_MODEL", "voice")
	t.Setenv("LLM_NARRATE_MODEL", "")
	t.Setenv("LLM_BASE_URL", "http://router.test/v1/")
	t.Setenv("LLM_API_KEY", "k")

	talk, narrate := FromEnv(), NarrateFromEnv()
	if talk.Model != "voice" {
		t.Fatalf("FromEnv model = %q, want voice", talk.Model)
	}
	if narrate.Model != "narrate" {
		t.Fatalf("NarrateFromEnv model = %q, want narrate", narrate.Model)
	}
	if narrate.BaseURL != talk.BaseURL || narrate.APIKey != talk.APIKey {
		t.Fatalf("narrate endpoint/key differ from voice: %q vs %q", narrate.BaseURL, talk.BaseURL)
	}
	if narrate.MaxTokens >= talk.MaxTokens {
		t.Fatalf("narrate max_tokens %d should be below voice %d", narrate.MaxTokens, talk.MaxTokens)
	}

	t.Setenv("LLM_NARRATE_MODEL", "narrate-b")
	if got := NarrateFromEnv().Model; got != "narrate-b" {
		t.Fatalf("LLM_NARRATE_MODEL not honoured: %q", got)
	}
}

func TestAPIKeyFromEnvReadsTheMountedFile(t *testing.T) {
	t.Setenv("LLM_API_KEY", "")
	p := filepath.Join(t.TempDir(), "key")
	if err := os.WriteFile(p, []byte("sk-file\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("LLM_API_KEY_FILE", p)
	if got := APIKeyFromEnv(); got != "sk-file" {
		t.Fatalf("APIKeyFromEnv() = %q, want the file's key with the newline trimmed", got)
	}
	t.Setenv("LLM_API_KEY", "sk-env")
	if got := APIKeyFromEnv(); got != "sk-env" {
		t.Fatalf("APIKeyFromEnv() = %q, want LLM_API_KEY to win over the file", got)
	}
	t.Setenv("LLM_API_KEY", "")
	t.Setenv("LLM_API_KEY_FILE", filepath.Join(t.TempDir(), "absent"))
	if got := APIKeyFromEnv(); got != "" {
		t.Fatalf("APIKeyFromEnv() = %q, want no key when the file is absent (anchor stays on templates)", got)
	}
}
