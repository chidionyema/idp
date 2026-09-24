ui = true

storage "raft" {
  path    = "/vault/data"
  node_id = "vault-1"
}

listener "tcp" {
  address         = "0.0.0.0:8200"
  tls_disable     = 1
  tls_min_version = "tls12"
}

telemetry {
  prometheus_retention_time = "30s"
  disable_hostname          = true
}
