import { timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { authorizeInvestor, brokerConfig, validBrokerOrigin, validSessionCookie } from "@/lib/investorAccess";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const FLOW = "__Host-meridian-investor-flow";
const SESSION = "__Host-meridian-investor";
const CODE = /^[A-Za-z0-9_-]{20,512}$/;
const B64 = /^[A-Za-z0-9_-]{43}$/;

const safeEqual = (a: string, b: string) =>
  a.length === b.length && timingSafeEqual(Buffer.from(a), Buffer.from(b));

export async function GET(req: NextRequest) {
  const canonicalSite = validBrokerOrigin(process.env.MERIDIAN_SITE_URL ?? "");
  if (!canonicalSite) {
    return NextResponse.json({ error: "investor_access_unavailable" }, {
      status: 503, headers: { "Cache-Control": "private, no-store", "X-Robots-Tag": "noindex" },
    });
  }
  const failed = (reason: string) => {
    const url = new URL("/investors", canonicalSite);
    url.searchParams.set("access", reason);
    const res = NextResponse.redirect(url, 303);
    res.cookies.delete(FLOW);
    res.cookies.delete(SESSION);
    res.headers.set("Referrer-Policy", "no-referrer");
    res.headers.set("Cache-Control", "no-store");
    return res;
  };
  const state = req.nextUrl.searchParams.get("state") ?? "";
  const code = req.nextUrl.searchParams.get("code") ?? "";
  const flow = req.cookies.get(FLOW)?.value ?? "";
  const parts = flow.split(".");
  const config = brokerConfig();
  if (!config || !CODE.test(code) || !B64.test(state) || parts.length !== 2 ||
      !B64.test(parts[0]) || !B64.test(parts[1]) || !safeEqual(state, parts[0])) {
    return failed("denied");
  }
  try {
    const response = await fetch(config.origin + "/v1/investor/login/redeem", {
      method: "POST", cache: "no-store", redirect: "error",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + config.serviceToken },
      body: JSON.stringify({ clientId: "meridian-investor-room", code,
        redirectUri: canonicalSite + "/investors/activate",
        state, verifier: parts[1] }),
      signal: AbortSignal.timeout(4500),
    });
    if (!response.ok) return failed("denied");
    const data: unknown = await response.json();
    if (!data || typeof data !== "object" || !("session" in data) ||
        !validSessionCookie(data.session)) return failed("denied");
    const auth = await authorizeInvestor(data.session, config);
    if (auth.state !== "allowed") return failed("denied");
    const validForSeconds = Math.min(900, Math.floor((Date.parse(auth.grant.expiresAt) - Date.now()) / 1000));
    if (validForSeconds <= 0) return failed("expired");
    const res = NextResponse.redirect(new URL("/investors/room", canonicalSite), 303);
    res.headers.set("Cache-Control", "private, no-store");
    res.headers.set("Referrer-Policy", "no-referrer");
    res.cookies.delete(FLOW);
    res.cookies.set(SESSION, data.session, {
      httpOnly: true, secure: true, sameSite: "lax", path: "/", maxAge: validForSeconds,
    });
    return res;
  } catch { return failed("denied"); }
}
