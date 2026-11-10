import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Contact",
  description: "Discuss AI strategy, engineering, autonomous systems, research partnerships or ventures with Merdian Intelligence.",
  alternates: { canonical: "/contact" },
  openGraph: {
    type: "website",
    title: "Contact | Merdian Intelligence",
    description: "Tell Merdian Intelligence about the engineering challenge or research question you want to tackle.",
    url: "/contact",
  },
};

export default function ContactLayout({ children }: { children: React.ReactNode }) {
  return children;
}
