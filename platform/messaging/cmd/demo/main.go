// The messaging demo (crew#639 CP9): `demo basic` and `demo advanced`.
//
//	basic     one CloudEvents message on the locked ORDERS_EVENTS stream, one
//	          durable pull consumer, explicit ack. What every service sees.
//	advanced  the transactional outbox end to end: a service that cannot reach
//	          the broker, a relay that crashes after publishing and is saved
//	          by the duplicate window, an idempotent consumer, a poison message
//	          that lands in the DLQ stream, and a full replay that changes
//	          nothing. What the estate relies on.
//
// With no NATS_URL / DATABASE_URL both run against an embedded broker and an
// embedded Postgres; with them, against the real ones. Every line printed is
// a measurement from the broker or the database, not a narration.
package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/jetstream"

	"github.com/chidionyema/idp/platform/messaging/cloudevent"
	"github.com/chidionyema/idp/platform/messaging/dlq"
	"github.com/chidionyema/idp/platform/messaging/inbox"
	"github.com/chidionyema/idp/platform/messaging/local"
	"github.com/chidionyema/idp/platform/messaging/outbox"
	"github.com/chidionyema/idp/platform/messaging/subject"
)

const (
	streamName  = "ORDERS_EVENTS"
	dlqStream   = "ORDERS_DLQ"
	consumerDur = "demo-orders"
)

var orderPlaced = subject.MustParse("orders.event.order.placed.v1")

// ordersStream is decision D8 and the CP3 scenario "the first stream exists
// with the locked values": file store, limits, 30 days, 15-minute duplicate
// window, deny delete and purge. Replicas 1 on the two-node pool (ADR 0012).
func ordersStream() jetstream.StreamConfig {
	return jetstream.StreamConfig{
		Name: streamName, Subjects: []string{"orders.event.>"},
		Storage: jetstream.FileStorage, Retention: jetstream.LimitsPolicy,
		MaxAge: 30 * 24 * time.Hour, Duplicates: 15 * time.Minute,
		DenyDelete: true, DenyPurge: true, Replicas: 1,
	}
}

func main() {
	if len(os.Args) != 2 || (os.Args[1] != "basic" && os.Args[1] != "advanced") {
		fmt.Fprintln(os.Stderr, "usage: demo basic|advanced")
		os.Exit(2)
	}
	if err := run(os.Args[1]); err != nil {
		fmt.Printf("RED demo %s: %v\n", os.Args[1], err)
		os.Exit(1)
	}
}

func run(mode string) error {
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Minute)
	defer cancel()
	t0 := time.Now()
	env, err := local.Start()
	if err != nil {
		return err
	}
	defer env.Stop()
	where := "cluster"
	if env.Embedded {
		where = "embedded"
	}
	fmt.Printf("broker %s %s, database %s, ready in %s\n", where, env.NATSURL, where, time.Since(t0).Round(time.Millisecond))

	if mode == "basic" {
		return basic(ctx, env)
	}
	return advanced(ctx, env)
}

func connect(url string, c local.Creds) (*nats.Conn, jetstream.JetStream, error) {
	nc, err := nats.Connect(url, nats.UserInfo(c.User, c.Pass), nats.Name("demo-"+c.User))
	if err != nil {
		return nil, nil, fmt.Errorf("connect as %s: %w", c.User, err)
	}
	js, err := jetstream.New(nc)
	if err != nil {
		return nil, nil, err
	}
	return nc, js, nil
}

// ---------------------------------------------------------------- basic

