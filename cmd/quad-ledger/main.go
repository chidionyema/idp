// cmd/quad-ledger/main.go
// Layer 4: tamper-evident history for the Quad (docs/tickets/2026-09-28-sovereign-identity-substrate-dros.md).
//
// One binary, four subcommands, so the deploy is one image:
//
//	migrate   create agent_actions and merkle_anchors in estate-db (idempotent)
//	consume   durable JetStream consumer on estate.quad.actions.> -> hash-chained rows
//	anchor    commit the chain head to merkle_anchors and PUT it to OCI Object Storage (PAR URL)
//	verify    recompute the whole chain and compare with the latest anchor; exit 1 on any mismatch
//
// The consumer is the single writer, so ordering is total and prev_hash is never contended.
// Every state change is also published on estate.quad.ledger.state for /fleet.
package main

import (
	"bytes"
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"os"
	"strings"
	"time"

	_ "github.com/jackc/pgx/v5/stdlib"
	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/jetstream"
)

const (
	subjectActions = "estate.quad.actions.>"
	subjectState   = "estate.quad.ledger.state"
	streamName     = "QUAD_ACTIONS"
	consumerName   = "quad-ledger"
)

const schema = `
create table if not exists agent_actions (
  seq              bigserial primary key,
  action_id        text not null unique,
  parent_action_id text,
  agent_urn        text not null,
  session_id       text not null,
  method           text not null,
  uri              text not null,
  ts               text not null,
  body_hash        text not null,
  signature        text not null,
  prev_hash        text not null,
  row_hash         text not null unique,
  inserted_at      timestamptz not null default now()
);
create table if not exists merkle_anchors (
  id             bigserial primary key,
  root_hash      text not null,
  leaf_count     bigint not null,
  last_seq       bigint not null,
  oci_object_uri text not null,
  anchored_at    timestamptz not null default now()
);
-- Rows are append-only: nothing in the estate may update or delete them. Enforced here so the
-- app role cannot, and detected by verify if a superuser does.
revoke update, delete on agent_actions from public;
`

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: quad-ledger migrate|consume|anchor|verify")
		os.Exit(2)
	}
	ctx := context.Background()
	db, err := sql.Open("pgx", must("DATABASE_URL"))
	if err != nil {
		die(err)
	}
	defer db.Close()
	switch os.Args[1] {
	case "migrate":
		_, err = db.ExecContext(ctx, schema)
		if err == nil {
			fmt.Println("quad-ledger: schema ready")
		}
	case "consume":
		err = consume(ctx, db)
	case "anchor":
		err = anchor(ctx, db)
	case "verify":
		err = verify(ctx, db)
	default:
		err = fmt.Errorf("unknown subcommand %q", os.Args[1])
	}
	if err != nil {
		die(err)
	}
}

// ---- consume ---------------------------------------------------------------------------------

func consume(ctx context.Context, db *sql.DB) error {
	nc, err := nats.Connect(must("NATS_URL"), nats.Name("quad-ledger"))
	if err != nil {
		return err
	}
	defer nc.Drain()
	js, err := jetstream.New(nc)
	if err != nil {
		return err
	}
	// The stream is the estate's, created here only if absent, so a fresh cluster works.
	stream, err := js.CreateOrUpdateStream(ctx, jetstream.StreamConfig{
		Name: streamName, Subjects: []string{subjectActions}, Retention: jetstream.LimitsPolicy,
		MaxAge: 30 * 24 * time.Hour, Storage: jetstream.FileStorage,
	})
	if err != nil {
		return fmt.Errorf("stream: %w", err)
	}
	cons, err := stream.CreateOrUpdateConsumer(ctx, jetstream.ConsumerConfig{
		Durable: consumerName, AckPolicy: jetstream.AckExplicitPolicy, MaxAckPending: 1, // one at a time: the chain is serial
	})
	if err != nil {
		return fmt.Errorf("consumer: %w", err)
	}
	head, count, err := chainHead(ctx, db)
	if err != nil {
		return err
	}
	fmt.Printf("quad-ledger: consuming from head %s (%d rows)\n", short(head), count)
	iter, err := cons.Messages()
	if err != nil {
		return err
	}
	defer iter.Stop()
	for {
		msg, err := iter.Next()
		if err != nil {
			return err
		}
		var a Action
		if err := json.Unmarshal(msg.Data(), &a); err != nil || a.ActionID == "" || a.Signature == "" {
			// A malformed record is not history; it is dropped with its subject named so /fleet shows it.
			fmt.Fprintf(os.Stderr, "quad-ledger: dropped malformed record on %s: %v\n", msg.Subject(), err)
			_ = msg.Term()
			continue
		}
		rowHash := RowHash(head, a)
		_, err = db.ExecContext(ctx, `insert into agent_actions
			(action_id, parent_action_id, agent_urn, session_id, method, uri, ts, body_hash, signature, prev_hash, row_hash)
			values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11) on conflict (action_id) do nothing`,
			a.ActionID, nullable(a.ParentActionID), a.AgentURN, a.SessionID, a.Method, a.URI, a.Timestamp, a.BodyHash, a.Signature, head, rowHash)
		if err != nil {
			_ = msg.Nak()
			return fmt.Errorf("insert: %w", err)
		}
		// Re-read the head: on a duplicate (redelivery) the row already exists and the head did not move.
		head, count, err = chainHead(ctx, db)
		if err != nil {
			return err
		}
		_ = msg.Ack()
		publishState(nc, map[string]any{"head": head, "leaf_count": count, "last_agent": a.AgentURN, "last_action": a.ActionID, "at": time.Now().UTC().Format(time.RFC3339)})
	}
}

