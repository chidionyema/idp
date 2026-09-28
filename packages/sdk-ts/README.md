# @fleetview/voice-sdk

TypeScript SDK for FleetView voice events over NATS WebSocket.

## Installation

```bash
npm install @fleetview/voice-sdk
```

## Quick Start

```typescript
import { VoiceEventClient, VoiceEvent } from '@fleetview/voice-sdk';

const client = new VoiceEventClient({
  token: 'your-auth-token',
  natsUrl: 'wss://nats.example.com:443',
});

// Register event handlers
client.on('steer', (event: VoiceEvent) => {
  console.log('Steer command received:', event.action);
  console.log('Target:', event.target);
});

client.on('speak', (event: VoiceEvent) => {
  console.log('Speak event:', event.transcript);
});

client.on('done', (event: VoiceEvent) => {
  console.log('Action completed:', event.action);
});

// Connect and emit events
await client.connect();

await client.emit('done', {
  action: 'deploy',
  target: 'production',
  confidence: 0.95,
  transcript: 'Deploy to production',
  author: 'user@example.com',
});

// Disconnect when done
await client.disconnect();
```

## API Reference

### VoiceEventClient

Main client class for interacting with voice events.

#### Constructor

```typescript
const client = new VoiceEventClient({
  token: string,           // Authentication token for NATS
  natsUrl: string,         // NATS WebSocket URL
  subjectPrefix?: string,  // Subject prefix (default: 'voice')
  maxReconnectAttempts?: number, // Max reconnect attempts (default: unlimited)
});
```

#### Methods

##### `connect(): Promise<void>`

Connect to the NATS server.

```typescript
await client.connect();
```

##### `disconnect(): Promise<void>`

Disconnect from the NATS server.

```typescript
await client.disconnect();
```

##### `on<T>(type: VoiceEventType, handler: VoiceEventHandler<T>): () => void`

Register an event handler. Returns an unsubscribe function.

```typescript
const unsubscribe = client.on('steer', (event) => {
  console.log(event.action);
});

// Later, unsubscribe
unsubscribe();
```

##### `off<T>(type: VoiceEventType, handler: VoiceEventHandler<T>): void`

Remove an event handler.

```typescript
client.off('steer', myHandler);
```

##### `once<T>(type: VoiceEventType, handler: VoiceEventHandler<T>): void`

Register a one-time event handler that is automatically removed after being called.

```typescript
client.once('done', (event) => {
  console.log('First done event:', event);
});
```

##### `emit<T>(type: VoiceEventType, payload: VoiceEventPayload): Promise<VoiceEvent>`

Emit a voice event. Returns the complete event with generated id and timestamp.

```typescript
const event = await client.emit('steer', {
  action: 'navigate',
  target: '/dashboard',
  confidence: 0.92,
  transcript: 'Go to dashboard',
  author: 'user@example.com',
});

console.log('Event ID:', event.id);
console.log('Timestamp:', event.timestamp);
```

#### Properties

##### `connectionState: ConnectionState`

Current connection state: `'disconnected'`, `'connecting'`, `'connected'`, or `'reconnecting'`.

##### `isConnected: boolean`

Whether the client is currently connected.

### Types

#### VoiceEvent

```typescript
interface VoiceEvent {
  id: string;           // Unique event identifier
  type: 'steer' | 'done' | 'speak';
  action: string;       // Action to perform
  target?: string;      // Optional target resource
  env?: string;         // Optional environment context
  confidence: number;   // Speech recognition confidence (0-1)
  transcript: string;   // Original transcript
  author: string;       // Event originator
  timestamp: Date;      // Event creation time
}
```

#### VoiceEventPayload

Same as `VoiceEvent` but without `id`, `timestamp`, and `type` (these are auto-generated or specified separately).

## Features

### Type-Safe Event Handlers

Handlers are fully typed based on the event type:

```typescript
client.on('steer', (event) => {
  // event.type is typed as 'steer'
  console.log(event.type); // TypeScript knows this is 'steer'
});
```

### Automatic Reconnection

The SDK automatically reconnects with exponential backoff:

- Initial delay: 1 second
- Doubles on each attempt: 1s, 2s, 4s, 8s...
- Maximum delay: 30 seconds

```typescript
const client = new VoiceEventClient({
  token: 'token',
  natsUrl: 'wss://nats.example.com',
  maxReconnectAttempts: 10, // Limit reconnection attempts
});
```

### Connection State Monitoring

```typescript
console.log(client.connectionState); // 'disconnected' | 'connecting' | 'connected' | 'reconnecting'
console.log(client.isConnected);     // true | false
```

## Error Handling

```typescript
try {
  await client.connect();
} catch (error) {
  console.error('Failed to connect:', error);
}

// Event handler errors are logged but don't stop processing
client.on('steer', (event) => {
  throw new Error('Handler error'); // Logged, doesn't crash
});
```

## License

MIT
