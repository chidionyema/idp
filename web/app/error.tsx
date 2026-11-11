"use client";
import { useEffect } from "react";
export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => { console.error(error); }, [error]);
  return (
    <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center", padding: "32px" }}>
      <div style={{ maxWidth: "480px", textAlign: "center" }}>
        <p className="mi-error-eyebrow">Application error</p>
        <h1 style={{ fontFamily: "var(--serif)", fontSize: "1.8rem", marginBottom: "16px" }}>Something went wrong</h1>
        <p className="mi-error-body">An unexpected error occurred. Try refreshing the page.</p>
        <button onClick={reset} className="btn-primary">Try again</button>
      </div>
    </div>
  );
}
