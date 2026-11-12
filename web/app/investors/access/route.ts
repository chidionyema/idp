import { createHash, randomBytes } from "node:crypto";
import { NextResponse } from "next/server";
import { brokerConfig } from "@/lib/investorAccess";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * Entry to a separate named-investor OIDC/MFA identity broker.
 * A random state + PKCE challenge is bound to this exact Meridian host.
 * No invite token, operational password or estate credential is accepted here.
 */
export async function GET() {
  const config = brokerConfig();
  const site = process.env.MERIDIAN_SITE_URL ?? "";
  let redirectOrigin: string;
  try {
    const url = new URL(site);
    if (url.protocol !== "https:" || url.username || url.password || url.search ||
        url.hash || url.pathname !== "/" || url.port || !url.hostname.includes(".")) throw Error("invalid");
    redirectOrigin = url.origin;
  } catch {
    return NextResponse.json({ error: "investor_auth_not_configured" },
      { status: 503, headers: { "Cache-Control": "no-store" } });
  }
  if (!config) return NextResponse.json({ error: "investor_auth_not_configured" },
    { status: 503, headers: { "Cache-Control": "no-store" } });
  const state = randomBytes(32).toString("base64url");
  const verifier = randomBytes(32).toString("base64url");
  const challenge = createHash("sha256").update(verifier).digest("base64url");
  const callback = redirectOrigin + "/investors/activate";
  const url = new URL("/v1/investor/login/start", config.origin);
  url.searchParams.set("client_id", "meridian-investor-room");
  url.searchParams.set("redirect_uri", callback);
  url.searchParams.set("state", state);
  url.searchParams.set("code_challenge", challenge);
  url.searchParams.set("code_challenge_method", "S256");
  const response = NextResponse.redirect(url, 303);
  response.headers.set("Cache-Control", "private, no-store");
  response.headers.set("Referrer-Policy", "no-referrer");
  response.cookies.set("__Host-meridian-investor-flow", state + "." + verifier, {
    httpOnly: true, secure: true, sameSite: "lax", path: "/", maxAge: 300,
  });
  return response;
}
