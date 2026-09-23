import { connect, NatsConnection, Subscription, StringCodec } from 'nats.ws';
import type {
  VoiceEvent,
  VoiceEventType,
  VoiceEventWire,
  VoiceEventClientOptions,
  VoiceEventHandler,
  VoiceEventPayload,
  ConnectionState,
} from './types.js';

/**
 * Generate a unique event ID.
 */
function generateEventId(): string {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).substring(2, 10);
  return `${timestamp}-${random}`;
}

/**
 * Calculate exponential backoff delay.
 * @param attempt - Current attempt number (0-indexed)
 * @param maxDelay - Maximum delay in milliseconds
 * @returns Delay in milliseconds
 */
function calculateBackoff(attempt: number, maxDelay: number = 30000): number {
  const baseDelay = 1000; // 1 second
  const delay = baseDelay * Math.pow(2, attempt);
  return Math.min(delay, maxDelay);
}

/**
 * Parse wire format to VoiceEvent.
 */
function parseVoiceEvent(wire: VoiceEventWire): VoiceEvent {
  return {
    ...wire,
    timestamp: new Date(wire.timestamp),
  };
}

/**
 * Serialize VoiceEvent to wire format.
 */
function serializeVoiceEvent(event: VoiceEvent): VoiceEventWire {
  return {
    ...event,
    timestamp: event.timestamp.toISOString(),
  };
}

/**
 * VoiceEventClient provides a type-safe interface for publishing and
 * subscribing to voice events over NATS WebSocket.
 *
 * Features:
 * - Type-safe event handlers via generics
 * - Automatic reconnection with exponential backoff
 * - Connection pooling via NATS connection reuse
 * - Async/await patterns throughout
 *
 * @example
 * ```typescript
 * const client = new VoiceEventClient({
 *   token: 'my-auth-token',
 *   natsUrl: 'wss://nats.example.com:443',
 * });
 *
 * client.on('steer', (event) => {
 *   console.log('Steer event:', event.action);
 * });
 *
 * await client.connect();
 * await client.emit('done', { action: 'complete', ... });
 * await client.disconnect();
 * ```
 */
export class VoiceEventClient {
  private readonly options: Required<VoiceEventClientOptions>;
  private connection: NatsConnection | null = null;
  private subscriptions: Map<VoiceEventType, Subscription> = new Map();
  private handlers: Map<VoiceEventType, Set<VoiceEventHandler>> = new Map();
  private state: ConnectionState = 'disconnected';
  private reconnectAttempt = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private readonly sc = StringCodec();

  constructor(options: VoiceEventClientOptions) {
    this.options = {
      subjectPrefix: 'voice',
      maxReconnectAttempts: Infinity,
      ...options,
    };

    // Initialize handler sets for each event type
    for (const type of ['steer', 'done', 'speak'] as const) {
      this.handlers.set(type, new Set());
    }
  }

  /**
   * Get the current connection state.
   */
  get connectionState(): ConnectionState {
    return this.state;
  }

  /**
   * Check if the client is connected.
   */
  get isConnected(): boolean {
    return this.state === 'connected';
  }

  /**
   * Register an event handler for a specific event type.
   * @param type - The event type to listen for
   * @param handler - The handler function to call when events arrive
   * @returns A function to unregister the handler
   */
  on<T extends VoiceEventType>(
    type: T,
    handler: VoiceEventHandler<T>
  ): () => void {
    const handlers = this.handlers.get(type);
    if (handlers) {
      handlers.add(handler as VoiceEventHandler);
    }

    // Return unsubscribe function
    return () => {
      this.off(type, handler);
    };
  }

  /**
   * Remove an event handler.
   * @param type - The event type
   * @param handler - The handler to remove
   */
  off<T extends VoiceEventType>(
    type: T,
    handler: VoiceEventHandler<T>
  ): void {
    const handlers = this.handlers.get(type);
    if (handlers) {
      handlers.delete(handler as VoiceEventHandler);
    }
  }

  /**
   * Register a one-time event handler.
   * @param type - The event type to listen for
   * @param handler - The handler function (called once)
   */
  once<T extends VoiceEventType>(
    type: T,
    handler: VoiceEventHandler<T>
  ): void {
    const wrappedHandler: VoiceEventHandler<T> = (event) => {
      this.off(type, wrappedHandler);
      return handler(event);
    };
    this.on(type, wrappedHandler);
  }

