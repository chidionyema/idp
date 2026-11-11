import { ImageResponse } from "next/og";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export default function OpenGraphImage() {
  return new ImageResponse(
    (<div style={{ display: "flex", flexDirection: "column", width: "100%", height: "100%", background: "#0B1421" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "8px", background: "#EAC47E" }} />
      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", justifyContent: "center", flex: 1, padding: "80px 80px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "16px", marginBottom: "32px" }}>
          {/* The mark, the same three primitives as components/Logo.tsx: ring, meridian, bead.
              Divs rather than the svg because ImageResponse renders a subset of svg; this is
              drawn once at one size, so it carries no ratios that could drift. */}
          <div style={{ display: "flex", position: "relative", width: "60px", height: "60px" }}>
            <div style={{ position: "absolute", top: "3px", left: "3px", width: "54px", height: "54px", border: "3px solid #F5F2E9", borderRadius: "30px" }} />
            <div style={{ position: "absolute", top: "3px", left: "21px", width: "18px", height: "54px", border: "3px solid #F5F2E9", borderRadius: "12px" }} />
            <div style={{ position: "absolute", top: "0px", left: "26px", width: "8px", height: "8px", borderRadius: "4px", background: "#EAC47E" }} />
          </div>
          <span style={{ fontFamily: "monospace", fontSize: "30px", fontWeight: 600, color: "#F5F2E9", letterSpacing: "-0.01em" }}>Meridian</span>
          <span style={{ fontFamily: "monospace", fontSize: "30px", fontWeight: 600, color: "#EAC47E" }}>.</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <p style={{ fontFamily: "Georgia, serif", fontSize: "56px", fontWeight: 500, color: "#F5F2E9", lineHeight: 1.1, letterSpacing: "-0.02em" }}>Intelligence, made real.</p>
          <p style={{ fontFamily: "monospace", fontSize: "20px", color: "#B1BDCA" }}>Consultancy · Research · Ventures</p>
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", height: "48px", background: "#F5F2E9", padding: "0 80px", gap: "24px" }}>
        {["Research", "Products", "Enterprise", "Lab", "Writing"].map((item) => (
          <span key={item} style={{ fontFamily: "monospace", fontSize: "11px", color: "#34544E", textTransform: "uppercase", letterSpacing: "0.08em" }}>{item}</span>
        ))}
      </div>
    </div>),
    { ...size }
  );
}
