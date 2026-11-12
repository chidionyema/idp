import { NextRequest, NextResponse } from "next/server";
import { authorizeInvestor, brokerConfig, readInvestorProjection, type InvestorSurface } from "@/lib/investorAccess";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const SESSION_COOKIE = "__Host-meridian-investor";
const securityHeaders = {
  "Cache-Control": "private, no-store, max-age=0",
  Pragma: "no-cache",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
  "Vary": "Cookie",
};

export async function GET(req: NextRequest) {
  const cookie = req.cookies.get(SESSION_COOKIE)?.value;
  const config = brokerConfig();
  const auth = await authorizeInvestor(cookie, config);
  if (auth.state === "denied") {
    return NextResponse.json({ error: auth.reason === "expired" ? "access_expired" : "access_required" },
      { status: 401, headers: securityHeaders });
  }
  if (auth.state === "unavailable" || !config) {
    return NextResponse.json({ error: "access_service_unavailable" },
      { status: 503, headers: securityHeaders });
  }
  const grant = auth.grant;
  const scopes = [
    ["genesis", "investor:genesis:view"],
    ["otto", "investor:otto:view"],
  ] as const;
  const visible = await Promise.all(scopes.map(async ([surface, permission]) => {
    if (!grant.permissions.includes(permission)) return { surface, status: "not_granted" as const };
    const record = await readInvestorProjection(cookie!, grant, surface as InvestorSurface, config);
    return record.state === "available"
      ? { surface, status: "observed" as const, data: record.projection }
      : { surface, status: "source_unavailable" as const };
  }));
  return NextResponse.json({
    schema: "meridian.investor.room.v1", readOnly: true,
    viewer: grant.displayName, accessExpiresAt: grant.expiresAt,
    surfaces: visible,
  }, { status: 200, headers: securityHeaders });
}
