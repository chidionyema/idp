// Package inbox is the consumer side of at-least-once delivery: an idempotent
// handler. The broker may deliver an event twice (redelivery after a crash,
// a replay after a restore, §11 test 8); the effect must happen once. The
// processed_events row and the business effect commit in one transaction, so
// a crash between them re-runs cleanly and a second delivery does nothing.
package inbox

import (
	"context"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// Schema is the inbox table, keyed by consumer so two services can each
// process the same event once.
const Schema = `
CREATE TABLE IF NOT EXISTS processed_events (
  consumer     text NOT NULL,
  event_id     uuid NOT NULL,
  processed_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (consumer, event_id)
);`

// Effect is the business work, run inside the same transaction as the inbox row.
type Effect func(ctx context.Context, tx pgx.Tx) error

// Process runs effect exactly once per (consumer, event id). It returns
// applied=false when the event was already processed; the caller still acks.
func Process(ctx context.Context, db *pgxpool.Pool, consumer string, eventID uuid.UUID, effect Effect) (applied bool, err error) {
	tx, err := db.Begin(ctx)
	if err != nil {
		return false, err
	}
	defer func() { _ = tx.Rollback(ctx) }()
	tag, err := tx.Exec(ctx, `INSERT INTO processed_events (consumer, event_id) VALUES ($1, $2) ON CONFLICT DO NOTHING`, consumer, eventID)
	if err != nil {
		return false, err
	}
	if tag.RowsAffected() == 0 {
		return false, nil
	}
	if err := effect(ctx, tx); err != nil {
		return false, err
	}
	return true, tx.Commit(ctx)
}