func basic(ctx context.Context, env *local.Env) error {
	nc, js, err := connect(env.NATSURL, local.Relay)
	if err != nil {
		return err
	}
	defer nc.Close()
	st, err := js.CreateOrUpdateStream(ctx, ordersStream())
	if err != nil {
		return err
	}
	info, _ := st.Info(ctx)
	fmt.Printf("stream %s subjects=%v max_age=%s duplicate_window=%s deny_delete=%v deny_purge=%v\n",
		info.Config.Name, info.Config.Subjects, info.Config.MaxAge, info.Config.Duplicates, info.Config.DenyDelete, info.Config.DenyPurge)

	payload, _ := json.Marshal(map[string]any{"order_id": uuid.NewString(), "sku": "100_ai_credits", "amount_minor": 2000, "currency": "USD"})
	ev := cloudevent.New(orderPlaced, "/orders", payload)
	ack, err := js.PublishMsg(ctx, &nats.Msg{Subject: ev.Subject.String(), Header: ev.Headers(), Data: ev.Data})
	if err != nil {
		return err
	}
	fmt.Printf("published %s seq=%d ce-id=%s trace=%s\n", ev.Subject, ack.Sequence, ev.ID, cloudevent.TraceID(ev.TraceParent))

	cn, cjs, err := connect(env.NATSURL, local.Consumer)
	if err != nil {
		return err
	}
	defer cn.Close()
	cst, err := cjs.Stream(ctx, streamName)
	if err != nil {
		return err
	}
	cons, err := cst.CreateOrUpdateConsumer(ctx, jetstream.ConsumerConfig{
		Durable: consumerDur, AckPolicy: jetstream.AckExplicitPolicy, FilterSubject: "orders.event.>",
	})
	if err != nil {
		return err
	}
	m, err := cons.Next(jetstream.FetchMaxWait(5 * time.Second))
	if err != nil {
		return fmt.Errorf("consumer got nothing in 5s: %w", err)
	}
	if err := m.DoubleAck(ctx); err != nil {
		return err
	}
	md, _ := m.Metadata()
	fmt.Printf("consumed %s by durable pull consumer %q: ce-id=%s ce-type=%s traceparent=%s delivered=%d acked=explicit\n",
		m.Subject(), consumerDur, m.Headers().Get("ce-id"), m.Headers().Get("ce-type"), m.Headers().Get("traceparent"), md.NumDelivered)
	ci, _ := cons.Info(ctx)
	fmt.Printf("consumer pending=%d ack_pending=%d redelivered=%d\n", ci.NumPending, ci.NumAckPending, ci.NumRedelivered)
	if ci.NumPending != 0 || ci.NumAckPending != 0 {
		return errors.New("consumer did not drain")
	}
	fmt.Printf("ok demo basic trace=%s\n", cloudevent.TraceID(ev.TraceParent))
	return nil
}

// ---------------------------------------------------------------- advanced

const serviceSchema = `
CREATE TABLE IF NOT EXISTS orders (id uuid PRIMARY KEY, sku text NOT NULL, amount_minor bigint NOT NULL, currency text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS order_effects (id bigserial PRIMARY KEY, order_id uuid NOT NULL, note text NOT NULL);`

func advanced(ctx context.Context, env *local.Env) error {
	db, err := pgxpool.New(ctx, env.DatabaseURL)
	if err != nil {
		return err
	}
	defer db.Close()
	if _, err := db.Exec(ctx, serviceSchema+outbox.Schema+inbox.Schema); err != nil {
		return fmt.Errorf("schema: %w", err)
	}

	// 1. The service cannot publish around the outbox (D3, enforced by credentials).
	if err := step1PermissionViolation(env); err != nil {
		return err
	}
	// 2. Three orders, three outbox rows, one transaction each; the broker is not involved.
	events, err := step2Enqueue(ctx, db)
	if err != nil {
		return err
	}
	// 3. The relay crashes after publishing the first row and before marking it; the
	//    second pass republishes; the duplicate window stores one copy.
	rn, rjs, err := connect(env.NATSURL, local.Relay)
	if err != nil {
		return err
	}
	defer rn.Close()
	if _, err := rjs.CreateOrUpdateStream(ctx, ordersStream()); err != nil {
		return err
	}
	if err := step3Relay(ctx, db, rjs, events[0].ID); err != nil {
		return err
	}
	// 4. A poison message the consumer can never process, on the same subject.
	poison := cloudevent.New(orderPlaced, "/orders", []byte(`{"poison":true}`))
	if _, err := rjs.PublishMsg(ctx, &nats.Msg{Subject: poison.Subject.String(), Header: poison.Headers(), Data: poison.Data}); err != nil {
		return err
	}
	// 5. The DLQ processor listens before the consumer gives up.
	dn, djs, err := connect(env.NATSURL, local.DLQ)
	if err != nil {
		return err
	}
	defer dn.Close()
	if _, err := djs.CreateOrUpdateStream(ctx, jetstream.StreamConfig{Name: dlqStream, Subjects: []string{"orders.dlq.>"}, Storage: jetstream.FileStorage, Replicas: 1}); err != nil {
		return err
	}
	dlqDone := make(chan string, 1)
	sub, err := dn.Subscribe(dlq.AdvisorySubject(streamName, consumerDur), func(m *nats.Msg) {
		target, err := dlq.Copy(ctx, djs, m.Data)
		if err != nil {
			dlqDone <- "RED " + err.Error()
			return
		}
		dlqDone <- target
	})
	if err != nil {
		return err
	}
	defer sub.Unsubscribe()
	// 6. The idempotent consumer: three effects, one poison terminated after max_deliver.
	applied, err := step6Consume(ctx, db, env)
	if err != nil {
		return err
	}
	if applied != 3 {
		return fmt.Errorf("consumer applied %d effects, wanted 3", applied)
	}
	select {
	case target := <-dlqDone:
		if strings.HasPrefix(target, "RED") {
			return errors.New(target)
		}
		di, _ := djs.Stream(ctx, dlqStream)
		dinfo, _ := di.Info(ctx)
		fmt.Printf("dlq: advisory MAX_DELIVERIES -> copied to %s, stream %s messages=%d\n", target, dlqStream, dinfo.State.Msgs)
		if dinfo.State.Msgs != 1 {
			return fmt.Errorf("dlq stream holds %d messages, wanted 1", dinfo.State.Msgs)
		}
	case <-time.After(15 * time.Second):
		return errors.New("no MAX_DELIVERIES advisory in 15s")
	}
	// 7. Replay everything from the start into the same handler: nothing changes (§11 test 8 shape).
	if err := step7Replay(ctx, db, env); err != nil {
		return err
	}
	fmt.Printf("ok demo advanced trace=%s\n", cloudevent.TraceID(events[0].TraceParent))
	return nil
}

