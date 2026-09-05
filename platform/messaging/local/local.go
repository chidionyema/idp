// Package local gives the demo a real broker and a real database with nothing
// to install: nats-server embedded in the process (the same binary the chart
// on platform/event-bus runs, same version) and an embedded Postgres. Set
// NATS_URL and DATABASE_URL and none of this runs: the demo then speaks to
// the cluster bus (CP2) and the service's own database.
//
// The four NATS users are decision D3 and D4 in miniature: a service (app)
// cannot publish on orders.>, the relay is the only one that can publish
// events, the DLQ processor is the only one that can publish dlq subjects,
// and the consumer can only read.
package local

import (
	"fmt"
	"io"
	"net"
	"os"
	"path/filepath"
	"time"

	embeddedpostgres "github.com/fergusstrange/embedded-postgres"
	"github.com/nats-io/nats-server/v2/server"
)

// Creds is one NATS user of the demo.
type Creds struct{ User, Pass string }

// Users are the four roles. Passwords are demo-only and local-only: on the
// cluster these are nsc-issued JWTs from the vault (D4).
var (
	App      = Creds{"app", "app-local-only"}
	Relay    = Creds{"relay", "relay-local-only"}
	Consumer = Creds{"consumer", "consumer-local-only"}
	DLQ      = Creds{"dlq", "dlq-local-only"}
)

// Env is what the demo runs against.
type Env struct {
	NATSURL     string
	DatabaseURL string
	Embedded    bool
	stop        []func()
}

// Start returns the environment named by NATS_URL / DATABASE_URL, or an embedded one.
func Start() (*Env, error) {
	if u, d := os.Getenv("NATS_URL"), os.Getenv("DATABASE_URL"); u != "" && d != "" {
		return &Env{NATSURL: u, DatabaseURL: d}, nil
	}
	dir, err := os.MkdirTemp("", "messaging-demo-")
	if err != nil {
		return nil, err
	}
	e := &Env{Embedded: true}
	e.stop = append(e.stop, func() { _ = os.RemoveAll(dir) })

	ns, err := server.NewServer(&server.Options{
		Host: "127.0.0.1", Port: -1, JetStream: true, StoreDir: filepath.Join(dir, "js"),
		NoSigs: true, NoLog: true,
		Users: []*server.User{
			{Username: App.User, Password: App.Pass, Permissions: &server.Permissions{
				Publish:   &server.SubjectPermission{Deny: []string{"orders.>", "$JS.API.>"}},
				Subscribe: &server.SubjectPermission{Allow: []string{"_INBOX.>"}},
			}},
			{Username: Relay.User, Password: Relay.Pass, Permissions: &server.Permissions{
				Publish:   &server.SubjectPermission{Allow: []string{"orders.event.>", "$JS.API.>"}},
				Subscribe: &server.SubjectPermission{Allow: []string{"_INBOX.>"}},
			}},
			{Username: Consumer.User, Password: Consumer.Pass, Permissions: &server.Permissions{
				Publish:   &server.SubjectPermission{Allow: []string{"$JS.API.>", "$JS.ACK.>"}},
				Subscribe: &server.SubjectPermission{Allow: []string{"_INBOX.>", "orders.event.>"}},
			}},
			{Username: DLQ.User, Password: DLQ.Pass, Permissions: &server.Permissions{
				Publish:   &server.SubjectPermission{Allow: []string{"orders.dlq.>", "$JS.API.>"}},
				Subscribe: &server.SubjectPermission{Allow: []string{"_INBOX.>", "$JS.EVENT.ADVISORY.>"}},
			}},
		},
	})
	if err != nil {
		e.Stop()
		return nil, err
	}
	go ns.Start()
	if !ns.ReadyForConnections(10 * time.Second) {
		e.Stop()
		return nil, fmt.Errorf("embedded nats-server not ready in 10s")
	}
	e.stop = append(e.stop, ns.Shutdown)
	e.NATSURL = ns.ClientURL()

	port, err := freePort()
	if err != nil {
		e.Stop()
		return nil, err
	}
	// The Postgres binaries are fetched once and unpacked once, into the user's
	// cache directory (never a literal path, LAW 46); the data directory is fresh
	// per run so a demo never sees a previous demo's rows.
	cache, err := os.UserCacheDir()
	if err != nil {
		cache = dir
	}
	pg := embeddedpostgres.NewDatabase(embeddedpostgres.DefaultConfig().
		Version(embeddedpostgres.V16).Port(uint32(port)).
		BinariesPath(filepath.Join(cache, "idp-messaging-demo", "postgres-16")).
		RuntimePath(filepath.Join(dir, "pg")).DataPath(filepath.Join(dir, "pg", "data")).
		Logger(io.Discard))
	if err := pg.Start(); err != nil {
		e.Stop()
		return nil, fmt.Errorf("embedded postgres: %w", err)
	}
	e.stop = append(e.stop, func() { _ = pg.Stop() })
	e.DatabaseURL = fmt.Sprintf("postgres://postgres:postgres@127.0.0.1:%d/postgres?sslmode=disable", port)
	return e, nil
}

// Stop tears down in reverse order.
func (e *Env) Stop() {
	for i := len(e.stop) - 1; i >= 0; i-- {
		e.stop[i]()
	}
	e.stop = nil
}

func freePort() (int, error) {
	l, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return 0, err
	}
	defer l.Close()
	return l.Addr().(*net.TCPAddr).Port, nil
}
