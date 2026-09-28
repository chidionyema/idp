package voice

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"sync"
	"time"

	"github.com/nats-io/nats.go"
)

// Common errors returned by the Client.
var (
	ErrNotConnected    = errors.New("voice: client not connected")
	ErrAlreadyConnected = errors.New("voice: client already connected")
	ErrEmptyNatsURL    = errors.New("voice: NATS URL is required")
	ErrEmptyAction     = errors.New("voice: action cannot be empty")
)

// Client is a thread-safe voice event client over NATS.
type Client struct {
	config   Config
	conn     *nats.Conn
	handlers map[string][]EventHandler
	subs     []*nats.Subscription

	mu        sync.RWMutex
	connected bool

	ctx    context.Context
	cancel context.CancelFunc
}

// NewClient creates a new voice Client with the given configuration.
func NewClient(cfg Config, opts ...Option) *Client {
	for _, opt := range opts {
		opt(&cfg)
	}
	cfg.applyDefaults()

	ctx, cancel := context.WithCancel(context.Background())

	return &Client{
		config:   cfg,
		handlers: make(map[string][]EventHandler),
		ctx:      ctx,
		cancel:   cancel,
	}
}

// Connect establishes a connection to the NATS server.
// It returns an error if already connected or if the connection fails.
func (c *Client) Connect() error {
	return c.ConnectWithContext(context.Background())
}

// ConnectWithContext establishes a connection to the NATS server with context support.
func (c *Client) ConnectWithContext(ctx context.Context) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if c.connected {
		return ErrAlreadyConnected
	}

	if c.config.NatsURL == "" {
		return ErrEmptyNatsURL
	}

	opts := []nats.Option{
		nats.ReconnectWait(c.config.ReconnectWait),
		nats.MaxReconnects(c.config.MaxReconnects),
		nats.DisconnectErrHandler(c.handleDisconnect),
		nats.ReconnectHandler(c.handleReconnect),
		nats.ClosedHandler(c.handleClosed),
		nats.CustomReconnectDelay(c.reconnectDelay),
	}

	if c.config.Token != "" {
		opts = append(opts, nats.Token(c.config.Token))
	}

	if c.config.Name != "" {
		opts = append(opts, nats.Name(c.config.Name))
	}

	// Create connection with context timeout if set
	var conn *nats.Conn
	var err error

	done := make(chan struct{})
	go func() {
		conn, err = nats.Connect(c.config.NatsURL, opts...)
		close(done)
	}()

	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-done:
		if err != nil {
			return fmt.Errorf("voice: failed to connect to NATS: %w", err)
		}
	}

	c.conn = conn
	c.connected = true

	// Subscribe to registered handlers
	if err := c.subscribeAll(); err != nil {
		c.conn.Close()
		c.conn = nil
		c.connected = false
		return fmt.Errorf("voice: failed to subscribe: %w", err)
	}

	return nil
}

// reconnectDelay implements exponential backoff with jitter.
func (c *Client) reconnectDelay(attempts int) time.Duration {
	// Exponential backoff: 1s, 2s, 4s, 8s, ... up to max
	delay := c.config.ReconnectWait * (1 << uint(attempts))
	if delay > c.config.MaxReconnectWait {
		delay = c.config.MaxReconnectWait
	}
	return delay
}

// handleDisconnect is called when the connection is lost.
func (c *Client) handleDisconnect(conn *nats.Conn, err error) {
	// Connection lost, NATS will attempt to reconnect
}

// handleReconnect is called when the connection is re-established.
func (c *Client) handleReconnect(conn *nats.Conn) {
	// Connection restored
}

// handleClosed is called when the connection is permanently closed.
func (c *Client) handleClosed(conn *nats.Conn) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.connected = false
}

// subscribeAll creates subscriptions for all registered handlers.
func (c *Client) subscribeAll() error {
	for action := range c.handlers {
		if err := c.subscribeAction(action); err != nil {
			return err
		}
	}
	return nil
}

// subscribeAction creates a subscription for a specific action.
func (c *Client) subscribeAction(action string) error {
	subject := fmt.Sprintf("%s.%s", c.config.Subject, action)
	sub, err := c.conn.Subscribe(subject, func(msg *nats.Msg) {
		var event Event
		if err := json.Unmarshal(msg.Data, &event); err != nil {
			return // Silently drop malformed messages
		}

		c.mu.RLock()
		handlers := c.handlers[action]
		c.mu.RUnlock()

		for _, h := range handlers {
			// Run handlers in goroutines for non-blocking execution
			go h(event)
		}
	})
	if err != nil {
		return err
	}
	c.subs = append(c.subs, sub)
	return nil
}

// On registers a handler for events with the given action.
// Handlers are invoked concurrently in separate goroutines.
// Can be called before or after Connect().
func (c *Client) On(action string, handler EventHandler) {
	c.mu.Lock()
	defer c.mu.Unlock()

	c.handlers[action] = append(c.handlers[action], handler)

	// If already connected, subscribe immediately
	if c.connected && c.conn != nil {
		// Check if we already have a subscription for this action
		subject := fmt.Sprintf("%s.%s", c.config.Subject, action)
		for _, sub := range c.subs {
			if sub.Subject == subject {
				return // Already subscribed
			}
		}
		// Create new subscription
		_ = c.subscribeAction(action)
	}
}

// Emit publishes an event with the given action and payload.
// The payload will be merged into a new Event.
func (c *Client) Emit(action string, payload Event) error {
	return c.EmitWithContext(context.Background(), action, payload)
}

// EmitWithContext publishes an event with context support.
func (c *Client) EmitWithContext(ctx context.Context, action string, payload Event) error {
	c.mu.RLock()
	connected := c.connected
	conn := c.conn
	c.mu.RUnlock()

	if !connected || conn == nil {
		return ErrNotConnected
	}

	if action == "" {
		return ErrEmptyAction
	}

	// Set defaults
	if payload.ID == "" {
		payload.ID = generateID()
	}
	if payload.Action == "" {
		payload.Action = action
	}
	if payload.Timestamp.IsZero() {
		payload.Timestamp = time.Now().UTC()
	}
	if payload.Author == "" && c.config.Author != "" {
		payload.Author = c.config.Author
	}

	data, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("voice: failed to marshal event: %w", err)
	}

	subject := fmt.Sprintf("%s.%s", c.config.Subject, action)

	// Check context before publishing
	select {
	case <-ctx.Done():
		return ctx.Err()
	default:
	}

	if err := conn.Publish(subject, data); err != nil {
		return fmt.Errorf("voice: failed to publish event: %w", err)
	}

	return conn.Flush()
}

// Disconnect closes the NATS connection.
func (c *Client) Disconnect() {
	c.mu.Lock()
	defer c.mu.Unlock()

	c.cancel()

	// Unsubscribe from all subscriptions
	for _, sub := range c.subs {
		_ = sub.Unsubscribe()
	}
	c.subs = nil

	if c.conn != nil {
		c.conn.Close()
		c.conn = nil
	}

	c.connected = false
}

// IsConnected returns true if the client is currently connected.
func (c *Client) IsConnected() bool {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.connected && c.conn != nil && c.conn.IsConnected()
}

// Stats returns connection statistics.
func (c *Client) Stats() nats.Statistics {
	c.mu.RLock()
	defer c.mu.RUnlock()
	if c.conn == nil {
		return nats.Statistics{}
	}
	return c.conn.Stats()
}