func step1PermissionViolation(env *local.Env) error {
	violated := make(chan error, 1)
	nc, err := nats.Connect(env.NATSURL, nats.UserInfo(local.App.User, local.App.Pass), nats.Name("demo-app"),
		nats.ErrorHandler(func(_ *nats.Conn, _ *nats.Subscription, err error) { violated <- err }))
	if err != nil {
		return err
	}
	defer nc.Close()
	if err := nc.Publish(orderPlaced.String(), []byte(`{"around":"the outbox"}`)); err != nil {
		return err
	}
	_ = nc.Flush()
	select {
	case err := <-violated:
		if !errors.Is(err, nats.ErrPermissionViolation) {
			return fmt.Errorf("app publish: wanted a permissions violation, got %v", err)
		}
		fmt.Printf("step 1: service user %q publishing %s directly -> %v\n", local.App.User, orderPlaced, err)
	case <-time.After(5 * time.Second):
		return errors.New("step 1: the service user published around the outbox and nothing refused it")
	}
	return nil
}

func step2Enqueue(ctx context.Context, db *pgxpool.Pool) ([]cloudevent.Event, error) {
	var events []cloudevent.Event
	for i, sku := range []string{"100_ai_credits", "500_ai_credits", "pro_monthly"} {
		orderID := uuid.New()
		payload, _ := json.Marshal(map[string]any{"order_id": orderID, "sku": sku, "amount_minor": 2000 * (i + 1), "currency": "USD"})
		ev := cloudevent.New(orderPlaced, "/orders", payload)
		err := pgx.BeginFunc(ctx, db, func(tx pgx.Tx) error {
			if _, err := tx.Exec(ctx, `INSERT INTO orders (id, sku, amount_minor, currency) VALUES ($1,$2,$3,$4)`, orderID, sku, 2000*(i+1), "USD"); err != nil {
				return err
			}
			return outbox.Enqueue(ctx, tx, ev)
		})
		if err != nil {
			return nil, err
		}
		events = append(events, ev)
	}
	n, err := outbox.Unpublished(ctx, db)
	if err != nil {
		return nil, err
	}
	fmt.Printf("step 2: 3 orders committed, outbox unpublished=%d, broker connections by the service=0\n", n)
	return events, nil
}

func step3Relay(ctx context.Context, db *pgxpool.Pool, js jetstream.JetStream, crashOn uuid.UUID) error {
	crashed := false
	r := &outbox.Relay{DB: db, JS: js, CrashAfterPublish: func(id uuid.UUID) bool {
		if id == crashOn && !crashed {
			crashed = true
			return true
		}
		return false
	}}
	first, err := r.Once(ctx)
	if !errors.Is(err, outbox.ErrCrashed) {
		return fmt.Errorf("relay pass 1: wanted the staged crash, got %v", err)
	}
	fmt.Printf("step 3: relay pass 1 published %d row(s) then crashed before marking %s\n", len(first), crashOn)
	n, _ := outbox.Unpublished(ctx, db)
	second, err := r.Once(ctx)
	if err != nil {
		return err
	}
	dups := 0
	for _, s := range second {
		if s.Duplicate {
			dups++
		}
	}
	st, _ := js.Stream(ctx, streamName)
	info, _ := st.Info(ctx)
	left, _ := outbox.Unpublished(ctx, db)
	fmt.Printf("step 3: relay pass 2 (unpublished before=%d) published %d, broker answered duplicate=%d, stream messages=%d, unpublished after=%d\n",
		n, len(second), dups, info.State.Msgs, left)
	if dups != 1 || info.State.Msgs != 3 || left != 0 {
		return fmt.Errorf("at-least-once did not end in exactly-once storage (duplicates=%d, messages=%d, unpublished=%d)", dups, info.State.Msgs, left)
	}
	return nil
}

