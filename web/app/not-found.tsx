import Link from "next/link";
export default function NotFound() {
  return (
    <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center", padding: "32px" }}>
      <div style={{ maxWidth: "480px", textAlign: "center" }}>
        <p style={{ fontFamily: "var(--mono)", fontSize: "48px", fontWeight: 600, color: "var(--rule)", marginBottom: "16px" }}>404</p>
        <h1 style={{ fontFamily: "var(--serif)", fontSize: "1.8rem", marginBottom: "16px" }}>Page not found</h1>
        <p style={{ color: "var(--ink-3)", marginBottom: "32px" }}>This page does not exist. The URL may have changed or been removed.</p>
        <div style={{ display: "flex", gap: "12px", justifyContent: "center", flexWrap: "wrap" }}>
          <Link href="/" className="btn-primary">Go home</Link>
          <Link href="/contact" className="btn-secondary">Contact us</Link>
        </div>
      </div>
    </div>
  );
}
