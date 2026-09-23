package voice

import (
	"time"
)

// Config holds the configuration for a voice Client.
type Config struct {
	// Token is the authentication token for the NATS connection.
	Token string

	// NatsURL is the NATS server URL (e.g., "nats://localhost:4222").
	NatsURL string

	// Subject is the NATS subject prefix for voice events.
	// Defaults to "voice.events" if not set.
	Subject string

	// ReconnectWait is the initial delay before reconnecting.
	// Defaults to 1 second if not set.
	ReconnectWait time.Duration

	// MaxReconnectWait is the maximum delay between reconnection attempts.
	// Defaults to 30 seconds if not set.
	MaxReconnectWait time.Duration

	// MaxReconnects is the maximum number of reconnection attempts.
	// Set to -1 for unlimited. Defaults to -1 if not set.
	MaxReconnects int

	// Name is an optional client name for identification.
	Name string

	// Author is the default author for emitted events.
	// Defaults to Name if not set.
	Author string
}

// Option is a functional option for configuring a Client.
type Option func(*Config)

// WithToken sets the authentication token.
func WithToken(token string) Option {
	return func(c *Config) {
		c.Token = token
	}
}

// WithNatsURL sets the NATS server URL.
func WithNatsURL(url string) Option {
	return func(c *Config) {
		c.NatsURL = url
	}
}

// WithSubject sets the NATS subject prefix.
func WithSubject(subject string) Option {
	return func(c *Config) {
		c.Subject = subject
	}
}

// WithReconnectWait sets the initial reconnect delay.
func WithReconnectWait(d time.Duration) Option {
	return func(c *Config) {
		c.ReconnectWait = d
	}
}

// WithMaxReconnectWait sets the maximum reconnect delay.
func WithMaxReconnectWait(d time.Duration) Option {
	return func(c *Config) {
		c.MaxReconnectWait = d
	}
}

// WithMaxReconnects sets the maximum number of reconnection attempts.
func WithMaxReconnects(n int) Option {
	return func(c *Config) {
		c.MaxReconnects = n
	}
}

// WithName sets the client name.
func WithName(name string) Option {
	return func(c *Config) {
		c.Name = name
	}
}

// WithAuthor sets the default author for emitted events.
func WithAuthor(author string) Option {
	return func(c *Config) {
		c.Author = author
	}
}

// applyDefaults fills in default values for unset Config fields.
func (c *Config) applyDefaults() {
	if c.Subject == "" {
		c.Subject = "voice.events"
	}
	if c.ReconnectWait == 0 {
		c.ReconnectWait = time.Second
	}
	if c.MaxReconnectWait == 0 {
		c.MaxReconnectWait = 30 * time.Second
	}
	if c.MaxReconnects == 0 {
		c.MaxReconnects = -1 // unlimited
	}
	if c.Author == "" && c.Name != "" {
		c.Author = c.Name
	}
}