// handle is the one business handler: grant credits for the order in the
// payload, exactly once per event. A payload with no sku cannot be handled and
// the error is what makes a message poison; the same handler on a replay makes
// the same decision.
func handle(ctx context.Context, db *pgxpool.Pool, m jetstream.Msg, note string) (applied bool, err error) {
	id, err := uuid.Parse(m.Headers().Get("ce-id"))
	if err != nil {
		return false, fmt.Errorf("ce-id: %w", err)
	}
	var order struct {
		OrderID uuid.UUID `json:"order_id"`
		SKU     string    `json:"sku"`
	}
	if err := json.Unmarshal(m.Data(), &order); err != nil || order.SKU == "" {
		return false, fmt.Errorf("event %s: cannot grant credits, payload names no sku", id)
	}
	return inbox.Process(ctx, db, consumerDur, id, func(ctx context.Context, tx pgx.Tx) error {
		_, err := tx.Exec(ctx, `INSERT INTO order_effects (order_id, note) VALUES ($1, $2)`, order.OrderID, note)
		return err
	})
}

func step6Consume(ctx context.Context, db *pgxpool.Pool, env *local.Env) (int, error) {
	cn, cjs, err := connect(env.NATSURL, local.Consumer)
	if err != nil {
		return 0, err
	}
	defer cn.Close()
	st, err := cjs.Stream(ctx, streamName)
	if err != nil {
		return 0, err
	}
	cons, err := st.CreateOrUpdateConsumer(ctx, jetstream.ConsumerConfig{
		Durable: consumerDur, AckPolicy: jetstream.AckExplicitPolicy, FilterSubject: "orders.event.>",
		MaxDeliver: 3, AckWait: 2 * time.Second, BackOff: []time.Duration{200 * time.Millisecond, 400 * time.Millisecond},
	})
	if err != nil {
		return 0, err
	}
	applied, poisonSeen := 0, 0
	deadline := time.Now().Add(20 * time.Second)
	for time.Now().Before(deadline) && (applied < 3 || poisonSeen < 3) {
		m, err := cons.Next(jetstream.FetchMaxWait(2 * time.Second))
		if err != nil {
			continue
		}
		md, _ := m.Metadata()
		did, err := handle(ctx, db, m, "credits granted")
		if err != nil {
			poisonSeen++
			fmt.Printf("step 6: delivery %d of 3 failed (%v) -> nak\n", md.NumDelivered, err)
			_ = m.Nak()
			continue
		}
		if did {
			applied++
		}
		_ = m.DoubleAck(ctx)
	}
	// The server raises MAX_DELIVERIES when it next tries to redeliver, which is
	// the next pull: one more fetch that returns nothing is what fires it.
	if _, err := cons.Next(jetstream.FetchMaxWait(1500 * time.Millisecond)); err == nil {
		return applied, errors.New("step 6: the poison message was delivered a fourth time")
	}
	var effects int
	_ = db.QueryRow(ctx, `SELECT count(*) FROM order_effects`).Scan(&effects)
	fmt.Printf("step 6: consumer %q applied=%d effects_in_db=%d poison_deliveries=%d\n", consumerDur, applied, effects, poisonSeen)
	return effects, nil
}

func step7Replay(ctx context.Context, db *pgxpool.Pool, env *local.Env) error {
	cn, cjs, err := connect(env.NATSURL, local.Consumer)
	if err != nil {
		return err
	}
	defer cn.Close()
	st, err := cjs.Stream(ctx, streamName)
	if err != nil {
		return err
	}
	replay, err := st.CreateOrUpdateConsumer(ctx, jetstream.ConsumerConfig{
		Name: "demo-replay", AckPolicy: jetstream.AckExplicitPolicy, DeliverPolicy: jetstream.DeliverAllPolicy, FilterSubject: "orders.event.>",
		InactiveThreshold: time.Minute,
	})
	if err != nil {
		return err
	}
	delivered, applied, failed := 0, 0, 0
	for delivered < 4 {
		m, err := replay.Next(jetstream.FetchMaxWait(3 * time.Second))
		if err != nil {
			break
		}
		delivered++
		did, err := handle(ctx, db, m, "replayed")
		if err != nil {
			failed++
			_ = m.Term() // a replay does not retry poison; it is already in the DLQ
			continue
		}
		if did {
			applied++
		}
		_ = m.DoubleAck(ctx)
	}
	var effects int
	_ = db.QueryRow(ctx, `SELECT count(*) FROM order_effects`).Scan(&effects)
	fmt.Printf("step 7: replay from the start delivered=%d applied=%d failed_again=%d effects_in_db=%d\n", delivered, applied, failed, effects)
	if delivered != 4 || applied != 0 || failed != 1 || effects != 3 {
		return fmt.Errorf("replay changed something (delivered=%d applied=%d failed=%d effects=%d)", delivered, applied, failed, effects)
	}
	return nil
}
