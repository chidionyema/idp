# FleetView Voice Go SDK

A fully typed Go SDK for FleetView voice events over NATS.

## Installation

```bash
go get github.com/fleetview/voice-sdk-go
```

## Quick Start

```go
package main

import (
    "fmt"
    "os"
    "os/signal"
    "syscall"

    voice "github.com/fleetview/voice-sdk-go"
)

func main() {
    // Create a new client
    client := voice.NewClient(voice.Config{
        Token:   os.Getenv("API_TOKEN"),
        NatsURL: "nats://localhost:4222",
        Name:    "my-voice-client",
    })

    // Register event handlers before connecting
    client.On("steer", func(event voice.Event) {
        fmt.Printf("%s commanded: %s\n", event.Author, event.Transcript)
    })

    client.On("done", func(event voice.Event) {
        fmt.Printf("Task completed by %s\n", event.Author)
    })

    // Connect to NATS
    if err := client.Connect(); err != nil {
        panic(err)
    }
    defer client.Disconnect()

    // Emit an event
    err := client.Emit("done", voice.Event{
        Transcript: "Task completed successfully",
        Confidence: 0.95,
        Author:     "my-service",
    })
    if err != nil {
        fmt.Printf("Failed to emit: %v\n", err)
    }

    // Wait for interrupt signal
    sigCh := make(chan os.Signal, 1)
    signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
    <-sigCh

    fmt.Println("Shutting down...")
}
```

## Configuration

### Config Struct

```go
type Config struct {
    Token            string        // Authentication token for NATS
    NatsURL          string        // NATS server URL (required)
    Subject          string        // Subject prefix (default: "voice.events")
    ReconnectWait    time.Duration // Initial reconnect delay (default: 1s)
    MaxReconnectWait time.Duration // Max reconnect delay (default: 30s)
    MaxReconnects    int           // Max reconnect attempts (-1 = unlimited)
    Name             string        // Client name for identification
    Author           string        // Default author for emitted events
}
```

### Functional Options

```go
client := voice.NewClient(voice.Config{
    NatsURL: "nats://localhost:4222",
},
    voice.WithToken("my-token"),
    voice.WithSubject("custom.events"),
    voice.WithName("my-client"),
    voice.WithAuthor("my-service"),
    voice.WithReconnectWait(2*time.Second),
    voice.WithMaxReconnectWait(60*time.Second),
    voice.WithMaxReconnects(10),
)
```

## Event Type

```go
type Event struct {
    ID         string    `json:"id"`
    Type       string    `json:"type"`
    Action     string    `json:"action"`
    Target     *string   `json:"target,omitempty"`
    Env        *string   `json:"env,omitempty"`
    Confidence float64   `json:"confidence"`
    Transcript string    `json:"transcript"`
    Author     string    `json:"author"`
    Timestamp  time.Time `json:"timestamp"`
}
```

## API Reference

### Creating a Client

```go
client := voice.NewClient(voice.Config{
    Token:   os.Getenv("API_TOKEN"),
    NatsURL: "nats://localhost:4222",
})
```

### Connecting

```go
// Simple connect
err := client.Connect()

// With context (for timeout/cancellation)
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()
err := client.ConnectWithContext(ctx)
```

### Registering Handlers

Handlers are goroutine-safe and run concurrently:

```go
client.On("steer", func(event voice.Event) {
    fmt.Printf("%s commanded: %s\n", event.Author, event.Transcript)
})

// Multiple handlers for the same action
client.On("steer", func(event voice.Event) {
    log.Printf("Received steer command with confidence: %.2f", event.Confidence)
})
```

### Emitting Events

```go
// Simple emit
err := client.Emit("done", voice.Event{
    Transcript: "Task completed",
    Confidence: 0.95,
})

// With context
ctx, cancel := context.WithTimeout(context.Background(), time.Second)
defer cancel()
err := client.EmitWithContext(ctx, "done", voice.Event{
    Transcript: "Task completed",
    Confidence: 0.95,
})
```

### Checking Connection Status

```go
if client.IsConnected() {
    fmt.Println("Connected to NATS")
}
```

### Getting Statistics

```go
stats := client.Stats()
fmt.Printf("Messages sent: %d, received: %d\n", stats.OutMsgs, stats.InMsgs)
```

### Disconnecting

```go
client.Disconnect()
```

## Features

- **Goroutine-safe**: All client methods are thread-safe
- **Connection pooling**: Reuses the NATS connection for efficiency
- **Exponential backoff**: Automatic reconnection with backoff (1s, 2s, 4s, 8s... max 30s)
- **Context support**: Full context.Context support for cancellation and timeouts
- **Multiple handlers**: Register multiple handlers for the same event action
- **Flexible configuration**: Both struct and functional option patterns supported

## Error Handling

The SDK defines the following errors:

```go
voice.ErrNotConnected     // Client is not connected
voice.ErrAlreadyConnected // Client is already connected
voice.ErrEmptyNatsURL     // NATS URL is required
voice.ErrEmptyAction      // Action cannot be empty when emitting
```

## License

MIT
