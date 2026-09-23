package voice

import (
	"context"
	"encoding/json"
	"testing"
	"time"
)

func TestNewClient(t *testing.T) {
	cfg := Config{
		Token:   "test-token",
		NatsURL: "nats://localhost:4222",
		Name:    "test-client",
	}

	client := NewClient(cfg)

	if client == nil {
		t.Fatal("NewClient returned nil")
	}

	if client.config.Token != "test-token" {
		t.Errorf("Token = %q, want %q", client.config.Token, "test-token")
	}

	if client.config.NatsURL != "nats://localhost:4222" {
		t.Errorf("NatsURL = %q, want %q", client.config.NatsURL, "nats://localhost:4222")
	}

	// Check defaults were applied
	if client.config.Subject != "voice.events" {
		t.Errorf("Subject = %q, want %q", client.config.Subject, "voice.events")
	}

	if client.config.ReconnectWait != time.Second {
		t.Errorf("ReconnectWait = %v, want %v", client.config.ReconnectWait, time.Second)
	}

	if client.config.MaxReconnectWait != 30*time.Second {
		t.Errorf("MaxReconnectWait = %v, want %v", client.config.MaxReconnectWait, 30*time.Second)
	}
}

func TestNewClientWithOptions(t *testing.T) {
	client := NewClient(Config{},
		WithToken("opt-token"),
		WithNatsURL("nats://remote:4222"),
		WithSubject("custom.subject"),
		WithName("opt-client"),
		WithAuthor("opt-author"),
		WithReconnectWait(2*time.Second),
		WithMaxReconnectWait(60*time.Second),
		WithMaxReconnects(5),
	)

	if client.config.Token != "opt-token" {
		t.Errorf("Token = %q, want %q", client.config.Token, "opt-token")
	}

	if client.config.NatsURL != "nats://remote:4222" {
		t.Errorf("NatsURL = %q, want %q", client.config.NatsURL, "nats://remote:4222")
	}

	if client.config.Subject != "custom.subject" {
		t.Errorf("Subject = %q, want %q", client.config.Subject, "custom.subject")
	}

	if client.config.Author != "opt-author" {
		t.Errorf("Author = %q, want %q", client.config.Author, "opt-author")
	}

	if client.config.MaxReconnects != 5 {
		t.Errorf("MaxReconnects = %d, want %d", client.config.MaxReconnects, 5)
	}
}

func TestConnectWithoutURL(t *testing.T) {
	client := NewClient(Config{})

	err := client.Connect()
	if err != ErrEmptyNatsURL {
		t.Errorf("Connect() = %v, want %v", err, ErrEmptyNatsURL)
	}
}

func TestEmitWithoutConnection(t *testing.T) {
	client := NewClient(Config{
		NatsURL: "nats://localhost:4222",
	})

	err := client.Emit("test", Event{})
	if err != ErrNotConnected {
		t.Errorf("Emit() = %v, want %v", err, ErrNotConnected)
	}
}

func TestEmitEmptyAction(t *testing.T) {
	client := NewClient(Config{
		NatsURL: "nats://localhost:4222",
	})
	// Simulate connected state for test
	client.connected = true

	err := client.Emit("", Event{})
	if err != ErrEmptyAction {
		t.Errorf("Emit('') = %v, want %v", err, ErrEmptyAction)
	}
}

func TestOnHandlerRegistration(t *testing.T) {
	client := NewClient(Config{
		NatsURL: "nats://localhost:4222",
	})

	called := false
	client.On("test", func(e Event) {
		called = true
	})

	if len(client.handlers["test"]) != 1 {
		t.Errorf("handlers['test'] length = %d, want 1", len(client.handlers["test"]))
	}

	// Register another handler for the same action
	client.On("test", func(e Event) {})

	if len(client.handlers["test"]) != 2 {
		t.Errorf("handlers['test'] length = %d, want 2", len(client.handlers["test"]))
	}
}

func TestIsConnectedWhenDisconnected(t *testing.T) {
	client := NewClient(Config{
		NatsURL: "nats://localhost:4222",
	})

	if client.IsConnected() {
		t.Error("IsConnected() = true, want false for new client")
	}
}

func TestDisconnectIdempotent(t *testing.T) {
	client := NewClient(Config{
		NatsURL: "nats://localhost:4222",
	})

	// Should not panic when called multiple times
	client.Disconnect()
	client.Disconnect()
	client.Disconnect()

	if client.IsConnected() {
		t.Error("IsConnected() = true after Disconnect()")
	}
}

