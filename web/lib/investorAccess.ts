import { readFileSync } from "node:fs";
import { join } from "node:path";

/**
 * Boundary: the public Meridian site is NOT an identity provider.
 * The estate's separate investor access broker must verify the named investor,
 * inspect a revocable, expiring grant on EVERY request, and return only approved
 * read-only Genesis / OTTO projections. No source repo, worker credential,
 * automation command, private URL, or raw system event enters this contract.
 */
export type InvestorSurface = "genesis" | "otto";
export type InvestorPermission = "investor:genesis:view" | "investor:otto:view";

export interface InvestorGrant {
  grantId: string;
  displayName: string;
  subject: string;
  issuedAt: string;
  expiresAt: string;
  lastActivityAt: string;
  permissions: InvestorPermission[];
  identityVerifiedAt: string;
}

export interface InvestorFact { label: string; value: string }
export interface InvestorMoment { title: string; description: string; observedAt: string }
export interface InvestorProjection {
  surface: InvestorSurface;
  headline: string;
  introduction: string;
  observedAt: string;
  sourceRevision: string;
  facts: InvestorFact[];
  moments: InvestorMoment[];
}

export type AccessResult =
  | { state: "allowed"; grant: InvestorGrant }
  | { state: "denied"; reason: "no_session" | "invalid" | "expired" }
  | { state: "unavailable"; reason: "not_configured" | "upstream_unavailable" };

export type ProjectionResult =
  | { state: "available"; projection: InvestorProjection }
  | { state: "unavailable" };

export type BrokerConfig = { origin: string; serviceToken: string };
type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;
const SESSION_PATTERN = /^[A-Za-z0-9._~+/-]{24,4096}$/;
const PERMISSIONS: readonly InvestorPermission[] = ["investor:genesis:view", "investor:otto:view"];
const MAX_SESSION_WINDOW_MS = 30 * 60 * 1000;
// Founder-approved default investor grant ceiling: seven days, enforced on every request.
const MAX_GRANT_WINDOW_MS = 7 * 24 * 60 * 60 * 1000;
const isObject = (v: unknown): v is Record<string, unknown> => v !== null && typeof v === "object" && !Array.isArray(v);
const cleanText = (v: unknown, max = 150): string | null =>
  typeof v === "string" && v.length > 0 && v.length <= max && !/[\u0000-\u001f<>]/.test(v) ? v : null;
const parseTime = (v: unknown): number | null =>
  typeof v === "string" && /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z$/.test(v) && Number.isFinite(Date.parse(v)) ? Date.parse(v) : null;
const SHA = /^[a-f0-9]{40}$/;

/** The source is fixed by operator config, never by path, query or request headers. */
export function validBrokerOrigin(value: string): string | null {
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || url.username || url.password ||
        url.port || url.search || url.hash || (url.pathname !== "/" && url.pathname !== "") ||
        !url.hostname.includes(".") || url.hostname === "localhost" ||
        /^(?:\d{1,3}\.){3}\d{1,3}$/.test(url.hostname) ||
        url.hostname.includes("..")) return null;
    return url.origin;
  } catch { return null; }
}

/** Use the existing Kubernetes secret mount or explicit protected server env. */
export function brokerConfig(
  env: NodeJS.ProcessEnv = process.env,
  readSecret: (filename: string) => string | undefined = file => {
    try { return readFileSync(join(process.env.MERIDIAN_SECRETS_DIR ?? "/etc/meridian-secrets", file), "utf8"); }
    catch { return undefined; }
  },
): BrokerConfig | null {
  const origin = validBrokerOrigin(env.INVESTOR_BROKER_ORIGIN ?? "");
  const serviceToken = (readSecret("investor-broker-service-token") ?? env.INVESTOR_BROKER_SERVICE_TOKEN ?? "").trim();
  if (!origin || serviceToken.length < 32 || serviceToken.length > 512 || /[\r\n\s]/.test(serviceToken)) return null;
  return { origin, serviceToken };
}

/**
 * Require the caller to present a secure, host-bound cookie issued by the
 * identity broker. Cookie creation/login/MFA is the broker's job, NOT this site.
 */
export function validSessionCookie(cookie: unknown): cookie is string {
  return typeof cookie === "string" && SESSION_PATTERN.test(cookie);
}

