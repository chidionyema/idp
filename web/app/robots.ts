import { MetadataRoute } from "next";
export default function robots(): MetadataRoute.Robots {
  const base = process.env.MERIDIAN_SITE_URL ?? process.env.MERDIAN_SITE_URL ?? process.env.MERIAN_SITE_URL ?? "https://meridian-intelligence-uk.vercel.app";
  return { rules: { userAgent: "*", allow: "/" }, sitemap: `${base}/sitemap.xml` };
}
