import { ImageResponse } from "next/og";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export default function OpenGraphImage() {
  return new ImageResponse(
    (<div style={{ display: "flex", flexDirection: "column", width: "100%", height: "100%", background: "#FAFAF8" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "8px", background: "#1A56DB" }} />
      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", justifyContent: "center", flex: 1, padding: "80px 80px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "32px" }}>
          <span style={{ fontFamily: "monospace", fontSize: "28px", fontWeight: 600, color: "#1A56DB" }}>Meridian</span>
          <span style={{ fontFamily: "monospace", fontSize: "28px", color: "#1A56DB" }}>.</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <p style={{ fontFamily: "Georgia, serif", fontSize: "56px", fontWeight: 500, color: "#0D0D0A", lineHeight: 1.1, letterSpacing: "-0.02em" }}>AI infrastructure for the enterprises building what’s next.</p>
          <p style={{ fontFamily: "monospace", fontSize: "20px", color: "#6B6B68" }}>Routing · Observability · Security · Evaluation</p>
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", height: "48px", background: "#0D0D0A", padding: "0 80px", gap: "24px" }}>
        {["Research", "Case Studies", "Tooling", "Consulting", "Writing"].map((item) => (
          <span key={item} style={{ fontFamily: "monospace", fontSize: "11px", color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: "0.08em" }}>{item}</span>
        ))}
      </div>
    </div>),
    { ...size }
  );
}
