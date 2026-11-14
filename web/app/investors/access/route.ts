import { createHash, randomBytes } from "node:crypto";
import { NextResponse } from "next/server";
import { brokerConfig, validBrokerOrigin } from "@/lib/investorAccess";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * Entry to a separate named-investor OIDC/MFA identity broker.
 * A random state + PKCE challenge is bound to this exact Meridian host.
 * No invite token, operational password or estate credential is accepted here.
 */
export async function GET() {
  const config = brokerConfig();
  const redirectOrigin = validBrokerOrigin(process.env.MERIDIAN_SITE_URL ?? "");
  if (!redirectOrigin) {
    // Relative Location is valid HTTP and never reflects an untrusted Host header.
    // Without configured identity, visitors reach the humane refusal page on this origin.
    return new NextResponse(null, {
      status: 303,
      headers: { Location: "/investors/unavailable", "Cache-Control": "private, no-store",
        "Referrer-Policy": "no-referrer" },
    });
  }
  if (!config) {
    const response = NextResponse.redirect(new URL("/investors/unavailable", redirectOrigin), 303);
    response.headers.set("Cache-Control", "private, no-store");
    return response;
  }
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
