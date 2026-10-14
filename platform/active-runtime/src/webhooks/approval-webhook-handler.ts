// src/webhooks/approval-webhook-handler.ts
import crypto from "node:crypto";
import { z } from "zod";
import { AcidBackendDriver } from "../adapters/cortex-convex-adapter";
import { AgentTurnInput } from "../runtime/default-agent-wrapper";
import { ActiveRuntimeTelemetry } from "../telemetry/active-otel-exporter";

export const ApprovalWebhookPayloadSchema = z.object({
  ticketId: z.string().min(1),
  expectedPayloadHash: z.string().length(64),
  decision: z.enum(["approve", "reject"]),
  reviewerId: z.string().min(1),
  reason: z.string().optional(),
});

export type ApprovalWebhookPayload = z.infer<typeof ApprovalWebhookPayloadSchema>;

export interface SuspendedRunCheckpoint {
  runId: string;
  ticketId: string;
  expectedPayloadHash: string;
  turnInput: AgentTurnInput;
  resumeCallback: (input: AgentTurnInput) => Promise<{
    status: string;
    responseText: string;
  }>;
  createdAt: number;
}

export interface WebhookHttpRequest {
  headers: {
    "x-fleet-timestamp"?: string;
    "x-fleet-signature"?: string;
  };
  rawBody: string;
}

export interface WebhookHttpResponse {
  statusCode: 200 | 400 | 401 | 404 | 409;
  body: {
    ok: boolean;
    ticketId?: string;
    newStatus?: "approved" | "rejected";
    resumedRunStatus?: string;
    resumedResponseText?: string;
    error?: string;
  };
}

export class ApprovalWebhookHandler {
  private readonly suspendedRunsByTicket = new Map<string, SuspendedRunCheckpoint>();
  private readonly maxClockSkewMs = 5 * 60 * 1000; // 5 minutes anti-replay window

  constructor(
    private readonly signingSecret: string,
    private readonly acidBackend: AcidBackendDriver,
    private readonly telemetry: ActiveRuntimeTelemetry
  ) {}

  /**
   * Registers a suspended agent run when DefaultActiveAgentHarness returns AWAITING_APPROVAL
   * so the run automatically resumes as soon as the webhook approves the ticket.
   */
  registerSuspendedRun(checkpoint: SuspendedRunCheckpoint): void {
    this.suspendedRunsByTicket.set(checkpoint.ticketId, checkpoint);
  }

  /**
   * Generates a valid HMAC-SHA256 header signature (v0=<hex>) for webhook clients/tests.
   */
  static signWebhookPayload(
    signingSecret: string,
    timestampSec: number,
    rawBody: string
  ): string {
    const baseString = `v0:${timestampSec}:${rawBody}`;
    const hmac = crypto
      .createHmac("sha256", signingSecret)
      .update(baseString, "utf8")
      .digest("hex");
    return `v0=${hmac}`;
  }

  /**
   * Constant-time HMAC-SHA256 signature verification + replay timestamp check.
   */
  private verifySignature(req: WebhookHttpRequest): { valid: boolean; reason?: string } {
    const timestampHeader = req.headers["x-fleet-timestamp"];
    const signatureHeader = req.headers["x-fleet-signature"];

    if (!timestampHeader || !signatureHeader) {
      return { valid: false, reason: "Missing cryptographic signature or timestamp headers." };
    }

    const timestampSec = Number(timestampHeader);
    if (!Number.isFinite(timestampSec)) {
      return { valid: false, reason: "Invalid timestamp header." };
    }

    const ageMs = Math.abs(Date.now() - timestampSec * 1000);
    if (ageMs > this.maxClockSkewMs) {
      return {
        valid: false,
        reason: `Webhook timestamp outside 5-minute replay window (skew=${ageMs}ms).`,
      };
    }

    const expectedSig = ApprovalWebhookHandler.signWebhookPayload(
      this.signingSecret,
      timestampSec,
      req.rawBody
    );

    const actualBuf = Buffer.from(signatureHeader, "utf8");
    const expectedBuf = Buffer.from(expectedSig, "utf8");

    if (
      actualBuf.length !== expectedBuf.length ||
      !crypto.timingSafeEqual(actualBuf, expectedBuf)
    ) {
      return { valid: false, reason: "HMAC-SHA256 signature verification failed." };
    }

    return { valid: true };
  }

