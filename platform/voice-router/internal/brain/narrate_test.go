package brain

import "testing"

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
