// convex/schema.ts
import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  biTemporalFacts: defineTable({
    factId: v.string(),
    tenantId: v.string(),
    scope: v.union(
      v.literal("ephemeral_turn"),
      v.literal("project_fact"),
      v.literal("global_preference")
    ),
    projectId: v.optional(v.string()),
    subject: v.string(),
    predicate: v.string(),
    object: v.string(),
    artifactUri: v.optional(v.string()),
    artifactVersionHash: v.optional(v.string()),
    sourceEventAt: v.number(),
    ingestedAt: v.number(),
    provenance: v.union(
      v.literal("user_direct"),
      v.literal("verified_internal"),
      v.literal("untrusted_external")
    ),
    confidence: v.number(),
    recurrenceCount: v.number(),
    version: v.number(),
    status: v.union(
      v.literal("active"),
      v.literal("superseded"),
      v.literal("archived")
    ),
    supersededById: v.optional(v.string()),
    embedding: v.array(v.float64()),
  })
    .index("by_fact_id", ["factId"])
    .index("by_tenant_subject_predicate_status", [
      "tenantId",
      "subject",
      "predicate",
      "status",
      "projectId",
    ])
    .index("by_tenant_project_status", ["tenantId", "projectId", "status"])
    .vectorIndex("by_embedding", {
      vectorField: "embedding",
      dimensions: 1536,
      filterFields: ["tenantId", "status", "scope", "projectId"],
    }),

  graphEdges: defineTable({
    tenantId: v.string(),
    fromNode: v.string(),
    toNode: v.string(),
    relation: v.string(),
    factId: v.string(),
    status: v.union(v.literal("active"), v.literal("archived")),
    updatedAt: v.number(),
  })
    .index("by_tenant_from_status", ["tenantId", "fromNode", "status"])
    .index("by_tenant_to_status", ["tenantId", "toNode", "status"])
    .index("by_fact_id", ["factId"]),

  approvalTickets: defineTable({
    ticketId: v.string(),
    payloadHash: v.string(),
    agentId: v.string(),
    toolName: v.string(),
    targetResource: v.string(),
    status: v.union(
      v.literal("pending"),
      v.literal("approved"),
      v.literal("rejected"),
      v.literal("consumed"),
      v.literal("expired")
    ),
    approvedBy: v.optional(v.string()),
    createdAt: v.number(),
    expiresAt: v.number(),
  })
    .index("by_ticket_id", ["ticketId"])
    .index("by_payload_hash", ["payloadHash", "status"]),

  idempotencyLedger: defineTable({
    idempotencyKey: v.string(),
    toolName: v.string(),
    outcome: v.union(
      v.literal("progress"),
      v.literal("blocked"),
      v.literal("failed"),
      v.literal("needs_info"),
      v.literal("done")
    ),
    output: v.string(),
    errorCode: v.optional(v.string()),
    errorSummary: v.optional(v.string()),
    createdAt: v.number(),
  }).index("by_idempotency_key", ["idempotencyKey"]),
});
