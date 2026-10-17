"use client";
import { useEffect } from "react";
export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => { console.error(error); }, [error]);
  return (
    <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center", padding: "32px" }}>
      <div style={{ maxWidth: "480px", textAlign: "center" }}>
        <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "#DC2626", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "16px" }}>Application error</p>
        <h1 style={{ fontFamily: "var(--serif)", fontSize: "1.8rem", marginBottom: "16px" }}>Something went wrong</h1>
        <p style={{ color: "var(--ink-3)", marginBottom: "32px" }}>An unexpected error occurred. Try refreshing the page.</p>
        <button onClick={reset} className="btn-primary">Try again</button>
      </div>
    </div>
  );
}
