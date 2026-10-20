/** @type {import('next').NextConfig} */
const securityHeaders = [
  // Everything the site loads is same-origin; fonts are self-hosted by next/font.
  // 'unsafe-inline' is required for the inline ld+json and Next's bootstrap script.
  {
    key: "Content-Security-Policy",
    value: [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline'",
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: blob:",
      "font-src 'self' data:",
      "connect-src 'self'",
      "form-action 'self'",
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "object-src 'none'",
    ].join("; "),
  },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), interest-cohort=()" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
];

const nextConfig = {
  poweredByHeader: false,
  // What web/meridian.Dockerfile copies: Next traces the modules the server imports and
  // emits .next/standalone/server.js, so the image carries no node_modules and no toolchain.
  output: "standalone",
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "images.unsplash.com" },
      { protocol: "https", hostname: "picsum.photos" },
    ],
  },
  async headers() {
    return [
      { source: "/:path*", headers: securityHeaders },
      // The root layout awaits headers() to build the canonical host (LAW 46: the zone lives in
      // the cluster row, not in source), and that await makes every page a dynamic render -- so
      // Next sent `private, no-cache, no-store` on HTML that only changes when a commit lands.
      // Measured 2026-10-20 from the laptop: a first visit to / took 8.6s wall (7.2s of it before
      // the first byte on a lossy uplink) while a second page on the same warm connection took
      // 0.66s; a plain repeat navigation still paid a full round trip because nothing was
      // cacheable. These pages are static content, so they may be stored: five minutes fresh (a
      // deploy is never five minutes old and unseen), a day of stale served while revalidating,
      // and stale served outright when the network fails -- which is the founder's case.
      {
        source: "/:path((?!api/|_next/|opengraph-image|favicon).*)",
        headers: [
          { key: "Cache-Control", value: "public, max-age=300, stale-while-revalidate=86400, stale-if-error=86400" },
        ],
      },
    ];
  },
};
export default nextConfig;
