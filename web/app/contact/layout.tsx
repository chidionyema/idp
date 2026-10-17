import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Contact",
  description:
    "Tell us what you are running and what it costs. We reply within one business day, and the first call is a diagnosis rather than a pitch.",
  alternates: { canonical: "/contact" },
  openGraph: {
    type: "website",
    title: "Contact | Meridian Intelligence",
    description: "Tell us what you are running and what it costs. We reply within one business day.",
    url: "/contact",
  },
};

export default function ContactLayout({ children }: { children: React.ReactNode }) {
  return children;
}
