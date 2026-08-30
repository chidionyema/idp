// Package dlq is the dead-letter processor: when a consumer gives up on a
// message (max_deliver reached) JetStream publishes an advisory; this copies
// the original message, headers intact, into the DLQ stream under the dlq
// kind of the same grammar, so it can be inspected and replayed by `ops
// replay` (CP7) and never lost. The consumer itself never writes the DLQ:
// one writer per stream, enforced by the DLQ user's permissions.
package dlq

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/jetstream"

	"github.com/chidionyema/idp/platform/messaging/subject"
)

// Advisory is the part of $JS.EVENT.ADVISORY.CONSUMER.MAX_DELIVERIES that matters.
type Advisory struct {
	Stream     string `json:"stream"`
	Consumer   string `json:"consumer"`
	StreamSeq  uint64 `json:"stream_seq"`
	Deliveries int    `json:"deliveries"`
}

// AdvisorySubject is where JetStream announces a consumer's give-up.
func AdvisorySubject(stream, consumer string) string {
	return fmt.Sprintf("$JS.EVENT.ADVISORY.CONSUMER.MAX_DELIVERIES.%s.%s", stream, consumer)
}

// Subject maps orders.event.order.placed.v1 to orders.dlq.order.placed.v1.
func Subject(s subject.Subject) subject.Subject {
	s.Kind = "dlq"
	return s
}

// Copy handles one advisory: fetch the original by sequence, publish it to
// the DLQ subject with the reason on a header. Returns the DLQ subject used.
func Copy(ctx context.Context, js jetstream.JetStream, raw []byte) (string, error) {
	var adv Advisory
	if err := json.Unmarshal(raw, &adv); err != nil {
		return "", err
	}
	st, err := js.Stream(ctx, adv.Stream)
	if err != nil {
		return "", err
	}
	orig, err := st.GetMsg(ctx, adv.StreamSeq)
	if err != nil {
		return "", err
	}
	s, err := subject.Parse(orig.Subject)
	if err != nil {
		return "", err
	}
	hdr := nats.Header(orig.Header)
	if hdr == nil {
		hdr = nats.Header{}
	}
	hdr.Set("Dlq-Reason", fmt.Sprintf("max_deliver %d reached on consumer %s", adv.Deliveries, adv.Consumer))
	hdr.Set("Dlq-Origin-Seq", fmt.Sprint(adv.StreamSeq))
	target := Subject(s).String()
	if _, err := js.PublishMsg(ctx, &nats.Msg{Subject: target, Header: hdr, Data: orig.Data}); err != nil {
		return "", err
	}
	return target, nil
}
