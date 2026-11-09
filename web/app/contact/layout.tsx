import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Contact",
  description:
    "Tell us what you are running and what it costs. Tell us what you are building and what a successful result must prove.",
  alternates: { canonical: "/contact" },
  openGraph: {
    type: "website",
    title: "Contact | Meridian Intelligence",
    description: "Tell us what you are running and what it costs. Start a technical conversation with Meridian Intelligence.",
    url: "/contact",
  },
};

export default function ContactLayout({ children }: { children: React.ReactNode }) {
  return children;
}
