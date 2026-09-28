// Package voice provides a Go SDK for FleetView voice events over NATS.
package voice

import (
	"encoding/json"
	"time"
)

// Event represents a voice event transmitted over NATS.
type Event struct {
	// ID is the unique identifier for this event.
	ID string `json:"id"`

	// Type categorizes the event (e.g., "voice", "command").
	Type string `json:"type"`

	// Action is the specific action being performed (e.g., "steer", "done").
	Action string `json:"action"`

	// Target is the optional target of the action.
	Target *string `json:"target,omitempty"`

	// Env is the optional environment context.
	Env *string `json:"env,omitempty"`

	// Confidence is the recognition confidence score (0.0 to 1.0).
	Confidence float64 `json:"confidence"`

	// Transcript is the recognized speech text.
	Transcript string `json:"transcript"`

	// Author is the identifier of the event originator.
	Author string `json:"author"`

	// Timestamp is when the event was created.
	Timestamp time.Time `json:"timestamp"`
}

// MarshalJSON implements json.Marshaler for Event.
func (e Event) MarshalJSON() ([]byte, error) {
	type Alias Event
	return json.Marshal(&struct {
		Timestamp string `json:"timestamp"`
		*Alias
	}{
		Timestamp: e.Timestamp.Format(time.RFC3339Nano),
		Alias:     (*Alias)(&e),
	})
}

// UnmarshalJSON implements json.Unmarshaler for Event.
func (e *Event) UnmarshalJSON(data []byte) error {
	type Alias Event
	aux := &struct {
		Timestamp string `json:"timestamp"`
		*Alias
	}{
		Alias: (*Alias)(e),
	}
	if err := json.Unmarshal(data, &aux); err != nil {
		return err
	}
	if aux.Timestamp != "" {
		t, err := time.Parse(time.RFC3339Nano, aux.Timestamp)
		if err != nil {
			// Try RFC3339 as fallback
			t, err = time.Parse(time.RFC3339, aux.Timestamp)
			if err != nil {
				return err
			}
		}
		e.Timestamp = t
	}
	return nil
}

// NewEvent creates a new Event with the given action and sets defaults.
func NewEvent(action string) Event {
	return Event{
		ID:        generateID(),
		Action:    action,
		Timestamp: time.Now().UTC(),
	}
}

// generateID creates a simple unique identifier.
func generateID() string {
	return time.Now().UTC().Format("20060102150405.000000000")
}

// EventHandler is the callback function type for handling incoming events.
type EventHandler func(Event)
