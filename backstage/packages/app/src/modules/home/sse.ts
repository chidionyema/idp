/*
 * An SSE reader that can carry a bearer token: `EventSource` cannot.
 *
 * WHY THIS FILE EXISTS. `/fleet` and `/face` open the board's live stream at
 * `<proxy>/fleetview/stream`. `EventSource` is the obvious tool and the wrong one here: the
 * browser's implementation sends no `Authorization` header and offers no way to add one, so the
 * request arrives at the Backstage proxy with no credentials. Measured 2026-10-04 against
 * production, in real Chrome, signed in as a guest:
 *
 *   GET /api/proxy/fleetview/sessions   -> 200 application/json   (through fetchApiRef)
 *   GET /api/proxy/fleetview/stream     -> 401 text/plain         (through EventSource)
 *
 * The 401 is not the fleetview service's -- dialled directly at 127.0.0.1:18790 the same path
 * streams frames and never refuses. It is the edge in front of it refusing an unauthenticated
 * request, exactly as the estate recorded on 2026-09-22 ("an `EventSource` would arrive with no
 * credentials and get a 401", useEstateVoice.ts). The page then falls back to polling, so the
 * defect is quiet: the board works, but never live.
 *
 * HOW. Route the stream through `fetchApi.fetch`, the same authenticated fetch every other
 * `/api/proxy/fleetview/...` call already uses -- so this is the estate's existing pattern, not a
 * second one. This is the shape `useEstateVoice.ts` reads `/voice/stream` with; it lives here now
 * so the three boards share one reader instead of three copies. No new dependency: buffering a
 * `ReadableStream` needs no library, and the rule below (a chunk boundary is not a message
 * boundary) is the one that has already bitten this codebase.
 *
 * The returned handle mimics the slice of `EventSource` the boards use -- `close()` and the
 * `onopen` / `onmessage` / `onerror` slots -- so a call site changes its constructor and nothing
 * else. `onerror` fires on a dropped connection, which is the signal the existing backoff retries
 * on; a `close()` is silent, as `EventSource.close()` is.
 */
import type { FetchApi } from '@backstage/core-plugin-api';

export interface SseHandlers {
  /** The connection opened and delivered its first bytes. Resets a caller's retry backoff. */
  onopen?: () => void;
  /** One decoded SSE frame. `data` is the raw `data:` payload (the boards `JSON.parse` it). */
  onmessage?: (ev: { data: string }) => void;
  /** The connection failed or ended unexpectedly. A deliberate `close()` does not call this. */
  onerror?: (err: unknown) => void;
}

export interface SseHandle {
  close: () => void;
}

export interface SseOptions extends SseHandlers {
  /** `url`, `headers`, `method`, `body` -- whatever the request needs beyond the bearer. */
  init?: RequestInit;
}

/**
 * Open an SSE stream through an authenticated fetch.
 *
 * `fetchApi` is the Backstage one (`useApi(fetchApiRef)`), so the request carries the identity
 * token the proxy requires. Returns immediately with a handle; the connection is awaited inside.
 */
export function openSse(
  fetchApi: FetchApi,
  url: string,
  options: SseOptions = {},
): SseHandle {
  const controller = new AbortController();
  let closed = false;
  let opened = false;

  const run = async () => {
    try {
      const res = await fetchApi.fetch(url, {
        ...options.init,
        headers: {
          Accept: 'text/event-stream',
          ...(options.init?.headers as Record<string, string> | undefined),
        },
        signal: controller.signal,
      });
      if (!res.ok || !res.body) {
        throw new Error(`stream ${res.status}`);
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        if (!opened) {
          opened = true;
          options.onopen?.();
        }
        buffer += decoder.decode(value, { stream: true });
        // Frames are separated by a blank line. A partial frame stays in the buffer until its
        // terminator arrives, because a chunk boundary is not a message boundary.
        const frames = buffer.split('\n\n');
        buffer = frames.pop() ?? '';
        for (const frame of frames) {
          // Heartbeats arrive as `: heartbeat` and carry no data line; skipping them keeps the
          // connection open without waking a caller that only speaks in frames.
          const dataLine = /^data:\s?(.*)$/m.exec(frame)?.[1];
          if (dataLine === undefined) continue;
          options.onmessage?.({ data: dataLine });
        }
      }
      // The server ended the stream without us asking. That is a drop, not a close.
      if (!closed) options.onerror?.(new Error('stream ended'));
    } catch (err) {
      const aborted = err instanceof Error && err.name === 'AbortError';
      if (!closed && !aborted) options.onerror?.(err);
    }
  };

  void run();

  return {
    close: () => {
      closed = true;
      controller.abort();
    },
  };
}
