import type { Metadata } from "next";
import { Playfair_Display, DM_Sans, DM_Mono } from "next/font/google";
import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import "./globals.css";

const playfair = Playfair_Display({ subsets: ["latin"], variable: "--serif", display: "swap" });
const dmSans = DM_Sans({ subsets: ["latin"], variable: "--sans", display: "swap" });
const dmMono = DM_Mono({ subsets: ["latin"], variable: "--mono", weight: ["300", "400", "500"], display: "swap" });

export const metadata: Metadata = {
  // The host the site is actually served on (platform/meridian/public-door.yaml), not a domain
  // the estate does not own: these URLs become the canonical link, the OpenGraph url and the
  // base every relative OG image resolves against, so a wrong host here is a wrong canonical
  // on every page.
  metadataBase: new URL("https://meridian.mumchimp.com"),
  title: { default: "Meridian Intelligence", template: "%s | Meridian Intelligence" },
  description: "We build the routing, tracing, workload identity and eval layers that put LLM features into production. Twelve deployments, with the numbers.",
  openGraph: { type: "website", locale: "en_US", url: "https://meridian.mumchimp.com", siteName: "Meridian Intelligence", images: [{ url: "/opengraph-image", width: 1200, height: 630 }] },
  twitter: { card: "summary_large_image", creator: "@meridianai" },
  robots: { index: true, follow: true },
};

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
