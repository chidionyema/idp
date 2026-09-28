// Package cloudevent is decision D2 of ADR 0012: CloudEvents 1.0 in binary
// mode, the attributes travel as NATS headers (ce-*), the payload is the body.
// Binary mode is what lets the broker, the relay and the DLQ processor route
// and trace a message without decoding its payload.
//
// The payload here is JSON; the protobuf 3 schema and `buf breaking` arrive
// with CP3 (platform/messaging/schemas). The headers do not change when it does.
package cloudevent

import (
	"crypto/rand"
	"encoding/hex"
	"time"

	"github.com/google/uuid"
	"github.com/nats-io/nats.go"

	"github.com/chidionyema/idp/platform/messaging/subject"
)

// Spec is the only CloudEvents version the estate speaks.
const Spec = "1.0"

// Event is one business event before it is enqueued.
type Event struct {
	ID          uuid.UUID
	Subject     subject.Subject // ce-type is the subject: one grammar, one name
	Source      string          // ce-source: the service, e.g. /orders
	Time        time.Time
	TraceParent string // W3C traceparent, so the trace id survives the outbox
	ContentType string
	Data        []byte
}

// New mints an event with a fresh id and a fresh trace.
func New(subj subject.Subject, source string, data []byte) Event {
	return Event{
		ID: uuid.New(), Subject: subj, Source: source, Time: time.Now().UTC(),
		TraceParent: newTraceParent(), ContentType: "application/json", Data: data,
	}
}

// Headers renders the binary-mode attributes. Nats-Msg-Id is the event id, so
// JetStream's duplicate window (D8: 15 minutes) drops a second copy of the same
// event: the relay may publish twice, the stream stores once.
func (e Event) Headers() nats.Header {
	h := nats.Header{}
	h.Set("ce-specversion", Spec)
	h.Set("ce-id", e.ID.String())
	h.Set("ce-type", e.Subject.String())
	h.Set("ce-source", e.Source)
	h.Set("ce-time", e.Time.Format(time.RFC3339Nano))
	h.Set("ce-datacontenttype", e.ContentType)
	h.Set("traceparent", e.TraceParent)
	h.Set(nats.MsgIdHdr, e.ID.String())
	return h
}

// TraceID is the 32-hex trace id inside a traceparent, or "" when absent.
func TraceID(traceparent string) string {
	if len(traceparent) < 55 {
		return ""
	}
	return traceparent[3:35]
}

func newTraceParent() string {
	var t [16]byte
	var s [8]byte
	_, _ = rand.Read(t[:])
	_, _ = rand.Read(s[:])
	return "00-" + hex.EncodeToString(t[:]) + "-" + hex.EncodeToString(s[:]) + "-01"
}
