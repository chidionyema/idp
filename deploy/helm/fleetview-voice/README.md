# FleetView Voice Helm Chart

Deploy the FleetView Voice stack to Kubernetes in 10 minutes.

## Quick Start

```bash
# Add dependencies
helm dependency update ./deploy/helm/fleetview-voice

# Install with bundled NATS
helm install fleetview-voice ./deploy/helm/fleetview-voice

# Or with existing NATS
helm install fleetview-voice ./deploy/helm/fleetview-voice \
  --set nats.enabled=false \
  --set eventBus.nats.url=nats://your-nats:4222

# Enterprise deployment with Kafka
helm install fleetview-voice ./deploy/helm/fleetview-voice \
  -f ./deploy/helm/fleetview-voice/values-enterprise.yaml \
  --set eventBus.kafka.brokers[0]=kafka-1:9092 \
  --set auth.issuerUrl=https://your-idp.okta.com \
  --set auth.clientId=fleetview-voice
```

## Components

| Component | Description |
|-----------|-------------|
| API Server | FastAPI backend serving voice endpoints |
| Outbox Worker | Background worker draining SQLite outbox to NATS/Kafka |
| NATS JetStream | Bundled message bus (optional) |
| Redis | Session state cache (optional) |

## Configuration

### Authentication

```yaml
auth:
  provider: "oidc"  # oidc, saml, github, none
  issuerUrl: "https://your-idp.com"
  clientId: "fleetview-voice"
  clientSecretRef:
    name: "fleetview-voice-oidc"
    key: "client-secret"
```

### Event Bus

**NATS (default):**
```yaml
eventBus:
  type: "nats"
  nats:
    url: "nats://nats:4222"
    subjectPrefix: "fleetview.voice"
    streamName: "FLEETVIEW_VOICE"
    maxAge: "15m"
```

**Kafka:**
```yaml
eventBus:
  type: "kafka"
  kafka:
    brokers:
      - "kafka-1:9092"
      - "kafka-2:9092"
    topic: "fleetview.voice.events"
    sasl:
      enabled: true
      mechanism: "SCRAM-SHA-256"
      username: "fleetview"
      passwordSecretRef:
        name: "kafka-creds"
        key: "password"
    tls:
      enabled: true
      caSecretRef:
        name: "kafka-ca"
        key: "ca.crt"
```

### Privacy

```yaml
privacy:
  defaultTtlMinutes: 15        # Voice data expires after 15 minutes
  durableRetentionEnabled: false  # Enable for audit/compliance
  redaction:
    enabled: true
```

### Resources

```yaml
api:
  replicas: 2
  resources:
    requests:
      cpu: "100m"
      memory: "256Mi"
    limits:
      cpu: "1000m"
      memory: "1Gi"

worker:
  replicas: 1
  persistence:
    enabled: true
    size: 1Gi
```

## Health Checks

- **Liveness**: `GET /health`
- **Readiness**: `GET /ready`

## Observability

### Prometheus Metrics

```yaml
observability:
  metrics:
    enabled: true
    port: 9090
    path: /metrics
    serviceMonitor:
      enabled: true
```

### OpenTelemetry

```yaml
observability:
  otel:
    enabled: true
    endpoint: "otel-collector:4317"
    serviceName: "fleetview-voice"
```

## Requirements

- Kubernetes 1.24+
- Helm 3.8+
- Optional: NATS JetStream or Kafka cluster
- Optional: Redis for session state
