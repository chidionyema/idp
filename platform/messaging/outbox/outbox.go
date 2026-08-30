// Package outbox is decision D3 of ADR 0012: the transactional outbox is the
// only path a business event takes, and the relay is the only writer to the
// broker. A service writes its row and its event in one database transaction;
// the relay reads the table and publishes. Nothing is lost when the broker is
// down (the row waits) and nothing is invented when the service crashes after
// commit (the row is the record). Enforcement is credentials, not review: the
// service's NATS user cannot publish on orders.>, only the relay's can.
package outbox

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/jetstream"

	"github.com/chidionyema/idp/platform/messaging/cloudevent"
)

// Schema is the outbox table. `published_at IS NULL` is the relay's queue; the
// partial index keeps the poll cheap however large the history grows.
const Schema = `
CREATE TABLE IF NOT EXISTS outbox (
  id           uuid PRIMARY KEY,
  subject      text NOT NULL,
  headers      jsonb NOT NULL,
  payload      bytea NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now(),
  published_at timestamptz
);
CREATE INDEX IF NOT EXISTS outbox_unpublished ON outbox (created_at) WHERE published_at IS NULL;`

// Enqueue writes the event inside the caller's transaction. It is the only
// function a service calls; it never touches the broker.
func Enqueue(ctx context.Context, tx pgx.Tx, e cloudevent.Event) error {
	hdr, err := json.Marshal(e.Headers())
	if err != nil {
		return err
	}
	_, err = tx.Exec(ctx, `INSERT INTO outbox (id, subject, headers, payload) VALUES ($1, $2, $3, $4)`,
		e.ID, e.Subject.String(), hdr, e.Data)
	return err
}

// Relay moves rows to the stream. One relay per database; more than one is
// safe because of FOR UPDATE SKIP LOCKED, and a crash between publish and
// mark is safe because Nats-Msg-Id makes the second publish a duplicate.
type Relay struct {
	DB *pgxpool.Pool
	JS jetstream.JetStream
	// CrashAfterPublish, when set, returns before the mark on the first row: the
	// demo's way of proving the at-least-once path ends in exactly one stored copy.
	CrashAfterPublish func(id uuid.UUID) bool
}

// ErrCrashed is what CrashAfterPublish produces: the pass ends the way a
// process death would, with the row still unpublished.
var ErrCrashed = errors.New("relay crashed after publish, before mark")

// Result is one relayed row.
type Result struct {
	ID        uuid.UUID
	Subject   string
	Duplicate bool
	StreamSeq uint64
}

// Once drains what is unpublished now and returns what it did.
func (r *Relay) Once(ctx context.Context) ([]Result, error) {
	var out []Result
	for {
		res, more, err := r.one(ctx)
		if errors.Is(err, ErrCrashed) {
			return append(out, res), err
		}
		if err != nil {
			return out, err
		}
		if !more {
			return out, nil
		}
		out = append(out, res)
	}
}

func (r *Relay) one(ctx context.Context) (Result, bool, error) {
	tx, err := r.DB.Begin(ctx)
	if err != nil {
		return Result{}, false, err
	}
	defer func() { _ = tx.Rollback(ctx) }()
	var (
		id      uuid.UUID
		subj    string
		hdrJSON []byte
		payload []byte
	)
	err = tx.QueryRow(ctx, `SELECT id, subject, headers, payload FROM outbox
		WHERE published_at IS NULL ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED`).Scan(&id, &subj, &hdrJSON, &payload)
	if err == pgx.ErrNoRows {
		return Result{}, false, nil
	}
	if err != nil {
		return Result{}, false, err
	}
	hdr := nats.Header{}
	if err := json.Unmarshal(hdrJSON, &hdr); err != nil {
		return Result{}, false, fmt.Errorf("outbox %s: headers: %w", id, err)
	}
	ack, err := r.JS.PublishMsg(ctx, &nats.Msg{Subject: subj, Header: hdr, Data: payload})
	if err != nil {
		return Result{}, false, fmt.Errorf("outbox %s: publish: %w", id, err)
	}
	if r.CrashAfterPublish != nil && r.CrashAfterPublish(id) {
		return Result{ID: id, Subject: subj, Duplicate: ack.Duplicate, StreamSeq: ack.Sequence}, false, ErrCrashed // rollback: the row stays unpublished
	}
	if _, err := tx.Exec(ctx, `UPDATE outbox SET published_at = $2 WHERE id = $1`, id, time.Now().UTC()); err != nil {
		return Result{}, false, err
	}
	if err := tx.Commit(ctx); err != nil {
		return Result{}, false, err
	}
	return Result{ID: id, Subject: subj, Duplicate: ack.Duplicate, StreamSeq: ack.Sequence}, true, nil
}

// Unpublished counts the queue; the alert row in CP6 is this number over a threshold.
func Unpublished(ctx context.Context, db *pgxpool.Pool) (int, error) {
	var n int
	err := db.QueryRow(ctx, `SELECT count(*) FROM outbox WHERE published_at IS NULL`).Scan(&n)
	return n, err
}
