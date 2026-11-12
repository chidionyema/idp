import { NextResponse } from "next/server";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function POST() {
  const res = NextResponse.redirect(new URL("/investors", process.env.MERIDIAN_SITE_URL ?? "https://meridian-intelligence-uk.vercel.app"), 303);
  res.cookies.delete("__Host-meridian-investor");
  res.cookies.delete("__Host-meridian-investor-flow");
  res.headers.set("Cache-Control", "private, no-store");
  return res;
}
