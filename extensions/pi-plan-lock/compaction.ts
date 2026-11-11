// Thin Pi lifecycle adapter. The reducer is shared and the existing Estate router owns models.
import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import { reduceSummary } from "../../packages/estate-context/bounded-summary.ts";

function diagnostic(value: unknown): string {
  let text = String(value);
  const key = process.env.LITELLM_API_KEY;
  if (key && key.length > 8) text = text.split(key).join("<redacted-key>");
  return text.replace(/Bearer\s+\S+/gi, "Bearer <redacted>")
    .replace(/sk-[A-Za-z0-9_-]{8,}/g, "<redacted-key>").slice(0, 1000);
}

function addUsage(a: any, b: any): any {
  if (!a) return b ? structuredClone(b) : undefined;
  const out = { ...a };
  for (const [key, value] of Object.entries(b ?? {})) {
    if (typeof value === "number") out[key] = (out[key] ?? 0) + value;
    else if (value && typeof value === "object") out[key] = addUsage(out[key], value);
  }
  return out;
}

export function registerCompaction(pi: any, serialize: (messages: any[]) => string) {
  pi.on("session_before_compact", async (event: any, ctx: any) => {
    try {
      const policy = JSON.parse(readFileSync(new URL("../../platform/llm/context-policy.json", import.meta.url), "utf8"));
      for (const key of ["max_request_bytes", "max_summary_bytes", "max_output_tokens", "max_requests", "timeout_ms"]) {
        if (!Number.isSafeInteger(policy[key]) || policy[key] < 1) throw new Error(`Invalid context policy: ${key}`);
      }
      const lane = process.env.ESTATE_SUMMARY_LANE ?? policy.summary_lane;
      if (typeof lane !== "string" || !lane) throw new Error("Context policy has no summary lane");
      const model = ctx.modelRegistry.find("estate", lane);
      let router: URL | undefined;
      try {
        router = new URL(model?.baseUrl);
      } catch {
        // Reported below with the lane name; never fall through to a direct provider.
      }
      const loopback = router && ["127.0.0.1", "localhost", "::1"].includes(router.hostname);
      if (!model || model.provider !== "estate" || !loopback || !["http:", "https:"].includes(router?.protocol ?? "")) {
        throw new Error(`Estate summary lane ${lane} is not bound to the configured local router`);
      }
      if (!Number.isFinite(model.contextWindow) || model.contextWindow < 16_384) {
        throw new Error("Estate summary lane has no usable context budget");
      }
      const p = event.preparation;
      if (!p.firstKeptEntryId && !Array.isArray(p.retainedTail)) {
        throw new Error("Pi supplied no retained-context boundary");
      }
      const messages = [...(p.messagesToSummarize ?? []), ...(p.turnPrefixMessages ?? [])];
      const source = serialize(messages);
      if (!source.trim() && !p.previousSummary) return undefined;
      // Byte bound is conservative even for text with unusually high token density. Provider
      // framing and output have at least half the advertised context left for themselves.
      const maxRequestBytes = Math.min(policy.max_request_bytes, Math.floor(model.contextWindow / 2));
      const maxSummaryBytes = Math.min(policy.max_summary_bytes, Math.floor(maxRequestBytes / 4));
      const sessionId = `estate-compaction-${randomUUID()}`;
      const signal = AbortSignal.any([event.signal, AbortSignal.timeout(policy.timeout_ms)]);
      let usage: any;
      ctx.ui.notify("Compacting history through the Estate router in bounded chunks", "info");
      const result = await reduceSummary(source, {
        maxRequestBytes,
        maxSummaryBytes,
        maxRequests: policy.max_requests,
        previousSummary: p.previousSummary,
        customInstructions: event.customInstructions,
        signal,
        complete: async (context) => {
          const response = await ctx.modelRegistry.complete(model, context, {
            maxTokens: Math.min(policy.max_output_tokens, model.maxTokens > 0 ? model.maxTokens : policy.max_output_tokens),
            signal,
            cacheRetention: "none",
            sessionId,
          });
          usage = addUsage(usage, response.usage);
          if (response.stopReason === "error" || response.stopReason === "aborted" || response.stopReason === "length") {
            throw new Error(`Estate summary did not complete (${response.stopReason}): ${diagnostic(response.errorMessage ?? "no provider detail")}`);
          }
          if (response.content.some((c: any) => c.type === "toolCall")) throw new Error("Summary attempted a tool call");
          return response.content.filter((c: any) => c.type === "text").map((c: any) => c.text).join("\n");
        },
        onProgress: (chunk) => ctx.ui.notify(`Compaction chunk ${chunk.index} complete (${chunk.requestBytes} bytes)`, "info"),
      });
      const fileOps = p.fileOps ?? {};
      return {
        compaction: {
          summary: result.summary,
          firstKeptEntryId: p.firstKeptEntryId,
          // Pi 0.86's bundled runtime retains messages directly; the unbundled runtime uses
          // firstKeptEntryId. Carry the supplied boundary unchanged for either runtime.
          ...(Array.isArray(p.retainedTail) ? { retainedTail: p.retainedTail } : {}),
          tokensBefore: p.tokensBefore,
          usage,
          details: {
            readFiles: [...(fileOps.read ?? [])].filter((f) => !fileOps.edited?.has(f)),
            modifiedFiles: [...(fileOps.edited ?? [])],
            boundedReduction: { ...result, summary: undefined, sessionId, lane, maxRequestBytes },
          },
        },
      };
    } catch (error) {
      const message = diagnostic(error instanceof Error ? error.message : error);
      pi.appendEntry?.("estate_compaction_failed", { error: message, transcriptRetained: true });
      ctx.ui.notify(`Compaction stopped; transcript retained: ${message}`, "error");
      // Returning undefined would re-run Pi's original unbounded summarizer.
      return { cancel: true };
    }
  });
}