// ---- anchor ----------------------------------------------------------------------------------

// anchor writes the chain head to merkle_anchors and to OCI Object Storage through a
// pre-authenticated request URL (write-only PAR on the quad-anchors bucket, held in the vault as
// QUAD_ANCHOR_PAR_URL). No SDK, no long-lived key: the PAR is the only credential and it can
// only create objects, never read or delete them.
func anchor(ctx context.Context, db *sql.DB) error {
	head, count, err := chainHead(ctx, db)
	if err != nil {
		return err
	}
	if count == 0 {
		fmt.Println("quad-ledger: nothing to anchor yet")
		return nil
	}
	var lastSeq int64
	if err := db.QueryRowContext(ctx, `select coalesce(max(seq),0) from agent_actions`).Scan(&lastSeq); err != nil {
		return err
	}
	name := fmt.Sprintf("anchor-%s-seq%d.json", time.Now().UTC().Format("20060102T150405Z"), lastSeq)
	body, _ := json.Marshal(map[string]any{"root_hash": head, "leaf_count": count, "last_seq": lastSeq, "anchored_at": time.Now().UTC().Format(time.RFC3339)})
	uri := must("QUAD_ANCHOR_PAR_URL") + name
	req, _ := http.NewRequestWithContext(ctx, http.MethodPut, uri, bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return fmt.Errorf("object storage: %w", err)
	}
	resp.Body.Close()
	if resp.StatusCode/100 != 2 {
		return fmt.Errorf("object storage: HTTP %d putting %s", resp.StatusCode, name)
	}
	_, err = db.ExecContext(ctx, `insert into merkle_anchors (root_hash, leaf_count, last_seq, oci_object_uri) values ($1,$2,$3,$4)`, head, count, lastSeq, name)
	if err != nil {
		return err
	}
	fmt.Printf("quad-ledger: anchored %s (%d rows) as %s\n", short(head), count, name)
	return nil
}

// ---- verify ----------------------------------------------------------------------------------

// verify recomputes every row and compares the head with the latest anchor. Exit 1 is the
// only output that matters: this is the check that must go red on a planted fault.
func verify(ctx context.Context, db *sql.DB) error {
	rs, err := db.QueryContext(ctx, `select seq, action_id, coalesce(parent_action_id,''), agent_urn, session_id, method, uri, ts, body_hash, signature, prev_hash, row_hash from agent_actions order by seq`)
	if err != nil {
		return err
	}
	defer rs.Close()
	var rows []Row
	for rs.Next() {
		var r Row
		if err := rs.Scan(&r.Seq, &r.Action.ActionID, &r.Action.ParentActionID, &r.Action.AgentURN, &r.Action.SessionID, &r.Action.Method, &r.Action.URI, &r.Action.Timestamp, &r.Action.BodyHash, &r.Action.Signature, &r.PrevHash, &r.RowHash); err != nil {
			return err
		}
		rows = append(rows, r)
	}
	var anchored string
	var anchorSeq int64
	err = db.QueryRowContext(ctx, `select root_hash, last_seq from merkle_anchors order by id desc limit 1`).Scan(&anchored, &anchorSeq)
	if errors.Is(err, sql.ErrNoRows) {
		anchored, anchorSeq = "", 0
	} else if err != nil {
		return err
	}
	// Verify the anchored prefix against the anchor, then the tail against itself.
	prefix := rows
	if anchorSeq > 0 && int64(len(rows)) > anchorSeq {
		prefix = rows[:anchorSeq]
	}
	head, bad, verr := Verify(prefix, anchored)
	if verr == nil && len(prefix) < len(rows) {
		head, bad, verr = Verify(rows, "")
	}
	state := map[string]any{"verified": verr == nil, "rows": len(rows), "head": head, "anchor": anchored, "bad_seq": bad, "at": time.Now().UTC().Format(time.RFC3339)}
	if nc, err := nats.Connect(os.Getenv("NATS_URL")); err == nil {
		publishState(nc, state)
		nc.Drain()
	}
	if verr != nil {
		return fmt.Errorf("LEDGER RED: %w", verr)
	}
	fmt.Printf("quad-ledger: %d rows verified, head %s matches anchor\n", len(rows), short(head))
	return nil
}

// ---- helpers ---------------------------------------------------------------------------------

func chainHead(ctx context.Context, db *sql.DB) (string, int64, error) {
	var head sql.NullString
	var count int64
	err := db.QueryRowContext(ctx, `select (select row_hash from agent_actions order by seq desc limit 1), count(*) from agent_actions`).Scan(&head, &count)
	if err != nil {
		return "", 0, err
	}
	if !head.Valid {
		return ZeroHash, 0, nil
	}
	return head.String, count, nil
}

func publishState(nc *nats.Conn, state map[string]any) {
	b, _ := json.Marshal(state)
	_ = nc.Publish(subjectState, b)
}

func nullable(s string) any {
	if s == "" {
		return nil
	}
	return s
}

// must reads NAME_FILE (a mounted secret, the estate's convention: an env-var secret is refused
// by platform/edge/kyverno-secrets-policy.yaml) and falls back to NAME for local runs.
func must(env string) string {
	if f := os.Getenv(env + "_FILE"); f != "" {
		b, err := os.ReadFile(f)
		if err != nil {
			die(fmt.Errorf("%s_FILE: %w", env, err))
		}
		return strings.TrimSpace(string(b))
	}
	v := os.Getenv(env)
	if v == "" {
		die(fmt.Errorf("%s must be set", env))
	}
	return v
}

func die(err error) {
	fmt.Fprintf(os.Stderr, "FATAL: %v\n", err)
	os.Exit(1)
}