  /**
   * Processes incoming POST /webhooks/approvals callbacks from Slack or internal UI.
   */
  async handleWebhook(req: WebhookHttpRequest): Promise<WebhookHttpResponse> {
    return this.telemetry.withSpan(
      "approval_webhook.handle",
      {},
      async (): Promise<WebhookHttpResponse> => {
        // 1. Verify HMAC-SHA256 & Anti-Replay Window
        const sigCheck = this.verifySignature(req);
        if (!sigCheck.valid) {
          return {
            statusCode: 401,
            body: { ok: false, error: sigCheck.reason },
          };
        }

        // 2. Parse & Validate Schema
        let parsedJson: unknown;
        try {
          parsedJson = JSON.parse(req.rawBody);
        } catch {
          return {
            statusCode: 400,
            body: { ok: false, error: "Malformed JSON body." },
          };
        }

        const parsed = ApprovalWebhookPayloadSchema.safeParse(parsedJson);
        if (!parsed.success) {
          return {
            statusCode: 400,
            body: { ok: false, error: parsed.error.message },
          };
        }

        const payload = parsed.data;
        const now = Date.now();

        // 3. Atomic ACID State Transition + Payload-Hash Verification
        const txOutcome = await this.acidBackend.executeAcidTransaction(async (store) => {
          const ticket = store.approvals.get(payload.ticketId);
          if (!ticket) {
            return { code: 404 as const, error: `Ticket ${payload.ticketId} not found.` };
          }

          if (ticket.status !== "pending") {
            this.telemetry.recordApprovalEvent({
              agentId: ticket.agentId,
              toolName: ticket.toolName,
              event: "replay_or_hash_blocked",
            });
            return {
              code: 409 as const,
              error: `Ticket ${payload.ticketId} is already in terminal state "${ticket.status}".`,
            };
          }

          if (ticket.expiresAt <= now) {
            store.approvals.set(ticket.ticketId, { ...ticket, status: "expired" });
            this.telemetry.recordApprovalEvent({
              agentId: ticket.agentId,
              toolName: ticket.toolName,
              event: "replay_or_hash_blocked",
            });
            return {
              code: 409 as const,
              error: `Ticket ${payload.ticketId} expired at ${new Date(ticket.expiresAt).toISOString()}.`,
            };
          }

          // CRITICAL TOCTOU CHECK: Ensure the reviewer approved the exact SHA-256 payload hash
          if (ticket.payloadHash !== payload.expectedPayloadHash) {
            this.telemetry.recordApprovalEvent({
              agentId: ticket.agentId,
              toolName: ticket.toolName,
              event: "replay_or_hash_blocked",
            });
            return {
              code: 409 as const,
              error: `Payload hash mismatch on ticket ${payload.ticketId}. Action parameters changed since ticket creation.`,
            };
          }

          const newStatus: "approved" | "rejected" = payload.decision === "approve" ? "approved" : "rejected";
          store.approvals.set(ticket.ticketId, {
            ...ticket,
            status: newStatus,
            approvedBy: payload.reviewerId,
          });

          this.telemetry.recordApprovalEvent({
            agentId: ticket.agentId,
            toolName: ticket.toolName,
            event: newStatus,
          });

          return {
            code: 200 as const,
            ticket,
            newStatus,
          };
        });

        if (txOutcome.code !== 200) {
          return {
            statusCode: txOutcome.code,
            body: { ok: false, ticketId: payload.ticketId, error: txOutcome.error },
          };
        }

        // 4. Resume Suspended Agent Run if registered
        const checkpoint = this.suspendedRunsByTicket.get(payload.ticketId);
        if (checkpoint) {
          this.suspendedRunsByTicket.delete(payload.ticketId);
          const resumed = await checkpoint.resumeCallback(checkpoint.turnInput);
          return {
            statusCode: 200,
            body: {
              ok: true,
              ticketId: payload.ticketId,
              newStatus: txOutcome.newStatus,
              resumedRunStatus: resumed.status,
              resumedResponseText: resumed.responseText,
            },
          };
        }

        return {
          statusCode: 200,
          body: {
            ok: true,
            ticketId: payload.ticketId,
            newStatus: txOutcome.newStatus,
          },
        };
      }
    );
  }
}
