export default function Loading() {
  return (
    <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "16px" }}>
        <span className="pulse-dot" style={{ width: "8px", height: "8px" }} />
        <p style={{ fontFamily: "var(--mono)", fontSize: "12px", color: "var(--ink-3)" }}>Loading…</p>
      </div>
    </div>
  );
}