func TestReconnectDelay(t *testing.T) {
	client := NewClient(Config{
		NatsURL:          "nats://localhost:4222",
		ReconnectWait:    time.Second,
		MaxReconnectWait: 30 * time.Second,
	})

	tests := []struct {
		attempts int
		want     time.Duration
	}{
		{0, time.Second},      // 1s * 2^0 = 1s
		{1, 2 * time.Second},  // 1s * 2^1 = 2s
		{2, 4 * time.Second},  // 1s * 2^2 = 4s
		{3, 8 * time.Second},  // 1s * 2^3 = 8s
		{4, 16 * time.Second}, // 1s * 2^4 = 16s
		{5, 30 * time.Second}, // 1s * 2^5 = 32s -> capped at 30s
		{6, 30 * time.Second}, // Still capped
	}

	for _, tt := range tests {
		got := client.reconnectDelay(tt.attempts)
		if got != tt.want {
			t.Errorf("reconnectDelay(%d) = %v, want %v", tt.attempts, got, tt.want)
		}
	}
}

func TestConnectWithContextCancellation(t *testing.T) {
	client := NewClient(Config{
		NatsURL: "nats://localhost:4222",
	})

	ctx, cancel := context.WithCancel(context.Background())
	cancel() // Cancel immediately

	err := client.ConnectWithContext(ctx)
	if err != context.Canceled {
		// May also fail with connection error before context check
		if err == nil {
			t.Error("ConnectWithContext with canceled context should return error")
		}
	}
}

func TestAuthorDefaultsToName(t *testing.T) {
	cfg := Config{
		NatsURL: "nats://localhost:4222",
		Name:    "my-client",
	}
	cfg.applyDefaults()

	if cfg.Author != "my-client" {
		t.Errorf("Author = %q, want %q (should default to Name)", cfg.Author, "my-client")
	}
}

func TestEventMarshalJSON(t *testing.T) {
	target := "target-1"
	env := "production"
	event := Event{
		ID:         "123",
		Type:       "voice",
		Action:     "steer",
		Target:     &target,
		Env:        &env,
		Confidence: 0.95,
		Transcript: "turn left",
		Author:     "user-1",
		Timestamp:  time.Date(2024, 1, 15, 10, 30, 0, 0, time.UTC),
	}

	data, err := json.Marshal(event)
	if err != nil {
		t.Fatalf("Marshal failed: %v", err)
	}

	var decoded map[string]interface{}
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("Unmarshal failed: %v", err)
	}

	if decoded["id"] != "123" {
		t.Errorf("id = %v, want %v", decoded["id"], "123")
	}

	if decoded["action"] != "steer" {
		t.Errorf("action = %v, want %v", decoded["action"], "steer")
	}

	if decoded["transcript"] != "turn left" {
		t.Errorf("transcript = %v, want %v", decoded["transcript"], "turn left")
	}
}

func TestEventUnmarshalJSON(t *testing.T) {
	jsonData := `{
		"id": "456",
		"type": "command",
		"action": "done",
		"confidence": 0.88,
		"transcript": "task complete",
		"author": "agent-2",
		"timestamp": "2024-01-15T10:30:00Z"
	}`

	var event Event
	if err := json.Unmarshal([]byte(jsonData), &event); err != nil {
		t.Fatalf("Unmarshal failed: %v", err)
	}

	if event.ID != "456" {
		t.Errorf("ID = %q, want %q", event.ID, "456")
	}

	if event.Action != "done" {
		t.Errorf("Action = %q, want %q", event.Action, "done")
	}

	if event.Confidence != 0.88 {
		t.Errorf("Confidence = %v, want %v", event.Confidence, 0.88)
	}

	expectedTime := time.Date(2024, 1, 15, 10, 30, 0, 0, time.UTC)
	if !event.Timestamp.Equal(expectedTime) {
		t.Errorf("Timestamp = %v, want %v", event.Timestamp, expectedTime)
	}
}

func TestNewEvent(t *testing.T) {
	event := NewEvent("test-action")

	if event.ID == "" {
		t.Error("ID should not be empty")
	}

	if event.Action != "test-action" {
		t.Errorf("Action = %q, want %q", event.Action, "test-action")
	}

	if event.Timestamp.IsZero() {
		t.Error("Timestamp should not be zero")
	}
}

func TestGenerateID(t *testing.T) {
	id1 := generateID()
	time.Sleep(time.Millisecond)
	id2 := generateID()

	if id1 == "" {
		t.Error("generateID() returned empty string")
	}

	if id1 == id2 {
		t.Error("generateID() should return unique IDs")
	}
}
