//! DX — the HTTP probe.
//!
//! Read-only by default: a single `GET` that never mutates the target. It
//! reads `(status, latency, body)` and maps it into a typed observation the
//! controller can fold into the belief state.

use std::io::{Read, Write};
use std::net::TcpStream;
use std::time::{Duration, Instant};

use crate::probe::{Evidence, Observation, Probe, Severity};

/// The HTTP probe discriminates four fault classes plus healthy.
pub const HTTP_CLASSES: &[&str] = &["healthy", "http500", "corrupt", "degraded"];

pub struct HttpProbe;

impl Probe for HttpProbe {
    fn id(&self) -> &str {
        "http.status"
    }

    fn discriminates(&self) -> Vec<String> {
        HTTP_CLASSES.iter().map(|s| s.to_string()).collect()
    }

    fn run(&self, target: &str) -> Result<Evidence, String> {
        // Parse host:port, defaulting to port 80.
        let addr = target.trim_start_matches("http://").trim_start_matches("https://");
        let start = Instant::now();
        let mut stream = TcpStream::connect_timeout(
            &addr.parse().map_err(|e| format!("bad target {target}: {e}"))?,
            Duration::from_secs(3),
        )
        .map_err(|e| format!("connect failed for {target}: {e}"))?;
        stream
            .set_read_timeout(Some(Duration::from_secs(3)))
            .map_err(|e| format!("set timeout: {e}"))?;

        let req = format!(
            "GET / HTTP/1.1\r\nHost: {addr}\r\nConnection: close\r\n\r\n"
        );
        stream
            .write_all(req.as_bytes())
            .map_err(|e| format!("write failed: {e}"))?;

        let mut buf = Vec::new();
        let _ = stream.read_to_end(&mut buf);
        let latency_ms = start.elapsed().as_secs_f64() * 1000.0;
        let text = String::from_utf8_lossy(&buf).to_string();

        let status = text
            .lines()
            .next()
            .and_then(|l| l.split_whitespace().nth(1))
            .and_then(|s| s.parse::<u16>().ok())
            .unwrap_or(0u16);

        // Body = everything after the header block (blank line).
        let body = text
            .split("\r\n\r\n")
            .nth(1)
            .or_else(|| text.split("\n\n").nth(1))
            .unwrap_or("")
            .to_string();

        // Corrupt = body carries replacement characters (the mock returns
        // U+FFFD). Degraded = empty body on a 200.
        let corrupt = body.contains('\u{fffd}');
        let empty_body = body.trim().is_empty();

        // Map the observed response to a mode. Deterministic.
        let (mode, severity, remediation) = match status {
            500 => (
                "http500",
                Severity::Critical,
                "service returns 500; inspect handler".into(),
            ),
            0 => (
                "unreachable",
                Severity::Critical,
                "no valid HTTP response; check process/listener".into(),
            ),
            200 if corrupt => (
                "corrupt",
                Severity::Critical,
                "response body is corrupt (replacement bytes)".into(),
            ),
            200 if empty_body => (
                "degraded",
                Severity::Warning,
                "200 with empty body — degraded".into(),
            ),
            200 => ("ok", Severity::Ok, "service healthy".into()),
            s if s >= 400 => (
                "degraded",
                Severity::Warning,
                format!("unexpected status {s}"),
            ),
            s => (
                "degraded",
                Severity::Info,
                format!("status {s} outside healthy band"),
            ),
        };

        Ok(Evidence {
            id: self.id().to_string(),
            target: target.to_string(),
            discriminates: self.discriminates(),
            observation: Observation::Http {
                status,
                mode: mode.to_string(),
                latency_ms,
                body_len: text.len(),
            },
            severity,
            remediation,
        })
    }
}
