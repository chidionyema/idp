/**
 * Authoritative Estate Capability Registry
 * Sources: IDP repository, Argon Genesis repository
 * FLOW lifecycle #47 / PR #50 / Issue #7771
 */

import { EstateCapability } from './types';

export const ESTATE_CAPABILITIES: EstateCapability[] = [
  {
    id: 'idp.env.preview-provisioner',
    name: 'Ephemeral Environment Provisioner',
    version: '2.4.1',
    owner: 'IDP_CORE',
    authoritativeSource: 'idp/packages/preview-env/provisioner.ts',
    description: 'Provisions isolated, ephemeral PR preview environments with scoped PostgreSQL, Redis, and ingress route with auto-teardown TTL.',
    tags: ['preview', 'ephemeral', 'postgres', 'redis', 'k8s', 'environment'],
    inputs: [
      { name: 'branchName', type: 'string', required: true, description: 'Git branch name' },
      { name: 'ttlHours', type: 'number', required: false, description: 'Time-to-live in hours (default 72)' },
      { name: 'services', type: 'array', required: true, description: 'List of backend services to spin up' }
    ],
    outputs: [
      { name: 'endpointUrl', type: 'string', required: true, description: 'Preview ingress HTTPS URL' },
      { name: 'databaseConnectionUri', type: 'string', required: true, description: 'Isolated database URI' },
      { name: 'expiresAt', type: 'string', required: true, description: 'ISO expiry timestamp' }
    ],
    requiredPermissions: ['k8s:namespaces:create', 'k8s:deployments:create', 'dns:records:manage'],
    dependencies: ['idp.infra.cluster-manager', 'idp.data.pg-operator'],
    readiness: 'operationally_verified',
    readinessEvidence: {
      lastHealthCheck: '2026-11-09T20:30:00Z',
      uptime90d: 99.94,
      telemetrySource: 'otel-collector.idp.internal/preview-env-metrics',
      verifiedExecutionCount: 1482
    },
    slaMinutes: 3,
    avoidedHoursOnReuse: 18
  },
  {
    id: 'idp.security.vault-sync',
    name: 'Zero-Trust IAM & Vault Secret Sync',
    version: '3.1.2',
    owner: 'INFRA_SECOPS',
    authoritativeSource: 'idp/services/security/vault_sync.go',
    description: 'Rotates AWS/GCP IAM session credentials, synchronizes KMS secrets directly to Kubernetes Secret stores with cryptographic verification.',
    tags: ['iam', 'vault', 'credentials', 'secrets', 'k8s', 'rotation', 'security'],
    inputs: [
      { name: 'roleArn', type: 'string', required: true, description: 'Target IAM role ARN' },
      { name: 'targetNamespace', type: 'string', required: true, description: 'Target Kubernetes namespace' },
      { name: 'secretKeyMap', type: 'object', required: true, description: 'Mapping of Vault paths to K8s secret keys' }
    ],
    outputs: [
      { name: 'secretVersion', type: 'string', required: true, description: 'Synced secret version SHA' },
      { name: 'expiresAt', type: 'string', required: true, description: 'Session credential expiration ISO' },
      { name: 'auditDigest', type: 'string', required: true, description: 'SHA-256 tamper-evident log digest' }
    ],
    requiredPermissions: ['iam:AssumeRole', 'vault:read', 'k8s:secrets:write'],
    dependencies: ['idp.infra.vault-cluster', 'idp.security.kms-operator'],
    readiness: 'operationally_verified',
    readinessEvidence: {
      lastHealthCheck: '2026-11-09T20:40:00Z',
      uptime90d: 99.99,
      telemetrySource: 'otel-collector.idp.internal/vault-sync-health',
      verifiedExecutionCount: 4210
    },
    slaMinutes: 1,
    avoidedHoursOnReuse: 12
  },
  {
    id: 'idp.db.migration-runner',
    name: 'Zero-Downtime Database Migration Runner',
    version: '2.4.0',
    owner: 'DATA_PLATFORM',
    authoritativeSource: 'idp/services/data/migration_runner.py',
    description: 'Executes forward-compatible DB migrations with pre-flight lock acquisition, advisory safety locks, and automatic snapshot rollback checkpoint.',
    tags: ['database', 'migration', 'postgres', 'rollback', 'schema', 'zero-downtime'],
    inputs: [
      { name: 'targetDatabase', type: 'string', required: true, description: 'Identifier of target cluster' },
      { name: 'migrationScriptPath', type: 'string', required: true, description: 'Path to versioned SQL migration' },
      { name: 'dryRun', type: 'boolean', required: false, description: 'Verify lock acquisition without applying' }
    ],
    outputs: [
      { name: 'appliedVersion', type: 'string', required: true, description: 'Schema version reached' },
      { name: 'executionDurationMs', type: 'number', required: true, description: 'Execution time in milliseconds' },
      { name: 'snapshotCheckpointId', type: 'string', required: true, description: 'Point-in-time recovery snapshot ID' }
    ],
    requiredPermissions: ['db:schema:alter', 'db:snapshot:create'],
    dependencies: ['idp.data.pg-cluster-pool'],
    readiness: 'operationally_verified',
    readinessEvidence: {
      lastHealthCheck: '2026-11-09T20:35:00Z',
      uptime90d: 99.98,
      telemetrySource: 'otel-collector.idp.internal/db-migration-telemetry',
      verifiedExecutionCount: 890
    },
    slaMinutes: 5,
    avoidedHoursOnReuse: 14
  },
  {
    id: 'idp.traffic.canary-router',
    name: 'Service Mesh Canary Ingress Traffic Router',
    version: '1.8.3',
    owner: 'IDP_CORE',
    authoritativeSource: 'idp/packages/mesh/canary_router.ts',
    description: 'Configures Envoy/Istio canary virtual services for gradual traffic shifting with automated OTel P99 latency and 5xx error budget gating.',
    tags: ['traffic', 'canary', 'mesh', 'envoy', 'istio', 'ingress', 'split'],
    inputs: [
      { name: 'serviceName', type: 'string', required: true, description: 'Service identifier' },
      { name: 'splitPercentage', type: 'number', required: true, description: 'Percentage of traffic (0-100)' },
      { name: 'errorBudgetGate', type: 'number', required: false, description: 'Max allowed 5xx error percentage' }
    ],
    outputs: [
      { name: 'routingRuleId', type: 'string', required: true, description: 'VirtualService routing ID' },
      { name: 'telemetryStreamUrl', type: 'string', required: true, description: 'Realtime metric stream' }
    ],
    requiredPermissions: ['networking.k8s.io:virtualservices:patch'],
    dependencies: ['idp.infra.istio-control-plane', 'idp.observability.otel'],
    readiness: 'operationally_verified',
    readinessEvidence: {
      lastHealthCheck: '2026-11-09T20:39:00Z',
      uptime90d: 99.95,
      telemetrySource: 'otel-collector.idp.internal/mesh-canary',
      verifiedExecutionCount: 620
    },
    slaMinutes: 2,
    avoidedHoursOnReuse: 10
  },
  {
    id: 'idp.security.artifact-attestor',
    name: 'SLSA Provenance Attestor & Container Scanner',
    version: '2.0.4',
    owner: 'INFRA_SECOPS',
    authoritativeSource: 'idp/packages/security/attestation_scanner.py',
    description: 'Performs in-depth SBOM analysis, vulnerability scanning with Trivy/Grype, and generates cryptographic Cosign SLSA Level 3 provenance attestation.',
    tags: ['cve', 'security', 'slsa', 'provenance', 'container', 'cosign', 'attestation'],
    inputs: [
      { name: 'imageDigest', type: 'string', required: true, description: 'OCI image SHA256 digest' },
      { name: 'maxSeverityAllowed', type: 'string', required: false, description: 'Maximum tolerable CVE level (e.g. MEDIUM)' }
    ],
    outputs: [
      { name: 'attestationSignature', type: 'string', required: true, description: 'Cosign payload signature' },
      { name: 'cveReportSummary', type: 'object', required: true, description: 'Vulnerability counts by severity' },
      { name: 'slsaLevelAchieved', type: 'number', required: true, description: 'Achieved SLSA level (1-3)' }
    ],
    requiredPermissions: ['kms:sign', 'registry:catalog:read'],
    dependencies: ['idp.security.cosign-signer', 'idp.infra.harbor-registry'],
    readiness: 'operationally_verified',
    readinessEvidence: {
      lastHealthCheck: '2026-11-09T20:30:00Z',
      uptime90d: 99.99,
      telemetrySource: 'otel-collector.idp.internal/slsa-attestor',
      verifiedExecutionCount: 3104
    },
    slaMinutes: 4,
    avoidedHoursOnReuse: 15
  },
  {
    id: 'idp.data.kafka-topic-operator',
    name: 'Kafka Topic Operator & Schema Registry Validator',
    version: '1.4.2',
    owner: 'DATA_PLATFORM',
    authoritativeSource: 'idp/services/streaming/kafka_operator.go',
    description: 'Provisions partitioned Kafka topics, sets replication factors, retention policies, and validates Avro/Protobuf schema compatibility.',
    tags: ['kafka', 'streaming', 'topic', 'schema', 'avro', 'protobuf', 'partitions'],
    inputs: [
      { name: 'topicName', type: 'string', required: true, description: 'Kafka topic name' },
      { name: 'partitionCount', type: 'number', required: true, description: 'Number of partitions' },
      { name: 'schemaSpec', type: 'object', required: true, description: 'Avro/Protobuf schema definition' }
    ],
    outputs: [
      { name: 'topicArn', type: 'string', required: true, description: 'Kafka topic resource name' },
      { name: 'schemaId', type: 'number', required: true, description: 'Schema Registry registered ID' }
    ],
    requiredPermissions: ['kafka:topics:create', 'schemaregistry:subjects:write'],
    dependencies: ['idp.infra.kafka-cluster', 'idp.infra.schema-registry'],
    readiness: 'operationally_verified',
    readinessEvidence: {
      lastHealthCheck: '2026-11-09T20:25:00Z',
      uptime90d: 99.92,
      telemetrySource: 'otel-collector.idp.internal/kafka-operator',
      verifiedExecutionCount: 412
    },
    slaMinutes: 2,
    avoidedHoursOnReuse: 8
  },
  {
    id: 'idp.observability.trace-clusterer',
    name: 'OTel Distributed Trace Anomaly Clusterer',
    version: '2.1.0',
    owner: 'IDP_CORE',
    authoritativeSource: 'idp/services/observability/trace_clusterer.py',
    description: 'Aggregates OpenTelemetry spans for high latency anomalies (P95/P99), groups by root-cause call graph, and isolates cascading failures.',
    tags: ['otel', 'traces', 'telemetry', 'latency', 'p99', 'anomaly', 'diagnostics'],
    inputs: [
      { name: 'serviceName', type: 'string', required: true, description: 'Root service name' },
      { name: 'timeRangeMinutes', type: 'number', required: false, description: 'Lookback window in minutes' },
      { name: 'minLatencyMs', type: 'number', required: false, description: 'P99 threshold filter' }
    ],
    outputs: [
      { name: 'clusteredSpans', type: 'array', required: true, description: 'Grouped call chains with outlier spans' },
      { name: 'correlatedErrorCount', type: 'number', required: true, description: 'Count of 5xx or span exceptions' }
    ],
    requiredPermissions: ['observability:traces:query'],
    dependencies: ['idp.observability.jaeger-backend'],
    readiness: 'operationally_verified',
    readinessEvidence: {
      lastHealthCheck: '2026-11-09T20:41:00Z',
      uptime90d: 99.91,
      telemetrySource: 'otel-collector.idp.internal/trace-analytics',
      verifiedExecutionCount: 940
    },
    slaMinutes: 1,
    avoidedHoursOnReuse: 12
  },
  {
    id: 'idp.storage.s3-provisioner',
    name: 'Encrypted Object Storage Provisioner',
    version: '1.7.0',
    owner: 'INFRA_SECOPS',
    authoritativeSource: 'idp/services/storage/s3_provisioner.tf.json',
    description: 'Provisions enterprise S3/GCS buckets with customer-managed KMS encryption, versioning, CORS, and strict public-block policies.',
    tags: ['storage', 's3', 'bucket', 'kms', 'encryption', 'compliance'],
    inputs: [
      { name: 'bucketName', type: 'string', required: true, description: 'Globally unique bucket name' },
      { name: 'retentionDays', type: 'number', required: false, description: 'Lifecycle expiration days' },
      { name: 'kmsKeyId', type: 'string', required: false, description: 'Custom KMS key ARN' }
    ],
    outputs: [
      { name: 'bucketArn', type: 'string', required: true, description: 'Provisioned bucket ARN' },
      { name: 'accessPolicyJson', type: 'string', required: true, description: 'Applied least-privilege IAM policy' }
    ],
    requiredPermissions: ['s3:CreateBucket', 'kms:DescribeKey'],
    dependencies: ['idp.infra.aws-account-provider'],
    readiness: 'operationally_verified',
    readinessEvidence: {
      lastHealthCheck: '2026-11-09T20:10:00Z',
      uptime90d: 99.99,
      telemetrySource: 'otel-collector.idp.internal/s3-provisioner',
      verifiedExecutionCount: 780
    },
    slaMinutes: 3,
    avoidedHoursOnReuse: 6
  },
  {
    id: 'argon.flow.executor',
    name: 'Genesis FLOW Execution Engine',
    version: '3.0.0',
    owner: 'ARGON_GENESIS',
    authoritativeSource: 'argon/genesis/flow/lifecycle_engine.ts',
    description: 'Authoritative FLOW lifecycle coordinator (Issue #47 / PR #50) providing staged discovery, verification gates, and atomic rollback on failure.',
    tags: ['flow', 'lifecycle', 'genesis', 'execution', 'orchestration', 'governance'],
    inputs: [
      { name: 'instructionPayload', type: 'object', required: true, description: 'Structured agent intent' },
      { name: 'callerIdentity', type: 'string', required: true, description: 'Identity of requesting agent' },
      { name: 'ownershipClaimId', type: 'string', required: true, description: 'Claim reference (Issue #7771)' }
    ],
    outputs: [
      { name: 'lifecycleStatus', type: 'string', required: true, description: 'Final FLOW state' },
      { name: 'executionProofHash', type: 'string', required: true, description: 'Tamper-evident hash' },
      { name: 'avoidedWorkRecord', type: 'object', required: true, description: 'Audited avoided hours' }
    ],
    requiredPermissions: ['argon:flow:execute', 'argon:claims:verify'],
    dependencies: ['argon.genesis.claims-registry'],
    readiness: 'operationally_verified',
    readinessEvidence: {
      lastHealthCheck: '2026-11-09T20:42:00Z',
      uptime90d: 99.99,
      telemetrySource: 'otel-collector.argon.internal/flow-lifecycle',
      verifiedExecutionCount: 12540
    },
    slaMinutes: 1,
    avoidedHoursOnReuse: 25
  },
  {
    id: 'argon.genesis.claims-registry',
    name: 'Estate Ownership & Claims Manager',
    version: '1.2.4',
    owner: 'ARGON_GENESIS',
    authoritativeSource: 'argon/genesis/claims/issue_7771.ts',
    description: 'Enforces exclusive task leasing and ownership claims per issue #7771, preventing race conditions and duplicate agent commissioning.',
    tags: ['claims', 'ownership', 'lease', 'coordination', 'concurrency'],
    inputs: [
      { name: 'claimKey', type: 'string', required: true, description: 'Unique domain lock key' },
      { name: 'agentId', type: 'string', required: true, description: 'Claiming agent identifier' },
      { name: 'leaseTtlSeconds', type: 'number', required: false, description: 'Lease duration (default 300)' }
    ],
    outputs: [
      { name: 'leaseAcquired', type: 'boolean', required: true, description: 'Whether lease was granted' },
      { name: 'leaseToken', type: 'string', required: false, description: 'Cryptographic lease proof' }
    ],
    requiredPermissions: ['argon:claims:acquire'],
    dependencies: ['idp.infra.redis-cluster'],
    readiness: 'operationally_verified',
    readinessEvidence: {
      lastHealthCheck: '2026-11-09T20:40:00Z',
      uptime90d: 99.999,
      telemetrySource: 'otel-collector.argon.internal/claims-manager',
      verifiedExecutionCount: 18450
    },
    slaMinutes: 1,
    avoidedHoursOnReuse: 8
  },
  {
    id: 'idp.policy.opa-evaluator',
    name: 'Open Policy Agent (OPA) Guardrail Validator',
    version: '2.2.0',
    owner: 'INFRA_SECOPS',
    authoritativeSource: 'idp/services/policy/opa_evaluator.go',
    description: 'Evaluates Terraform plans, Kubernetes manifests, and IAM policies against authoritative enterprise security guardrails.',
    tags: ['opa', 'policy', 'rego', 'guardrail', 'compliance', 'security'],
    inputs: [
      { name: 'manifestJson', type: 'object', required: true, description: 'Resource manifest to inspect' },
      { name: 'policyDomain', type: 'string', required: true, description: 'Policy set: k8s | terraform | iam' }
    ],
    outputs: [
      { name: 'compliant', type: 'boolean', required: true, description: 'True if all checks passed' },
      { name: 'violations', type: 'array', required: true, description: 'List of rule infractions' }
    ],
    requiredPermissions: ['policy:evaluate'],
    dependencies: ['idp.security.rego-bundle-server'],
    readiness: 'operationally_verified',
    readinessEvidence: {
      lastHealthCheck: '2026-11-09T20:38:00Z',
      uptime90d: 99.96,
      telemetrySource: 'otel-collector.idp.internal/opa-engine',
      verifiedExecutionCount: 5200
    },
    slaMinutes: 1,
    avoidedHoursOnReuse: 9
  },
  {
    id: 'idp.env.zombie-cleaner',
    name: 'Ephemeral Environment Garbage Collector',
    version: '1.3.1',
    owner: 'IDP_CORE',
    authoritativeSource: 'idp/services/preview/zombie_cleaner.py',
    description: 'Scans preview namespaces for expired TTL (>72h), drains active TCP connections, snapshots DB state, and deletes orphaned k8s resources.',
    tags: ['cleaner', 'zombie', 'ephemeral', 'reaper', 'k8s', 'garbage-collection'],
    inputs: [
      { name: 'maxAgeHours', type: 'number', required: false, description: 'Max age cutoff (default 72)' },
      { name: 'dryRun', type: 'boolean', required: false, description: 'Preview deletions without applying' }
    ],
    outputs: [
      { name: 'reclaimedNamespaces', type: 'array', required: true, description: 'Namespaces deleted' },
      { name: 'monthlyCostSavedUsd', type: 'number', required: true, description: 'Calculated cloud spend saved' }
    ],
    requiredPermissions: ['k8s:namespaces:delete'],
    dependencies: ['idp.infra.cluster-manager'],
    readiness: 'operationally_verified',
    readinessEvidence: {
      lastHealthCheck: '2026-11-09T20:00:00Z',
      uptime90d: 99.9,
      telemetrySource: 'otel-collector.idp.internal/zombie-cleaner',
      verifiedExecutionCount: 310
    },
    slaMinutes: 5,
    avoidedHoursOnReuse: 7
  },
  {
    id: 'idp.security.cert-issuer',
    name: 'Zero-Trust mTLS Cert-Manager Issuer',
    version: '1.5.0',
    owner: 'INFRA_SECOPS',
    authoritativeSource: 'idp/packages/certs/issuer.ts',
    description: 'Issues and rotates internal X.509 service certificates with SPIFFE IDs for zero-trust mutual TLS communication across microservices.',
    tags: ['mtls', 'certs', 'spiffe', 'x509', 'tls', 'security', 'zero-trust'],
    inputs: [
      { name: 'spiffeId', type: 'string', required: true, description: 'SPIFFE identity URI' },
      { name: 'dnsNames', type: 'array', required: true, description: 'Subject Alternative Names (SANs)' }
    ],
    outputs: [
      { name: 'certificateSecretName', type: 'string', required: true, description: 'K8s TLS secret holding cert & key' },
      { name: 'validUntil', type: 'string', required: true, description: 'Expiry timestamp' }
    ],
    requiredPermissions: ['cert-manager.io:certificates:create'],
    dependencies: ['idp.infra.vault-pki-backend'],
    readiness: 'operationally_verified',
    readinessEvidence: {
      lastHealthCheck: '2026-11-09T20:20:00Z',
      uptime90d: 99.97,
      telemetrySource: 'otel-collector.idp.internal/cert-manager-metrics',
      verifiedExecutionCount: 1820
    },
    slaMinutes: 1,
    avoidedHoursOnReuse: 11
  },
  {
    id: 'argon.context.postmortem-compiler',
    name: 'Automated Incident Context Bundle Synthesizer',
    version: '2.0.1',
    owner: 'ARGON_GENESIS',
    authoritativeSource: 'argon/genesis/diagnostics/postmortem_bundler.ts',
    description: 'Aggregates multi-source incident context from Slack channels, PagerDuty alerts, OTel metrics, and Datadog logs into a chronological bundle.',
    tags: ['incident', 'postmortem', 'slack', 'pagerduty', 'logs', 'bundle', 'context'],
    inputs: [
      { name: 'incidentId', type: 'string', required: true, description: 'PagerDuty incident identifier' },
      { name: 'slackChannelId', type: 'string', required: false, description: 'Slack war room channel' }
    ],
    outputs: [
      { name: 'timelineMarkdown', type: 'string', required: true, description: 'Chronological timeline of incident' },
      { name: 'rootCauseHypotheses', type: 'array', required: true, description: 'Ranked error call chains' }
    ],
    requiredPermissions: ['argon:integrations:read', 'observability:logs:query'],
    dependencies: ['idp.observability.otel', 'argon.integrations.slack-bot'],
    readiness: 'operationally_verified',
    readinessEvidence: {
      lastHealthCheck: '2026-11-09T20:15:00Z',
      uptime90d: 99.88,
      telemetrySource: 'otel-collector.argon.internal/postmortem-service',
      verifiedExecutionCount: 295
    },
    slaMinutes: 3,
    avoidedHoursOnReuse: 16
  },
  {
    id: 'idp.catalog.openapi-registrar',
    name: 'OpenAPI Service Catalogue Registrar',
    version: '1.1.0',
    owner: 'IDP_CORE',
    authoritativeSource: 'idp/services/catalog/registrar.ts',
    description: 'Validates OpenAPI 3.1 specifications, checks breaking contract changes against previous revisions, and publishes to the developer portal.',
    tags: ['openapi', 'catalog', 'api-spec', 'developer-portal', 'breaking-change'],
    inputs: [
      { name: 'serviceId', type: 'string', required: true, description: 'Service slug in catalog' },
      { name: 'specYamlOrJson', type: 'string', required: true, description: 'OpenAPI 3.x spec content' }
    ],
    outputs: [
      { name: 'catalogUrl', type: 'string', required: true, description: 'Public link in IDP catalog' },
      { name: 'hasBreakingChanges', type: 'boolean', required: true, description: 'Whether spec breaks existing consumers' }
    ],
    requiredPermissions: ['catalog:services:write'],
    dependencies: ['idp.infra.backstage-portal'],
    readiness: 'operationally_verified',
    readinessEvidence: {
      lastHealthCheck: '2026-11-09T20:05:00Z',
      uptime90d: 99.93,
      telemetrySource: 'otel-collector.idp.internal/catalog-registrar',
      verifiedExecutionCount: 610
    },
    slaMinutes: 1,
    avoidedHoursOnReuse: 5
  },
  {
    id: 'idp.data.glacier-archiver',
    name: 'Compliant Cold Storage Glacier Archiver',
    version: '1.0.3',
    owner: 'DATA_PLATFORM',
    authoritativeSource: 'idp/services/data/glacier_archiver.go',
    description: 'Archives multi-tenant audit logs to AWS Glacier / GCS Coldline with immutable Vault Lock policies and cryptographic SHA-512 manifest.',
    tags: ['glacier', 'archive', 'cold-storage', 'audit-logs', 'compliance', 'sha512'],
    inputs: [
      { name: 'logRetentionCutoff', type: 'string', required: true, description: 'ISO cutoff date' },
      { name: 'vaultLockYears', type: 'number', required: false, description: 'Compliance retention period (default 7)' }
    ],
    outputs: [
      { name: 'archiveArchiveId', type: 'string', required: true, description: 'Glacier archive identifier' },
      { name: 'manifestSha512', type: 'string', required: true, description: 'Cryptographic manifest hash' }
    ],
    requiredPermissions: ['glacier:UploadArchive', 'glacier:InitiateVaultLock'],
    dependencies: ['idp.infra.aws-account-provider'],
    readiness: 'operationally_verified',
    readinessEvidence: {
      lastHealthCheck: '2026-11-09T19:40:00Z',
      uptime90d: 99.95,
      telemetrySource: 'otel-collector.idp.internal/glacier-archiver',
      verifiedExecutionCount: 180
    },
    slaMinutes: 10,
    avoidedHoursOnReuse: 8
  },
  {
    id: 'idp.network.cloudflare-dns',
    name: 'Cloudflare DNS & TLS Challenge Automator',
    version: '2.0.0',
    owner: 'INFRA_SECOPS',
    authoritativeSource: 'idp/packages/dns/cloudflare_manager.ts',
    description: 'Automates DNS CNAME/A record updates and ACME DNS-01 challenge propagation across global Cloudflare edge network.',
    tags: ['dns', 'cloudflare', 'tls', 'acme', 'ssl', 'records'],
    inputs: [
      { name: 'domainName', type: 'string', required: true, description: 'Fully qualified domain name' },
      { name: 'recordType', type: 'string', required: true, description: 'A, CNAME, TXT' },
      { name: 'targetValue', type: 'string', required: true, description: 'IP or canonical alias' }
    ],
    outputs: [
      { name: 'dnsRecordId', type: 'string', required: true, description: 'Cloudflare zone record ID' },
      { name: 'edgePropagationVerified', type: 'boolean', required: true, description: 'Whether edge POPs have synced' }
    ],
    requiredPermissions: ['cloudflare:dns:edit'],
    dependencies: ['idp.infra.cloudflare-api'],
    readiness: 'operationally_verified',
    readinessEvidence: {
      lastHealthCheck: '2026-11-09T20:22:00Z',
      uptime90d: 99.99,
      telemetrySource: 'otel-collector.idp.internal/dns-manager',
      verifiedExecutionCount: 2200
    },
    slaMinutes: 1,
    avoidedHoursOnReuse: 4
  },
  {
    id: 'idp.infra.nodepool-upgrader',
    name: 'Safe Rolling Node Pool Upgrader',
    version: '0.9.2',
    owner: 'IDP_CORE',
    authoritativeSource: 'idp/packages/k8s/nodepool_upgrader.py',
    description: 'Coordinates blue/green Kubernetes node pool rollout, honoring PodDisruptionBudgets, node drains, and cordoning.',
    tags: ['nodepool', 'k8s', 'upgrade', 'rolling', 'pdb', 'infrastructure'],
    inputs: [
      { name: 'clusterId', type: 'string', required: true, description: 'Target cluster' },
      { name: 'targetK8sVersion', type: 'string', required: true, description: 'Target Kubernetes minor release' }
    ],
    outputs: [
      { name: 'upgradeStatus', type: 'string', required: true, description: 'SUCCESS | ROLLED_BACK' },
      { name: 'drainedNodesCount', type: 'number', required: true, description: 'Total nodes safely migrated' }
    ],
    requiredPermissions: ['k8s:nodes:cordon', 'k8s:nodes:drain', 'cloud:nodepools:update'],
    dependencies: ['idp.infra.cluster-manager'],
    readiness: 'tested', // Note: Only tested, not yet operationally_verified in prod
    readinessEvidence: {
      lastHealthCheck: '2026-11-09T18:00:00Z',
      uptime90d: 98.5,
      telemetrySource: 'otel-collector.idp.internal/nodepool-upgrader',
      verifiedExecutionCount: 14,
      lastFailureReason: 'Staging soak test passed; prod execution gate pending signoff'
    },
    slaMinutes: 20,
    avoidedHoursOnReuse: 16
  },
  {
    id: 'idp.data.synthetic-fixture-gen',
    name: 'Differential-Privacy Fixture Synthesizer',
    version: '0.8.0',
    owner: 'DATA_PLATFORM',
    authoritativeSource: 'idp/experimental/privacy/synthesizer.py',
    description: 'Generates mathematically synthetic database fixtures mimicking production distributions without retaining PII.',
    tags: ['privacy', 'synthetic', 'fixtures', 'pii', 'differential-privacy', 'test-data'],
    inputs: [
      { name: 'schemaTable', type: 'string', required: true, description: 'Table structure' },
      { name: 'recordCount', type: 'number', required: true, description: 'Number of rows' }
    ],
    outputs: [
      { name: 'fixtureSql', type: 'string', required: true, description: 'Safe SQL insert script' },
      { name: 'privacyEpsilon', type: 'number', required: true, description: 'Differential privacy budget utilized' }
    ],
    requiredPermissions: ['data:anonymize:read'],
    dependencies: ['idp.data.pg-cluster-pool'],
    readiness: 'implemented', // Implemented, passed unit tests, not deployed in main cluster
    readinessEvidence: {
      lastHealthCheck: '2026-11-08T12:00:00Z',
      uptime90d: 95.0,
      telemetrySource: 'local-test-runner',
      verifiedExecutionCount: 6,
      lastFailureReason: 'No live telemetry endpoint provisioned'
    },
    slaMinutes: 10,
    avoidedHoursOnReuse: 14
  },
  {
    id: 'idp.infra.legacy-dns-updater',
    name: 'Deprecated Legacy BIND DNS Tool',
    version: '0.3.0',
    owner: 'INFRA_SECOPS',
    authoritativeSource: 'idp/legacy/bind_dns.sh',
    description: 'Legacy bash script for updating on-prem BIND records. DEPRECATED and degraded.',
    tags: ['dns', 'bind', 'legacy', 'deprecated'],
    inputs: [
      { name: 'host', type: 'string', required: true, description: 'Hostname' }
    ],
    outputs: [
      { name: 'status', type: 'string', required: true, description: 'Exit status' }
    ],
    requiredPermissions: ['infra:legacy:bind'],
    dependencies: ['on-prem-bind-server'],
    readiness: 'degraded',
    readinessEvidence: {
      lastHealthCheck: '2026-10-01T00:00:00Z',
      uptime90d: 45.2,
      telemetrySource: 'legacy-syslog',
      verifiedExecutionCount: 0,
      lastFailureReason: 'On-prem BIND server decommissioned. Use idp.network.cloudflare-dns instead.'
    },
    slaMinutes: 60,
    avoidedHoursOnReuse: 2
  }
];
