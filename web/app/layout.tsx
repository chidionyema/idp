import type { Metadata } from "next";
import localFont from "next/font/local";
import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import "./globals.css";

// The woff2 files in ./fonts are the latin subsets of these three families, vendored from
// Google Fonts. `next/font/google` downloads at build time, and the image build was failing on
// that fetch (ETIMEDOUT from fonts.googleapis.com, retried until the build died), so the fonts
// are read off disk instead and the build needs no network at all. The variable names are the
// same three globals.css and every component already reference.
const playfair = localFont({ src: "./fonts/PlayfairDisplay-Variable.woff2", variable: "--serif", display: "swap", weight: "400 900" });
const dmSans = localFont({ src: "./fonts/DMSans-Variable.woff2", variable: "--sans", display: "swap", weight: "100 1000" });
const dmMono = localFont({
  src: [
    { path: "./fonts/DMMono-Light.woff2", weight: "300" },
    { path: "./fonts/DMMono-Regular.woff2", weight: "400" },
    { path: "./fonts/DMMono-Medium.woff2", weight: "500" },
  ],
  variable: "--mono",
  display: "swap",
});

// The host the site is served on arrives in the environment (MERIDIAN_SITE_URL, set by
// platform/meridian/deployment.yaml from the one ConfigMap that holds the zone), never as a
// literal here: LAW 46 still holds -- bin/estate-zone-gate refuses a hostname on main.
//
// It is deliberately not read off the request. `await headers()` marks every route that renders
// under this layout as dynamic, so the whole site was server-rendered per visit with no caching:
// measured 9.1 s cold and 1.4-2.9 s on a repeat from the same laptop, on a 300m CPU pod. A value
// known at build time keeps the pages static, which is what a brochure site wants; the canonical
// link, the OpenGraph url and every relative OG image resolve against it.
const SITE_URL = process.env.MERIDIAN_SITE_URL ?? "http://localhost:3000";

export function generateMetadata(): Metadata {
  const base = new URL(SITE_URL);
  return {
    metadataBase: base,
    title: { default: "Meridian Intelligence", template: "%s | Meridian Intelligence" },
    description: "We build the routing, tracing, workload identity and eval layers that put LLM features into production. Twelve deployments, with the numbers.",
    openGraph: { type: "website", locale: "en_US", url: base.href, siteName: "Meridian Intelligence", images: [{ url: "/opengraph-image", width: 1200, height: 630 }] },
    twitter: { card: "summary_large_image", creator: "@meridianai" },
    robots: { index: true, follow: true },
  };
}

const jsonLd = {
  "@context": "https://schema.org", "@type": "Organization",
  name: "Meridian Intelligence", url: "https://meridian.ai",
  logo: "https://meridian.ai/favicon.svg", email: "hello@meridian.ai",
  sameAs: ["https://github.com/meridian-intelligence", "https://linkedin.com/company/meridian-intelligence"],
  contactPoint: { "@type": "ContactPoint", email: "hello@meridian.ai", contactType: "sales" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${playfair.variable} ${dmSans.variable} ${dmMono.variable}`}>
      <head>
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        {/* The scroll reveal is decoration. Without scripting it would leave every
            section at opacity 0, so unhide it here rather than trusting the observer. */}
        <noscript>
          <style>{`.data-reveal{opacity:1!important;transform:none!important}`}</style>
        </noscript>
      </head>
      <body style={{ fontFamily: "var(--sans)", background: "var(--bg)", color: "var(--ink)", minHeight: "100dvh", display: "flex", flexDirection: "column" }}>
        <a href="#main" className="skip-link">Skip to content</a>
        <Nav />
        <main id="main" style={{ flex: 1 }}>{children}</main>
        <Footer />
      </body>
    </html>
  );
}
