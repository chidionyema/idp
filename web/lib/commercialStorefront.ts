/** Guard external digital-commerce URLs; no speculative checkout links.
 * Only verified Gumroad product URLs are accepted. Malformed URLs and any
 * unapproved host are rendered as publisher-not-yet-connected, never clicked.
 */
export function verifiedGumroadProductUrl(raw?: string | null): string | null {
  if (!raw || !raw.trim()) return null;
  try {
    const url = new URL(raw.trim());
    const validHost = url.hostname === "gumroad.com" || url.hostname.endsWith(".gumroad.com");
    if (url.protocol !== "https:" || !validHost || url.username || url.password || url.port ||
        !/^\/l\/[A-Za-z0-9_-]+\/?$/.test(url.pathname)) return null;
    // Do not forward user-controlled checkout parameters or fragments.
    return url.origin + url.pathname.replace(/\/$/, "");
  } catch {
    return null;
  }
}