export function parseInvestorGrant(raw: unknown, now: number): InvestorGrant | null {
  if (!isObject(raw) || raw.decision !== "allow" ||
      raw.issuer !== "meridian-investor-broker" || raw.identityVerified !== true ||
      raw.revoked !== false) return null;
  const grantId = cleanText(raw.grantId, 128), subject = cleanText(raw.subject, 160);
  const displayName = cleanText(raw.displayName, 80);
  // Grant age and inactivity are different security controls. The broker must
  // atomically reject expired, revoked or idle sessions BEFORE touching lastActivityAt.
  // This web application trusts only the authenticated broker's current introspection.
  const issued = parseTime(raw.issuedAt), expires = parseTime(raw.expiresAt);
  const lastActivity = parseTime(raw.lastActivityAt), verified = parseTime(raw.identityVerifiedAt);
  if (!grantId || !/^[a-zA-Z0-9:_-]{8,128}$/.test(grantId) || !subject ||
      !displayName || issued === null || expires === null || lastActivity === null ||
      verified === null || issued > now + 5000 || expires <= now ||
      expires <= issued || expires - issued > MAX_GRANT_WINDOW_MS ||
      lastActivity < issued || lastActivity > now + 5000 || lastActivity >= expires ||
      now - lastActivity >= MAX_SESSION_WINDOW_MS || verified > now + 5000) return null;
  if (!Array.isArray(raw.permissions) || raw.permissions.length === 0 ||
      raw.permissions.length > PERMISSIONS.length ||
      raw.permissions.some(p => !PERMISSIONS.includes(p as InvestorPermission)) ||
      new Set(raw.permissions).size !== raw.permissions.length) return null;
  return { grantId, subject, displayName,
    issuedAt: raw.issuedAt as string, expiresAt: raw.expiresAt as string,
    lastActivityAt: raw.lastActivityAt as string,
    identityVerifiedAt: raw.identityVerifiedAt as string,
    permissions: raw.permissions as InvestorPermission[] };
}

async function brokerPost(
  config: BrokerConfig, path: "/v1/investor/introspect" | "/v1/investor/projection",
  payload: object, fetcher: Fetcher,
): Promise<Response> {
  return fetcher(config.origin + path, {
    method: "POST", cache: "no-store", redirect: "error",
    headers: { "Content-Type": "application/json", Accept: "application/json",
      Authorization: "Bearer " + config.serviceToken },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(4500),
  });
}

export async function authorizeInvestor(
  sessionCookie: unknown, config: BrokerConfig | null,
  now = Date.now(), fetcher: Fetcher = fetch,
): Promise<AccessResult> {
  if (!validSessionCookie(sessionCookie)) return { state: "denied", reason: "no_session" };
  if (!config) return { state: "unavailable", reason: "not_configured" };
  try {
    const response = await brokerPost(config, "/v1/investor/introspect",
      { session: sessionCookie, audience: "meridian-investor-room" }, fetcher);
    if (response.status === 401 || response.status === 403 || response.status === 410)
      return { state: "denied", reason: response.status === 410 ? "expired" : "invalid" };
    if (!response.ok) return { state: "unavailable", reason: "upstream_unavailable" };
    const raw: unknown = await response.json();
    const grant = parseInvestorGrant(raw, now);
    return grant ? { state: "allowed", grant } : { state: "denied", reason: "invalid" };
  } catch { return { state: "unavailable", reason: "upstream_unavailable" }; }
}

/** Parse a fixed, investor-approved projection; do not emit arbitrary JSON. */
export function parseInvestorProjection(
  raw: unknown, surface: InvestorSurface, now: number,
): InvestorProjection | null {
  if (!isObject(raw) || raw.schema !== "meridian.investor.projection.v1" ||
      raw.surface !== surface || raw.readOnly !== true ||
      raw.classification !== "INVESTOR_APPROVED" || raw.state !== "observed") return null;
  const at = parseTime(raw.observedAt);
  if (at === null || at > now + 5000 || now - at > 5 * 60_000) return null;
  const headline = cleanText(raw.headline, 130), introduction = cleanText(raw.introduction, 500);
  const revision = raw.sourceRevision;
  if (!headline || !introduction || typeof revision !== "string" || !SHA.test(revision)) return null;
  if (!Array.isArray(raw.facts) || raw.facts.length > 4 ||
      !Array.isArray(raw.moments) || raw.moments.length > 6) return null;
  const facts: InvestorFact[] = [];
  const moments: InvestorMoment[] = [];
  for (const value of raw.facts) {
    if (!isObject(value)) return null;
    const label = cleanText(value.label, 48), fact = cleanText(value.value, 180);
    if (!label || !fact) return null;
    facts.push({ label, value: fact });
  }
  for (const value of raw.moments) {
    if (!isObject(value)) return null;
    const title = cleanText(value.title, 80), description = cleanText(value.description, 280);
    const moment = parseTime(value.observedAt);
    if (!title || !description || moment === null || moment > now + 5000 || now - moment > 7 * 24 * 60 * 60_000) return null;
    moments.push({ title, description, observedAt: value.observedAt as string });
  }
  return { surface, headline, introduction, observedAt: raw.observedAt as string,
    sourceRevision: revision, facts, moments };
}

export async function readInvestorProjection(
  sessionCookie: string, grant: InvestorGrant, surface: InvestorSurface,
  config: BrokerConfig, now = Date.now(), fetcher: Fetcher = fetch,
): Promise<ProjectionResult> {
  if (!validSessionCookie(sessionCookie) ||
      !grant.permissions.includes(`investor:${surface}:view`) ||
      parseTime(grant.expiresAt)! <= now) return { state: "unavailable" };
  try {
    const response = await brokerPost(config, "/v1/investor/projection",
      { session: sessionCookie, grantId: grant.grantId, surface,
        audience: "meridian-investor-room" }, fetcher);
    if (!response.ok) return { state: "unavailable" };
    const projection = parseInvestorProjection(await response.json(), surface, now);
    return projection ? { state: "available", projection } : { state: "unavailable" };
  } catch { return { state: "unavailable" }; }
}
