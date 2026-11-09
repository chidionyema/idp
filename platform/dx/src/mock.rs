//! DX — the mock target service.
//!
//! Reads a state file `state_<port>.json` of the form
//! `{"mode":"ok|http500|corrupt|degraded"}` (or no file -> healthy) and serves
//! the matching HTTP response, so the controller can be proven against a live
//! target. This is disposable lab infrastructure, not a production dependency.

use std::io::{Read, Write};
use std::net::TcpListener;
use std::path::PathBuf;
use std::time::Duration;

fn load_mode(port: u16) -> String {
    let path = PathBuf::from(format!("state_{port}.json"));
    match std::fs::read_to_string(&path) {
        Ok(s) => {
            let v: serde_json::Value = serde_json::from_str(&s).unwrap_or_default();
            v.get("mode")
                .and_then(|m| m.as_str())
                .unwrap_or("ok")
                .to_string()
        }
        Err(_) => "ok".to_string(),
    }
}

fn handle(mut stream: std::net::TcpStream, port: u16) {
    stream
        .set_read_timeout(Some(Duration::from_secs(2)))
        .ok();
    let mut req = [0u8; 2048];
    let _ = stream.read(&mut req);

    let mode = load_mode(port);
    let (status, body): (&str, &str) = match mode.as_str() {
        "ok" => ("200 OK", "ok"),
        "http500" => ("500 Internal Server Error", "boom"),
        "corrupt" => ("200 OK", "\u{fffd}\u{fffd}corrupt"),
        "degraded" => ("200 OK", ""),
        _ => ("200 OK", "ok"),
    };
    let resp = format!(
        "HTTP/1.1 {status}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
        body.len()
    );
    let _ = stream.write_all(resp.as_bytes());
}

/// Serve one mock target on `port`. Blocks until killed.
pub fn serve(port: u16) -> std::io::Result<()> {
    let listener = TcpListener::bind(("127.0.0.1", port))?;
    for conn in listener.incoming() {
        if let Ok(stream) = conn {
            std::thread::spawn(move || handle(stream, port));
        }
    }
    Ok(())
}