  /**
   * Emit a voice event.
   * @param type - The event type
   * @param payload - The event payload (id and timestamp are auto-generated)
   * @throws Error if not connected
   */
  async emit<T extends VoiceEventType>(
    type: T,
    payload: VoiceEventPayload
  ): Promise<VoiceEvent & { type: T }> {
    if (!this.connection) {
      throw new Error('Not connected to NATS');
    }

    const event: VoiceEvent = {
      id: generateEventId(),
      type,
      timestamp: new Date(),
      ...payload,
    };

    const subject = this.getSubject(type);
    const data = this.sc.encode(JSON.stringify(serializeVoiceEvent(event)));

    this.connection.publish(subject, data);
    await this.connection.flush();

    return event as VoiceEvent & { type: T };
  }

  /**
   * Connect to the NATS server.
   * @throws Error if connection fails after all retry attempts
   */
  async connect(): Promise<void> {
    if (this.state === 'connected' || this.state === 'connecting') {
      return;
    }

    this.state = 'connecting';
    this.reconnectAttempt = 0;

    await this.establishConnection();
  }

  /**
   * Disconnect from the NATS server.
   */
  async disconnect(): Promise<void> {
    this.clearReconnectTimer();

    // Unsubscribe from all subscriptions
    for (const subscription of this.subscriptions.values()) {
      subscription.unsubscribe();
    }
    this.subscriptions.clear();

    // Close connection
    if (this.connection) {
      await this.connection.drain();
      this.connection = null;
    }

    this.state = 'disconnected';
  }

  /**
   * Get the NATS subject for an event type.
   */
  private getSubject(type: VoiceEventType): string {
    return `${this.options.subjectPrefix}.${type}`;
  }

  /**
   * Establish a connection to NATS.
   */
  private async establishConnection(): Promise<void> {
    try {
      this.connection = await connect({
        servers: this.options.natsUrl,
        token: this.options.token,
        reconnect: false, // We handle reconnection ourselves for exponential backoff
      });

      this.state = 'connected';
      this.reconnectAttempt = 0;

      // Set up subscriptions for all event types with registered handlers
      await this.setupSubscriptions();

      // Set up connection close handler for reconnection
      this.monitorConnection();
    } catch (error) {
      await this.handleConnectionError(error);
    }
  }

  /**
   * Set up subscriptions for all event types.
   */
  private async setupSubscriptions(): Promise<void> {
    if (!this.connection) return;

    for (const type of ['steer', 'done', 'speak'] as const) {
      const subject = this.getSubject(type);
      const subscription = this.connection.subscribe(subject);
      this.subscriptions.set(type, subscription);

      // Process messages asynchronously
      this.processSubscription(type, subscription);
    }
  }

  /**
   * Process messages from a subscription.
   */
  private async processSubscription(
    type: VoiceEventType,
    subscription: Subscription
  ): Promise<void> {
    for await (const msg of subscription) {
      try {
        const wireEvent: VoiceEventWire = JSON.parse(
          this.sc.decode(msg.data)
        ) as VoiceEventWire;
        const event = parseVoiceEvent(wireEvent);

        // Call all registered handlers
        const handlers = this.handlers.get(type);
        if (handlers) {
          for (const handler of handlers) {
            try {
              await handler(event);
            } catch (handlerError) {
              // Log handler errors but don't stop processing
              console.error(
                `Error in ${type} event handler:`,
                handlerError
              );
            }
          }
        }
      } catch (parseError) {
        console.error('Error parsing voice event:', parseError);
      }
    }
  }

  /**
   * Monitor the connection for closure and trigger reconnection.
   */
  private monitorConnection(): void {
    if (!this.connection) return;

    (async () => {
      const connection = this.connection;
      if (!connection) return;

      // Wait for connection to close
      await connection.closed();

      // Only reconnect if we didn't explicitly disconnect
      if (this.state !== 'disconnected') {
        this.state = 'reconnecting';
        this.scheduleReconnect();
      }
    })();
  }

  /**
   * Handle connection errors with exponential backoff.
   */
  private async handleConnectionError(error: unknown): Promise<void> {
    if (this.reconnectAttempt >= this.options.maxReconnectAttempts) {
      this.state = 'disconnected';
      throw new Error(
        `Failed to connect after ${this.reconnectAttempt} attempts: ${error}`
      );
    }

    this.state = 'reconnecting';
    this.scheduleReconnect();
  }

  /**
   * Schedule a reconnection attempt with exponential backoff.
   */
  private scheduleReconnect(): void {
    this.clearReconnectTimer();

    const delay = calculateBackoff(this.reconnectAttempt);
    this.reconnectAttempt++;

    this.reconnectTimer = setTimeout(() => {
      this.establishConnection().catch((error) => {
        console.error('Reconnection failed:', error);
      });
    }, delay);
  }

  /**
   * Clear any pending reconnection timer.
   */
  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}
